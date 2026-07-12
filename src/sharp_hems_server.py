#!/usr/bin/env python3
"""
センサーからのパケットを Pub-Sub パターンで配信します。

Usage:
  sharp_hems_server.py [-c CONFIG] [-t SERIAL_PORT] [-p SERVER_PORT] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -t SERIAL_PORT    : HEMS 中継器を接続するシリアルポートを指定します。 [default: /dev/ttyUSB0]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します。 [default: 4444]
  -D                : デバッグモードで動作します。
"""

import logging
import os
import pathlib
import signal

import sharp_hems.config
import sharp_hems.notify
import sharp_hems.serial_pubsub


def sig_handler(num, frame):  # noqa: ARG001
    logging.warning("Receive signal %d", num)

    if num in (signal.SIGTERM, signal.SIGINT):
        sharp_hems.serial_pubsub.stop_server()


def start(serial_port, server_port, liveness_file, config):
    try:
        sharp_hems.serial_pubsub.start_server(serial_port, server_port, liveness_file)
    except Exception:
        sharp_hems.notify.error(config)
        raise


######################################################################
def main():
    import docopt
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    serial_port = os.environ.get("HEMS_SERIAL_PORT", args["-t"])
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = sharp_hems.config.load(config_file)

    liveness_file = pathlib.Path(config["liveness"]["file"]["measure"])

    logging.info("Start server (serial: %s, port: %d)", serial_port, server_port)

    start(serial_port, server_port, liveness_file, config)


if __name__ == "__main__":
    main()
