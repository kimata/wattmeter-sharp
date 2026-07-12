#!/usr/bin/env python3
"""
センサーのシリアル出力をダンプします。

Usage:
  sharp_hems_dump.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-o FILE] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します。 [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します。 [default: 4444]
  -o FILE           : 出力ファイル名 [default: packet.dump]
  -D                : デバッグモードで動作します。
"""

import logging
import os
import time

import sharp_hems.config
import sharp_hems.notify
import sharp_hems.packet_dump
import sharp_hems.serial_pubsub

start_time = None
packet_count = 0


def process_packet(handle, header, payload):
    global start_time  # noqa: PLW0603
    global packet_count  # noqa: PLW0603

    now = time.time()
    if start_time is None:
        start_time = now

    # NOTE: 1 行 = 1 パケットの追記形式なので、長時間のキャプチャでも
    # 書き込み量はパケット数に比例する
    sharp_hems.packet_dump.append(handle["dump_file"], now - start_time, header, payload)

    packet_count += 1
    logging.info("Receive %d packet(s)", packet_count)


def start(handle, server_host, server_port, config):
    try:
        sharp_hems.serial_pubsub.start_client(server_host, server_port, handle, process_packet)
    except Exception:
        sharp_hems.notify.error(config)
        raise


######################################################################
def main():
    import docopt
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    server_host = os.environ.get("HEMS_SERVER_HOST", args["-s"])
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    dump_file = args["-o"]
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = sharp_hems.config.load(config_file)

    logging.info("Start HEMS dump (server: %s:%d, output: %s)", server_host, server_port, dump_file)

    start({"dump_file": dump_file}, server_host, server_port, config)


if __name__ == "__main__":
    main()
