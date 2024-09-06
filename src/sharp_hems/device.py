#!/usr/bin/env python3
import logging

import my_lib.config

addr_list_cache = None
dev_config_mtime = None
addr_list = []


def get_name(addr):
    global addr_list

    for dev_info in addr_list:
        if dev_info["addr"].lower() == addr.lower():
            return dev_info["name"]
    return None


def get_list():
    global addr_list

    return [dev_info["name"] for dev_info in addr_list]


def reload(dev_config_file):
    global addr_list  # noqa: PLW0603
    global addr_list_cache  # noqa: PLW0603
    global dev_config_mtime  # noqa: PLW0603

    if (dev_config_mtime is not None) and (dev_config_mtime == dev_config_file.stat().st_mtime):
        return addr_list_cache

    logging.info("Load device list...")

    addr_list = my_lib.config.load(dev_config_file)
    addr_list_cache = addr_list
    dev_config_mtime = dev_config_file.stat().st_mtime

    return addr_list
