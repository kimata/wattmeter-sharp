#!/usr/bin/env python3
"""
スマートメータの実測値と突合して、電力補正倍率 (watt_scale) を較正します。

config.yaml の calibration.smartmeter で、スマートメータの計測値が入っている
InfluxDB の measurement / hostname / field を指定してください。

Usage:
  sharp_hems_calibrate.py [-c CONFIG] [-d DAYS] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -d DAYS           : 比較する日数を指定します。 [default: 7]
  -D                : デバッグモードで動作します。
"""

import asyncio
import logging
import pathlib

import my_lib.sensor_data

import sharp_hems.config
import sharp_hems.device
import sharp_hems.sniffer

# 比較に使う集計ウィンドウ (分)
WINDOW_MIN = 30


def compute_scale(current_scale, wattmeter_sums, smartmeter_values):
    """
    ウィンドウ毎の (全プラグ合計, スマートメータ実測) の対から新しい倍率を推定する。

    どちらかが欠損・ゼロのウィンドウは比較対象から除外する。
    """
    pairs = [
        (w, s)
        for w, s in zip(wattmeter_sums, smartmeter_values, strict=False)
        if w is not None and s is not None and w > 0 and s > 0
    ]

    if len(pairs) == 0:
        return None, 0

    wattmeter_total = sum(w for w, _ in pairs)
    smartmeter_total = sum(s for _, s in pairs)

    return current_scale * smartmeter_total / wattmeter_total, len(pairs)


def fetch_series(config, days):
    """全デバイスとスマートメータの時系列を取得する。"""
    db_config = my_lib.sensor_data.InfluxDBConfig.parse(config["influxdb"])
    measure = "{tag}.{label}".format(
        tag=config["fluentd"]["data"]["tag"], label=config["fluentd"]["data"]["label"]
    )
    field = config["fluentd"]["data"]["field"]

    sharp_hems.device.reload(pathlib.Path(config["device"]["define"]))
    sensor_names = sharp_hems.device.get_list()

    smartmeter = config["calibration"]["smartmeter"]

    requests = [
        my_lib.sensor_data.DataRequest(
            measure,
            name,
            field,
            start=f"-{days}d",
            every_min=WINDOW_MIN,
            window_min=WINDOW_MIN,
            create_empty=True,
        )
        for name in sensor_names
    ]
    requests.append(
        my_lib.sensor_data.DataRequest(
            smartmeter["measure"],
            smartmeter["hostname"],
            smartmeter.get("field", "power"),
            start=f"-{days}d",
            every_min=WINDOW_MIN,
            window_min=WINDOW_MIN,
            create_empty=True,
        )
    )

    results = asyncio.run(my_lib.sensor_data.fetch_data_parallel(db_config, requests))

    device_results = results[:-1]
    smartmeter_result = results[-1]

    return sensor_names, device_results, smartmeter_result


def sum_device_series(device_results):
    """全デバイスの時系列をウィンドウ毎に合計する (欠損は 0 扱い)。"""
    # 時刻の和集合を軸に揃える
    time_set = set()
    for result in device_results:
        if isinstance(result, my_lib.sensor_data.SensorDataResult) and result.valid:
            time_set.update(int(t.timestamp()) for t in result.time)

    times = sorted(time_set)
    time_index = {t: i for i, t in enumerate(times)}
    sums = [0.0] * len(times)

    for result in device_results:
        if not (isinstance(result, my_lib.sensor_data.SensorDataResult) and result.valid):
            continue
        for t, v in zip(result.time, result.value, strict=False):
            if v is None:
                continue
            index = time_index.get(int(t.timestamp()))
            if index is not None:
                sums[index] += float(v)

    return times, sums


def calibrate(config, days):
    current_scale = config.get("sensor", {}).get("watt_scale", sharp_hems.sniffer.WATT_SCALE_DEFAULT)

    sensor_names, device_results, smartmeter_result = fetch_series(config, days)

    valid_devices = sum(
        1 for r in device_results if isinstance(r, my_lib.sensor_data.SensorDataResult) and r.valid
    )
    logging.info("Fetched %d/%d device series", valid_devices, len(sensor_names))

    if not (isinstance(smartmeter_result, my_lib.sensor_data.SensorDataResult) and smartmeter_result.valid):
        logging.error("スマートメータのデータを取得できませんでした")
        return None

    times, sums = sum_device_series(device_results)

    # スマートメータ値を同じ時刻軸に揃える
    time_index = {t: i for i, t in enumerate(times)}
    smart_values: list[float | None] = [None] * len(times)
    for t, v in zip(smartmeter_result.time, smartmeter_result.value, strict=False):
        index = time_index.get(int(t.timestamp()))
        if index is not None and v is not None:
            smart_values[index] = float(v)

    new_scale, sample_count = compute_scale(current_scale, sums, smart_values)

    if new_scale is None:
        logging.error("比較可能なウィンドウがありませんでした")
        return None

    logging.info("========================================")
    logging.info("比較期間          : 過去 %d 日 (%d 分ウィンドウ x %d)", days, WINDOW_MIN, sample_count)
    logging.info("現在の watt_scale : %.3f", current_scale)
    logging.info("推奨の watt_scale : %.3f", new_scale)
    logging.info("========================================")
    logging.info("config.yaml の sensor.watt_scale を更新してください。")
    logging.info("(注: プラグを経由しない機器の消費電力分だけ、推定値は大きめに出ます)")

    return new_scale


######################################################################
def main():
    import docopt
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    days = int(args["-d"])
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = sharp_hems.config.load(config_file)

    if "calibration" not in config:
        logging.error("config.yaml に calibration.smartmeter の設定がありません。")
        logging.error("例:")
        logging.error("calibration:")
        logging.error("    smartmeter:")
        logging.error("        measure: sensor.rasp")
        logging.error("        hostname: smartmeter")
        logging.error("        field: power")
        return

    calibrate(config, days)


if __name__ == "__main__":
    main()
