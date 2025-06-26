#!/usr/bin/env python3
"""
センサーからのパケットを Pub-Sub パターンで配信します．

Usage:
  sharp_hmes_server.py [-c CONFIG] [-t SERIAL_PORT] [-p SERVER_PORT] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -t SERIAL_PORT    : HEMS 中継器を接続するシリアルポートを指定します． [default: /dev/ttyUSB0]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -D                : デバッグモードで動作します．
"""

import logging
import os
import pathlib
import signal

import sharp_hems.notify
import sharp_hems.serial_pubsub

SCHEMA_CONFIG = "config.schema"


def sig_handler(num, frame):  # noqa: ARG001
    logging.warning("Receive signal %d", num)

    if num == signal.SIGTERM:
        sharp_hems.serial_pubsub.stop_server()


def start():
    try:
        sharp_hems.serial_pubsub.start_server(serial_port, server_port, liveness_file)
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
    serial_port = os.environ.get("HEMS_SERIAL_PORT", args["-t"])
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    log_level = logging.DEBUG if args["-d"] else logging.INFO
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, pathlib.Path(SCHEMA_CONFIG))

    liveness_file = pathlib.Path(config["liveness"]["file"]["measure"])

    logging.info("Start server (serial: %s, port: %d)", serial_port, server_port)

    start()
