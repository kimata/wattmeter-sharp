"""センサー状態を返すFlask API。"""

import datetime
import logging
import threading
import time
from pathlib import Path

import flask
import my_lib.flask_util
import my_lib.time

import sharp_hems.device
from sharp_hems.metrics.collector import MetricsCollector

blueprint = flask.Blueprint("webapi-metrics", __name__)

_collector_lock = threading.Lock()


def _get_collector() -> MetricsCollector:
    """アプリケーション単位で共有する MetricsCollector を返す。"""
    app_config = flask.current_app.config
    with _collector_lock:
        if "METRICS_COLLECTOR" not in app_config:
            metrics_db_path = Path(app_config["CONFIG"]["metrics"]["data"])
            app_config["METRICS_COLLECTOR"] = MetricsCollector(metrics_db_path)
        return app_config["METRICS_COLLECTOR"]


@blueprint.route("/api/communication_errors", methods=["GET"])
@my_lib.flask_util.support_jsonp
def communication_errors():
    """
    通信エラー情報を返すAPI。

    Returns:
        JSON: {
            "histogram": {
                "bins": [...],
                "bin_labels": [...],
                "total_errors": 123
            },
            "latest_errors": [
                {
                    "sensor_name": "センサー名",
                    "datetime": "YYYY-MM-DD HH:MM:SS",
                    "timestamp": 1234567890,
                    "error_type": "consecutive_failure"
                }
            ]
        }

    """
    try:
        collector = _get_collector()

        # 通信エラーヒストグラム（過去1ヶ月）を取得
        histogram = collector.get_communication_errors_histogram(hours=24 * 30)

        # 最新の通信エラーログ（50件）を取得
        latest_errors = collector.get_latest_communication_errors(limit=50)

        # 通信エラーの時刻をUTCからJSTに変換
        for error in latest_errors:
            utc_datetime = datetime.datetime.strptime(error["datetime"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=datetime.UTC
            )
            jst_datetime = utc_datetime.astimezone(my_lib.time.get_zoneinfo())
            error["datetime"] = jst_datetime.strftime("%Y-%m-%d %H:%M:%S")

        result = {"histogram": histogram, "latest_errors": latest_errors}

        return flask.jsonify(result)

    except Exception as e:
        logging.exception("Failed to get communication errors")
        flask.abort(500, f"Failed to get communication errors: {e!s}")


@blueprint.route("/api/sensor_stat", methods=["GET"])
@my_lib.flask_util.support_jsonp
def sensor_stat():
    """
    センサーメトリクス情報を返すAPI。

    Returns:
        JSON: {
            "start_date": "YYYY-MM-DD",
            "sensors": [
                {
                    "name": "センサー名",
                    "availability_total": 95.5,
                    "availability_24h": 98.0,
                    "last_received": "YYYY-MM-DD HH:MM:SS"
                }
            ]
        }

    """
    try:
        config = flask.current_app.config["CONFIG"]
        collector = _get_collector()

        # デバイス定義ファイルを読み込み
        device_define_file = Path(config["device"]["define"])
        sharp_hems.device.reload(device_define_file)
        sensor_names = sharp_hems.device.get_list()

        # メトリクス収集開始日を取得（日次サマリーと生データの古い方）
        now = int(time.time())
        start_date = collector.get_start_date()
        if start_date is None:
            start_date = datetime.datetime.now(datetime.UTC).date().strftime("%Y-%m-%d")

        # 各センサーのメトリクス情報を収集
        sensors_metrics = []
        for sensor_name in sensor_names:
            # 最新のハートビート時刻を取得
            latest_timestamp = collector.get_latest_heartbeat(sensor_name)
            last_received = None
            if latest_timestamp:
                # UTCからJSTに変換
                utc_datetime = datetime.datetime.fromtimestamp(latest_timestamp, datetime.UTC)
                jst_datetime = utc_datetime.astimezone(my_lib.time.get_zoneinfo())
                last_received = jst_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # 累計と過去24時間の受信率を計算
            total_availability = collector.calculate_total_availability(sensor_name, now)
            last_24h_availability = collector.calculate_availability_between(sensor_name, now - 86400, now)

            sensors_metrics.append(
                {
                    "name": sensor_name,
                    "availability_total": total_availability,
                    "availability_24h": last_24h_availability,
                    "last_received": last_received,
                    "last_received_ts": latest_timestamp,
                }
            )

        result = {"start_date": start_date, "sensors": sensors_metrics}

        return flask.jsonify(result)

    except Exception as e:
        logging.exception("Failed to get metrics")
        flask.abort(500, f"Failed to get metrics: {e!s}")
