#!/usr/bin/env python3
"""
デバイスの無応答を監視し、切断・復帰を通知します。

logger のデータ受信ループから定期的に check() を呼び出す前提。
最後の受信からの経過時間がしきい値を超えたら切断アラートを送り、
受信が再開したら復帰通知を送る。
"""

import logging
import time

import sharp_hems.device
import sharp_hems.notify

# 無応答と判定するまでの時間 (分)。センサーの送信周期は約 6 分。
TIMEOUT_MIN_DEFAULT = 30

# check() の最短実行間隔 (秒)
CHECK_INTERVAL_SEC = 60


class DeviceWatchdog:
    """デバイス毎の最終受信時刻を監視して切断・復帰を通知する。"""

    def __init__(self, config, collector, timeout_min=TIMEOUT_MIN_DEFAULT):
        """監視対象の設定と通知先を初期化します。"""
        self.config = config
        self.collector = collector
        self.timeout_sec = timeout_min * 60
        self.alerted = set()
        self._last_check = 0.0

    def check(self, now=None):
        """全デバイスの無応答をチェックし、状態変化があれば通知する。"""
        if now is None:
            now = time.time()

        if now - self._last_check < CHECK_INTERVAL_SEC:
            return
        self._last_check = now

        for name in sharp_hems.device.get_list():
            try:
                self._check_device(name, now)
            except Exception:
                logging.exception("Failed to check device: %s", name)

    def _check_device(self, name, now):
        last_received = self.collector.get_latest_heartbeat(name)

        if last_received is None:
            # 一度も受信していないデバイスは対象外 (登録直後の誤報を避ける)
            return

        age = now - last_received

        if age > self.timeout_sec:
            if name not in self.alerted:
                self.alerted.add(name)
                sharp_hems.notify.alert(
                    self.config,
                    f"⚠️ 「{name}」から {int(age / 60)} 分間データを受信できていません。"
                    f"電源やワイヤレス接続を確認してください。",
                )
        elif name in self.alerted:
            self.alerted.discard(name)
            sharp_hems.notify.alert(self.config, f"✅ 「{name}」の受信が回復しました。")
