"""センサー状態を返すFlask API。"""

import datetime
import logging
from pathlib import Path

import flask
import my_lib.flask_util
import my_lib.sensor_data

import sharp_hems.device
from sharp_hems.metrics.collector import MetricsCollector

blueprint = flask.Blueprint("webapi-sensor-stat", __name__, url_prefix=my_lib.webapp.config.URL_PREFIX)


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
                    "last_received": "YYYY-MM-DD HH:MM:SS",
                    "power_consumption": 1023
                }
            ]
        }

    """
    try:
        # 設定から必要な情報を取得
        config = flask.current_app.config["CONFIG"]
        if not config:
            flask.abort(500, "Configuration not found")

        # メトリクスDBのパスを取得
        metrics_db_path = Path(config["metrics"]["data"])
        collector = MetricsCollector(metrics_db_path)

        # デバイス定義ファイルを読み込み
        device_define_file = Path(config["device"]["define"])
        sharp_hems.device.reload(device_define_file)
        sensor_names = sharp_hems.device.get_list()

        # 現在日付を取得 (将来の拡張用に準備)
        # today = datetime.datetime.now(datetime.timezone.utc).date()

        # メトリクス収集開始日を取得（最初のレコード日付）
        start_date = _get_metrics_start_date(collector)

        # 各センサーのメトリクス情報を収集
        sensors_metrics = []
        for sensor_name in sensor_names:
            # 最新のハートビート時刻を取得
            latest_timestamp = collector.get_latest_heartbeat(sensor_name)
            last_received = None
            if latest_timestamp:
                last_received = datetime.datetime.fromtimestamp(
                    latest_timestamp, datetime.timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S")

            # 累計の稼働率を計算
            total_availability = _calculate_total_availability(collector, sensor_name, start_date)

            # 過去24時間の稼働率を計算
            last_24h_availability = _calculate_last_24h_availability(collector, sensor_name)

            # 最新の電力消費値を取得
            power_consumption = _get_latest_power_consumption(config, sensor_name)

            sensors_metrics.append(
                {
                    "name": sensor_name,
                    "availability_total": total_availability,
                    "availability_24h": last_24h_availability,
                    "last_received": last_received,
                    "power_consumption": power_consumption,
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
            earliest_date = datetime.datetime.fromtimestamp(earliest_timestamp, datetime.timezone.utc).date()
            return earliest_date.strftime("%Y-%m-%d")
        else:
            # データがない場合は今日の日付を返す
            return datetime.datetime.now(datetime.timezone.utc).date().strftime("%Y-%m-%d")


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
    now = datetime.datetime.now(datetime.timezone.utc)
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
    now = datetime.datetime.now(datetime.timezone.utc)
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


def _get_latest_power_consumption(config, sensor_name: str) -> int | None:
    """
    センサーの最新の電力消費値を取得します。

    Args:
        config: アプリケーション設定
        sensor_name: センサー名

    Returns:
        最新の電力消費値（W）、データがない場合はNone

    """
    try:
        # InfluxDBから最新の電力データを取得
        sensor_data = my_lib.sensor_data.fetch_data(
            config["influxdb"],
            "{tag}.{label}".format(
                tag=config["fluentd"]["data"]["tag"], label=config["fluentd"]["data"]["label"]
            ),
            sensor_name,
            config["fluentd"]["data"]["field"],
            "-1h",  # 過去1時間のデータを取得
        )

        if sensor_data["valid"] and sensor_data["data"]:
            # 最新のデータポイントから電力値を取得
            latest_point = sensor_data["data"][-1]
            return int(latest_point[1]) if latest_point[1] is not None else None
        else:
            return None

    except Exception as e:
        logging.warning("Failed to get power consumption for %s: %s", sensor_name, e)
        return None
