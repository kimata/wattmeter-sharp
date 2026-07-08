"""センサー状態を返すFlask API。"""

import datetime
import logging
import threading
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

        # 現在日付を取得 (将来の拡張用に準備)
        # today = datetime.datetime.now(datetime.UTC).date()

        # メトリクス収集開始日を取得（最初のレコード日付）
        start_date = _get_metrics_start_date(collector)

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

            # 累計の稼働率を計算
            total_availability = _calculate_total_availability(collector, sensor_name, start_date)

            # 過去24時間の稼働率を計算
            last_24h_availability = _calculate_last_24h_availability(collector, sensor_name)

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


def _get_metrics_start_date(collector: MetricsCollector) -> str:
    """
    メトリクス収集の開始日を取得します。

    Args:
        collector: MetricsCollectorインスタンス

    Returns:
        開始日（YYYY-MM-DD形式）、データがない場合は今日の日付

    """
    with collector.get_connection() as conn:
        cursor = conn.execute("""
            SELECT MIN(timestamp) FROM sensor_heartbeats
        """)

        result = cursor.fetchone()
        if result and result[0] is not None:
            earliest_timestamp = result[0]
            earliest_date = datetime.datetime.fromtimestamp(earliest_timestamp, datetime.UTC).date()
            return earliest_date.strftime("%Y-%m-%d")
        else:
            # データがない場合は今日の日付を返す
            return datetime.datetime.now(datetime.UTC).date().strftime("%Y-%m-%d")


def _calculate_total_availability(collector: MetricsCollector, sensor_name: str, _start_date: str) -> float:
    """
    データ収集開始から現在までの累計稼働率を計算します。

    現在のタイムスロットでデータを受信していれば、そのスロットも稼働率に含める。

    Args:
        collector: MetricsCollectorインスタンス
        sensor_name: センサー名
        start_date: データ収集開始日（YYYY-MM-DD形式）

    Returns:
        累計稼働率（%）

    """
    # 実際のデータ開始時刻を取得
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT MIN(timestamp) FROM sensor_heartbeats
            WHERE sensor_name = ?
        """,
            (sensor_name,),
        )

        result = cursor.fetchone()
        if result and result[0] is not None:
            actual_start_timestamp = result[0]
        else:
            # データがない場合は0%
            return 0.0

    # 現在時刻
    now = datetime.datetime.now(datetime.UTC)
    current_timestamp = int(now.timestamp())

    # タイムスロット範囲を計算
    start_slot = actual_start_timestamp // 360
    current_slot = current_timestamp // 360

    # 現在のスロットでデータを受信しているかチェック
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM sensor_heartbeats
            WHERE sensor_name = ? AND time_slot = ?
        """,
            (sensor_name, current_slot),
        )

        has_current_slot_data = cursor.fetchone()[0] > 0

    # 期待されるタイムスロット数を計算
    if has_current_slot_data:
        # 現在のスロットでデータを受信している場合、そのスロットも含める
        expected_slots = current_slot - start_slot + 1
        end_slot = current_slot
    else:
        # 現在のスロットでデータを受信していない場合、前のスロットまで
        expected_slots = current_slot - start_slot
        end_slot = current_slot - 1

        # 期待スロット数が0以下になる場合の対処
        if expected_slots <= 0:
            expected_slots = 1
            end_slot = start_slot

    # 実際に受信したタイムスロット数
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(DISTINCT time_slot)
            FROM sensor_heartbeats
            WHERE sensor_name = ?
            AND time_slot >= ?
            AND time_slot <= ?
        """,
            (sensor_name, start_slot, end_slot),
        )

        received_slots = cursor.fetchone()[0]

    if expected_slots <= 0:
        return 0.0

    return round((received_slots / expected_slots) * 100, 2)


def _calculate_last_24h_availability(collector: MetricsCollector, sensor_name: str) -> float:
    """
    過去24時間の稼働率を計算します。

    現在のタイムスロットでデータを受信していれば、そのスロットも稼働率に含める。

    Args:
        collector: MetricsCollectorインスタンス
        sensor_name: センサー名

    Returns:
        過去24時間の稼働率（%）

    """
    now = datetime.datetime.now(datetime.UTC)
    current_timestamp = int(now.timestamp())

    # データ開始時刻を取得
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT MIN(timestamp) FROM sensor_heartbeats
            WHERE sensor_name = ?
        """,
            (sensor_name,),
        )

        result = cursor.fetchone()
        if result and result[0] is not None:
            data_start_timestamp = result[0]
        else:
            # データがない場合は0%
            return 0.0

    # 24時間前の時刻
    yesterday_timestamp = current_timestamp - 86400  # 24時間 = 86400秒

    # 実際の開始時刻（データ開始時刻と24時間前のうち、より新しい方）
    actual_start_timestamp = max(data_start_timestamp, yesterday_timestamp)

    # タイムスロット範囲を計算
    start_slot = actual_start_timestamp // 360
    current_slot = current_timestamp // 360

    # 現在のスロットでデータを受信しているかチェック
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM sensor_heartbeats
            WHERE sensor_name = ? AND time_slot = ?
        """,
            (sensor_name, current_slot),
        )

        has_current_slot_data = cursor.fetchone()[0] > 0

    # 期待されるタイムスロット数を計算
    if has_current_slot_data:
        # 現在のスロットでデータを受信している場合、そのスロットも含める
        expected_slots = current_slot - start_slot + 1
        end_slot = current_slot
    else:
        # 現在のスロットでデータを受信していない場合、前のスロットまで
        expected_slots = current_slot - start_slot
        end_slot = current_slot - 1

        # 期待スロット数が0以下になる場合の対処
        if expected_slots <= 0:
            expected_slots = 1
            end_slot = start_slot

    # 実際に受信したタイムスロット数
    with collector.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(DISTINCT time_slot)
            FROM sensor_heartbeats
            WHERE sensor_name = ?
            AND time_slot >= ?
            AND time_slot <= ?
        """,
            (sensor_name, start_slot, end_slot),
        )

        received_slots = cursor.fetchone()[0]

    if expected_slots <= 0:
        return 0.0

    return round((received_slots / expected_slots) * 100, 2)
