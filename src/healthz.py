#!/usr/bin/env python3
"""
Liveness のチェックを行います

Usage:
  healthz.py [-c CONFIG] [-p PORT] [-p SERVER_PORT] [-D]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します．[default: config.yaml]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -D                : デバッグモードで動作します．
"""

import logging
import pathlib
import sys

import my_lib.healthz


def check_liveness(target_list, port=None):
    for target in target_list:
        if not my_lib.healthz.check_liveness(target["name"], target["liveness_file"], target["interval"]):
            return False

    if port is not None:
        return my_lib.healthz.check_port(port)
    else:
        return True


######################################################################
if __name__ == "__main__":
    import os

    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    port = args["-p"]
    server_port = int(os.environ.get("HEMS_SERVER_PORT", args["-p"]))
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file)

    target_list = [
        {
            "name": name,
            "liveness_file": pathlib.Path(config["liveness"]["file"][name]),
            "interval": 6 * 60,  # NOTE: 6分間隔でパケットが飛んでくる
        }
        for name in ["measure"]
    ]

    if check_liveness(target_list, server_port):
        logging.info("OK.")
        sys.exit(0)
    else:
        sys.exit(-1)
