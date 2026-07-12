#!/usr/bin/env python3
"""device.yaml で定義されたデバイス一覧を管理します。"""

import logging
import pathlib

import my_lib.config

import sharp_hems.config


class DeviceRegistry:
    """device.yaml のロードとアドレス⇔名前の解決を行う (mtime キャッシュ付き)。"""

    def __init__(self):
        """レジストリを初期化します。"""
        self._dev_list = []
        self._mtime = None
        self._by_addr = {}

    def reload(self, dev_define_file):
        dev_define_file = pathlib.Path(dev_define_file)

        mtime = dev_define_file.stat().st_mtime
        if self._mtime == mtime:
            return self._dev_list

        logging.info("Load device list...")

        self._dev_list = sharp_hems.config.validate_device_list(my_lib.config.load(dev_define_file))
        self._by_addr = {dev_info["addr"].lower(): dev_info for dev_info in self._dev_list}
        self._mtime = mtime

        return self._dev_list

    def get_name(self, addr):
        dev_info = self._by_addr.get(addr.lower())
        return dev_info["name"] if dev_info is not None else None

    def get_scale(self, addr):
        """デバイス毎の電力倍率 (未定義なら None)。"""
        dev_info = self._by_addr.get(addr.lower())
        return dev_info.get("scale") if dev_info is not None else None

    def get_list(self):
        return [dev_info["name"] for dev_info in self._dev_list]


# NOTE: 互換のためのモジュールレベル API (既定のレジストリに委譲)
_default_registry = DeviceRegistry()


def reload(dev_define_file):
    return _default_registry.reload(dev_define_file)


def get_name(addr):
    return _default_registry.get_name(addr)


def get_scale(addr):
    return _default_registry.get_scale(addr)


def get_list():
    return _default_registry.get_list()
