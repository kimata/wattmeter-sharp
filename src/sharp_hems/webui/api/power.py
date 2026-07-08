"""電力データを返す Flask API。"""

import asyncio
import logging
import threading
import time
from pathlib import Path

import flask
import my_lib.flask_util
import my_lib.sensor_data

import sharp_hems.device

blueprint = flask.Blueprint("webapi-power", __name__)

# NOTE: 現在値はセンサーの送信周期 (約6分) の 5 周期分まで遡って探す
CURRENT_LOOKBACK = "-30m"
CURRENT_CACHE_SEC = 30
HISTORY_CACHE_SEC = 240

RANGE_CONFIG = {
    "3h": {"start": "-3h", "every_min": 6},
    "24h": {"start": "-24h", "every_min": 15},
    "7d": {"start": "-7d", "every_min": 60},
    "30d": {"start": "-30d", "every_min": 180},
}

_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > time.time():
            return entry[1]
        return None


def _cache_set(key, value, ttl):
    with _cache_lock:
        _cache[key] = (time.time() + ttl, value)


def _get_context():
    config = flask.current_app.config["CONFIG"]

    db_config = my_lib.sensor_data.InfluxDBConfig.parse(config["influxdb"])
    measure = "{tag}.{label}".format(
        tag=config["fluentd"]["data"]["tag"], label=config["fluentd"]["data"]["label"]
    )
    field = config["fluentd"]["data"]["field"]

    sharp_hems.device.reload(Path(config["device"]["define"]))
    sensor_names = sharp_hems.device.get_list()

    return db_config, measure, field, sensor_names


def _fetch_parallel(db_config, requests):
    return asyncio.run(my_lib.sensor_data.fetch_data_parallel(db_config, requests))


@blueprint.route("/api/power/current", methods=["GET"])
@my_lib.flask_util.support_jsonp
def power_current():
    """
    全デバイスの現在の消費電力を返すAPI。

    Returns:
        JSON: {
            "total": 1234.5,
            "devices": [
                {"name": "冷蔵庫", "watt": 50.2, "time": 1751900000}
            ],
            "updated_at": 1751900060
        }

    """
    try:
        cached = _cache_get("current")
        if cached is not None:
            return flask.jsonify(cached)

        db_config, measure, field, sensor_names = _get_context()

        requests = [
            my_lib.sensor_data.DataRequest(measure, name, field, start=CURRENT_LOOKBACK, last=True)
            for name in sensor_names
        ]
        results = _fetch_parallel(db_config, requests)

        devices = []
        total = 0.0
        for name, result in zip(sensor_names, results, strict=False):
            watt = None
            timestamp = None
            if (
                isinstance(result, my_lib.sensor_data.SensorDataResult)
                and result.valid
                and result.value
                and result.value[0] is not None
            ):
                watt = round(float(result.value[0]), 1)
                total += watt
                if result.time:
                    timestamp = int(result.time[0].timestamp())

            devices.append({"name": name, "watt": watt, "time": timestamp})

        response = {
            "total": round(total, 1),
            "devices": devices,
            "updated_at": int(time.time()),
        }
        _cache_set("current", response, CURRENT_CACHE_SEC)

        return flask.jsonify(response)

    except Exception as e:
        logging.exception("Failed to get current power")
        flask.abort(500, f"Failed to get current power: {e!s}")


@blueprint.route("/api/power/history", methods=["GET"])
@my_lib.flask_util.support_jsonp
def power_history():
    """
    全デバイスの消費電力履歴を返すAPI。

    Query Parameters:
        range: 取得期間 (3h / 24h / 7d / 30d、デフォルト 24h)

    Returns:
        JSON: {
            "range": "24h",
            "every_min": 15,
            "times": [1751800000, ...],
            "series": [
                {"name": "冷蔵庫", "values": [50.2, null, ...], "energy_wh": 1200.5}
            ],
            "updated_at": 1751900060
        }

    """
    range_key = flask.request.args.get("range", "24h")
    range_config = RANGE_CONFIG.get(range_key)
    if range_config is None:
        flask.abort(400, f"Invalid range: {range_key} (expected {'/'.join(RANGE_CONFIG)})")

    try:
        cache_key = f"history:{range_key}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return flask.jsonify(cached)

        db_config, measure, field, sensor_names = _get_context()

        requests = [
            my_lib.sensor_data.DataRequest(
                measure,
                name,
                field,
                start=range_config["start"],
                every_min=range_config["every_min"],
                window_min=range_config["every_min"],
                create_empty=True,
            )
            for name in sensor_names
        ]
        results = _fetch_parallel(db_config, requests)

        response = _build_history_response(range_key, range_config, sensor_names, results)
        _cache_set(cache_key, response, HISTORY_CACHE_SEC)

        return flask.jsonify(response)

    except Exception as e:
        logging.exception("Failed to get power history")
        flask.abort(500, f"Failed to get power history: {e!s}")


def _build_history_response(range_key, range_config, sensor_names, results):
    """取得結果を、共通の時刻軸に揃えた JSON 応答に組み立てる。"""
    # NOTE: create_empty=True でも系列間で時刻が完全一致する保証はないため、
    # 全系列の時刻の和集合を軸にして揃える
    time_set = set()
    for result in results:
        if isinstance(result, my_lib.sensor_data.SensorDataResult) and result.valid:
            time_set.update(int(t.timestamp()) for t in result.time)

    times = sorted(time_set)
    time_index = {t: i for i, t in enumerate(times)}

    interval_hour = range_config["every_min"] / 60.0

    series = []
    for name, result in zip(sensor_names, results, strict=False):
        values: list[float | None] = [None] * len(times)
        energy_wh = None

        if isinstance(result, my_lib.sensor_data.SensorDataResult) and result.valid:
            energy_wh = 0.0
            for t, v in zip(result.time, result.value, strict=False):
                if v is None:
                    continue
                index = time_index.get(int(t.timestamp()))
                if index is not None:
                    values[index] = round(float(v), 1)
                energy_wh += float(v) * interval_hour
            energy_wh = round(energy_wh, 1)

        series.append({"name": name, "values": values, "energy_wh": energy_wh})

    return {
        "range": range_key,
        "every_min": range_config["every_min"],
        "times": times,
        "series": series,
        "updated_at": int(time.time()),
    }
