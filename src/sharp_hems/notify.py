#!/usr/bin/env python3
"""
エラーを Slack で通知します。

Usage:
  notify.py [-c CONFIG] [-D]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します。[default: config.yaml]
  -D                : デバッグモードで動作します。
"""

import logging
import traceback

import my_lib.notify.slack


def error(config):
    logging.exception("Failed.")

    if "slack" in config:
        my_lib.notify.slack.error(
            config["slack"]["bot_token"],
            config["slack"]["error"]["channel"]["name"],
            config["slack"]["from"],
            traceback.format_exc(),
            config["slack"]["error"]["interval_min"],
        )


if __name__ == "__main__":
    # TEST Code
    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-D"]

    my_lib.logger.init("test", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file)

    try:
        raise RuntimeError("ERROR")
    except Exception:
        error(config)
