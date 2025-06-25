#!/usr/bin/env python3
"""
センサーから収集した消費電力データを Fluentd を使って送信します．

Usage:
  sharp_hmes_logger.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-T] [-d]

Options:
  -c CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します． [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -T                : テストモードで動作します．
  -d                : デバッグモードで動作します．
"""

import logging
import os
import pathlib

import my_lib.fluentd_util
import my_lib.footprint
import sharp_hems.device
import sharp_hems.notify
import sharp_hems.serial_pubsub
import sharp_hems.sniffer

SCHEMA_CONFIG = "config.schema"


def fluent_send(sender, label, field, data, liveness_file):
    try:
        name = sharp_hems.device.get_name(data["addr"])

        if name is None:
            logging.warning("Unknown device: dev_id = %s", data["dev_id_str"])
            return

        data = {
            "hostname": name,
            field: int(data["watt"]),
        }

        if my_lib.fluentd_util.send(sender, label, data):
            logging.info("Send: %s", data)
            my_lib.footprint.update(liveness_file)
        else:
            logging.error(sender.last_error)
    except Exception:
        sharp_hems.notify.error(config)


def process_packet(handle, header, payload):
    global test_mode

    sharp_hems.device.reload(handle["device"]["define"])

    if test_mode:
        sharp_hems.sniffer.process_packet(
            handle, header, payload, lambda _: (logging.info("OK"), os._exit(0))
        )
    else:
        sharp_hems.sniffer.process_packet(
            handle,
            header,
            payload,
            lambda data: fluent_send(
                handle["sender"],
                config["fluentd"]["data"]["label"],
                config["fluentd"]["data"]["field"],
                data,
                handle["liveness"],
            ),
        )


def start(handle):
    try:
        sharp_hems.serial_pubsub.start_client(server_host, server_port, handle, process_packet)
    except:
        sharp_hems.notify.error(config)
        raise


######################################################################
if __name__ == "__main__":
    import pathlib

    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    server_host = os.environ.get("HEMS_SERVER_HOST", args["-s"])
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    test_mode = args["-T"]
    debug_mode = args["-d"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, pathlib.Path(SCHEMA_CONFIG))

    dev_define_file = pathlib.Path(config["device"]["define"])
    dev_cache_file = pathlib.Path(config["device"]["cache"])
    liveness_file = pathlib.Path(config["liveness"]["file"]["measure"])

    logging.info("Start HEMS logger (server: %s:%d)", server_host, server_port)

    if test_mode:
        logging.info("TEST MODE")

    logging.info(
        "Initialize Fluentd sender (host: %s, tag: %s)",
        config["fluentd"]["host"],
        config["fluentd"]["data"]["tag"],
    )
    sender = my_lib.fluentd_util.get_handle(config["fluentd"]["data"]["tag"], host=config["fluentd"]["host"])

    start(
        {
            "sender": sender,
            "device": {
                "define": dev_define_file,
                "cache": dev_cache_file,
            },
            "data": {
                "label": config["fluentd"]["data"]["label"],
                "field": config["fluentd"]["data"]["field"],
            },
            "liveness": liveness_file,
        }
    )
