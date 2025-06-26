#!/usr/bin/env python3
"""
センサーのシリアル出力をダンプします。

Usage:
  sharp_hmes_dump.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-o FILE] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します。 [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します。 [default: 4444]
  -o FILE           : 出力ファイル名 [default: packet.dump]
  -D                : デバッグモードで動作します。
"""

import logging
import os
import pathlib
import time

import my_lib.fluentd_util
import my_lib.footprint
import my_lib.serializer

import sharp_hems.device
import sharp_hems.notify
import sharp_hems.serial_pubsub
import sharp_hems.sniffer

SCHEMA_CONFIG = "config.schema"

start_time = None
packet_list = []


def process_packet(handle, header, payload):
    global start_time  # noqa: PLW0603
    global packet_list

    now = time.time()
    if start_time is None:
        start_time = now

    packet_list.append([now - start_time, header, payload])
    logging.info("Receive %d packet(s) ", len(packet_list))

    my_lib.serializer.store(handle["dump_file"], packet_list)


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
    dump_file = args["-o"]
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, pathlib.Path(SCHEMA_CONFIG))

    dev_define_file = pathlib.Path(config["device"]["define"])
    dev_cache_file = pathlib.Path(config["device"]["cache"])
    liveness_file = pathlib.Path(config["liveness"]["file"]["measure"])

    logging.info("Start HEMS logger (server: %s:%d)", server_host, server_port)

    logging.info(
        "Initialize Fluentd sender (host: %s, tag: %s)",
        config["fluentd"]["host"],
        config["fluentd"]["data"]["tag"],
    )
    sender = my_lib.fluentd_util.get_handle(config["fluentd"]["data"]["tag"], host=config["fluentd"]["host"])

    start(
        {
            "sender": sender,
            "dump_file": dump_file,
        }
    )
