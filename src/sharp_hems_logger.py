#!/usr/bin/env python3
"""
センサーから収集した消費電力データを Fluentd を使って送信します。

Usage:
  sharp_hems_logger.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-n COUNT] [-d] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します。 [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します。 [default: 4444]
  -n COUNT          : n 回制御メッセージを受信したら終了します。0 は制限なし。 [default: 0]
  -d                : ダミーモードで動作します。
  -D                : デバッグモードで動作します。
"""

import logging
import os
import pathlib
import signal
import sys

import my_lib.fluentd_util
import my_lib.footprint
import my_lib.pretty

import sharp_hems.device
import sharp_hems.notify
import sharp_hems.serial_pubsub
import sharp_hems.sniffer
from sharp_hems.metrics.collector import MetricsCollector

SCHEMA_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config.schema"

# グローバル変数として保持（シグナルハンドラで使用）
_metrics_collector = None
_sender = None


def env_flag(name):
    """環境変数を真偽値として解釈する ("false" や "0" は偽)。"""
    value = os.environ.get(name)
    if value is None:
        return None
    return value.strip().lower() in ("1", "true", "yes", "on")


def record_metrics(metrics_collector, data):
    """メトリクス収集を記録する"""
    try:
        name = sharp_hems.device.get_name(data["addr"])
        if name is not None:
            metrics_collector.record_heartbeat(name)
            logging.debug("Recorded metrics for %s", name)
    except Exception:
        logging.exception("Failed to record metrics")


def fluent_send(handle, data):
    try:
        name = sharp_hems.device.get_name(data["addr"])

        if name is None:
            logging.warning("Unknown device: dev_id = %s", data["dev_id_str"])
            return

        send_data = {
            "hostname": name,
            handle["data"]["field"]: round(data["watt"]),
        }

        if my_lib.fluentd_util.send(handle["sender"], handle["data"]["label"], send_data):
            logging.info("Send: %s", send_data)
            my_lib.footprint.update(handle["liveness"])
        else:
            logging.error(handle["sender"].last_error)
    except Exception:
        sharp_hems.notify.error(handle["config"])


def process_packet(handle, header, payload):
    sharp_hems.device.reload(handle["device"]["define"])

    if handle["dummy_mode"]:

        def on_data_received(data):
            logging.info(my_lib.pretty.format(data))
            handle["packet"]["count"] += 1
            if (handle["packet"]["max"] != 0) and (handle["packet"]["count"] >= handle["packet"]["max"]):
                sharp_hems.serial_pubsub.stop_client()
    else:

        def on_data_received(data):
            # Fluentdに送信
            fluent_send(handle, data)
            # メトリクス収集も記録
            if "metrics_collector" in handle:
                record_metrics(handle["metrics_collector"], data)

    sharp_hems.sniffer.process_packet(handle, header, payload, on_data_received)


def cleanup():
    """終了処理を実行します。"""
    global _metrics_collector, _sender

    logging.info("Starting cleanup process...")

    sharp_hems.serial_pubsub.stop_client()

    # メトリクスコレクターをクローズ
    if _metrics_collector:
        try:
            _metrics_collector.close()
            logging.info("Closed metrics collector")
        except Exception:
            logging.exception("Failed to close metrics collector")

    # Fluentd senderをクローズ
    if _sender:
        try:
            if hasattr(_sender, "close"):
                _sender.close()
                logging.info("Closed Fluentd sender")
        except Exception:
            logging.exception("Failed to close Fluentd sender")

    logging.info("Cleanup completed")


def sig_handler(num, frame):  # noqa: ARG001
    """シグナルハンドラー"""
    logging.warning("Received signal %d", num)

    if num in (signal.SIGTERM, signal.SIGINT):
        cleanup()
        sys.exit(0)


def start(handle, server_host, server_port):
    try:
        sharp_hems.serial_pubsub.start_client(server_host, server_port, handle, process_packet)
    except Exception:
        sharp_hems.notify.error(handle["config"])
        raise
    finally:
        cleanup()


######################################################################
if __name__ == "__main__":
    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    server_host = os.environ.get("HEMS_SERVER_HOST", args["-s"])
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    count = int(args["-n"])
    dummy_mode = env_flag("DUMMY_MODE")
    if dummy_mode is None:
        dummy_mode = args["-d"]
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, SCHEMA_CONFIG)

    dev_define_file = pathlib.Path(config["device"]["define"])
    dev_cache_file = pathlib.Path(config["device"]["cache"])
    liveness_file = pathlib.Path(config["liveness"]["file"]["measure"])

    logging.info("Start HEMS logger (server: %s:%d)", server_host, server_port)

    if dummy_mode:
        logging.info("DUMMY MODE")

    logging.info(
        "Initialize Fluentd sender (host: %s, tag: %s)",
        config["fluentd"]["host"],
        config["fluentd"]["data"]["tag"],
    )
    sender = my_lib.fluentd_util.get_handle(config["fluentd"]["data"]["tag"], host=config["fluentd"]["host"])
    _sender = sender  # グローバル変数に保存（シグナルハンドラ用）

    # メトリクスコレクターを初期化
    metrics_collector = None
    if "metrics" in config:
        metrics_db_path = pathlib.Path(config["metrics"]["data"])
        metrics_collector = MetricsCollector(metrics_db_path)
        _metrics_collector = metrics_collector  # グローバル変数に保存（シグナルハンドラ用）
        logging.info("Initialize metrics collector (db: %s)", metrics_db_path)

    # シグナルハンドラーを設定
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    handle = {
        "config": config,
        "sender": sender,
        "device": {
            "define": dev_define_file,
            "cache": dev_cache_file,
        },
        "data": {
            "label": config["fluentd"]["data"]["label"],
            "field": config["fluentd"]["data"]["field"],
        },
        "sensor": {
            "watt_scale": config.get("sensor", {}).get("watt_scale", sharp_hems.sniffer.WATT_SCALE_DEFAULT),
            "scale_resolver": sharp_hems.device.get_scale,
        },
        "dummy_mode": dummy_mode,
        "packet": {
            "count": 0,
            "max": count,
        },
        "liveness": liveness_file,
    }

    if metrics_collector:
        handle["metrics_collector"] = metrics_collector

    start(handle, server_host, server_port)
