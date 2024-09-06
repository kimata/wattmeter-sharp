#!/usr/bin/env python3
import logging
import traceback

import my_lib.notify_slack


def error(config):
    logging.exception("Failed.")

    if "slack" in config:
        my_lib.notify_slack.error(
            config["slack"]["bot_token"],
            config["slack"]["error"]["channel"]["name"],
            config["slack"]["from"],
            traceback.format_exc(),
            config["slack"]["error"]["interval_min"],
        )
