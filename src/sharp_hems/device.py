#!/usr/bin/env python3
import logging
import pathlib

import my_lib.config

SCHEMA_DEVICE = "device.schema"

addr_list_cache = None
dev_define_mtime = None
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


def reload(dev_define_file):
    global addr_list  # noqa: PLW0603
    global addr_list_cache  # noqa: PLW0603
    global dev_define_mtime  # noqa: PLW0603

    if (dev_define_mtime is not None) and (dev_define_mtime == dev_define_file.stat().st_mtime):
        return addr_list_cache

    logging.info("Load device list...")

    addr_list = my_lib.config.load(dev_define_file, pathlib.Path(SCHEMA_DEVICE))
    my_lib.config.load(dev_define_file)

    addr_list_cache = addr_list
    dev_define_mtime = dev_define_file.stat().st_mtime

    return addr_list
