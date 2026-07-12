#!/usr/bin/env python3
"""
エラーやアラートを Slack で通知します。

Usage:
  notify.py [-c CONFIG] [-D]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します。[default: config.yaml]
  -D                : デバッグモードで動作します。
"""

import logging
import traceback

import my_lib.notify.slack

NOTIFY_TITLE = "wattmeter-sharp"


def _parse_slack_config(config):
    return my_lib.notify.slack.SlackConfig.parse(config.get("slack", {}))


def error(config):
    logging.exception("Failed.")

    my_lib.notify.slack.error(_parse_slack_config(config), NOTIFY_TITLE, traceback.format_exc())


def alert(config, message):
    """デバイスの切断・復帰などのアラートを通知する。"""
    logging.warning("Alert: %s", message)

    slack_config = _parse_slack_config(config)
    if isinstance(slack_config, my_lib.notify.slack.SlackEmptyConfig):
        logging.warning("Slack is not configured, skip alert")
        return

    # NOTE: info チャンネルが設定されていればそちらへ、無ければ error チャンネルへ
    if getattr(slack_config, "info", None) is not None:
        my_lib.notify.slack.info(slack_config, NOTIFY_TITLE, message)
    else:
        my_lib.notify.slack.error(slack_config, NOTIFY_TITLE, message)


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
