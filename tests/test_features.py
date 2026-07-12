#!/usr/bin/env python3
# ruff: noqa: S101
"""watchdog (F-1) と calibrate (F-7) の単体テスト"""

import pytest

import sharp_hems.device
import sharp_hems.notify
from sharp_hems.watchdog import DeviceWatchdog

NOW = 1_800_000_000


class FakeCollector:
    def __init__(self, last_received):
        """センサー毎の最終受信時刻を保持します。"""
        self.last_received = last_received

    def get_latest_heartbeat(self, sensor_name):
        return self.last_received.get(sensor_name)


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(sharp_hems.notify, "alert", lambda _config, message: sent.append(message))
    monkeypatch.setattr(sharp_hems.device, "get_list", lambda: ["エアコン", "冷蔵庫"])
    return sent


def make_watchdog(collector, timeout_min=30):
    watchdog = DeviceWatchdog({}, collector, timeout_min=timeout_min)
    watchdog._last_check = 0.0  # noqa: SLF001
    return watchdog


def test_watchdog_alerts_on_timeout(alerts):
    collector = FakeCollector({"エアコン": NOW - 2 * 3600, "冷蔵庫": NOW - 60})
    watchdog = make_watchdog(collector)

    watchdog.check(now=NOW)

    assert len(alerts) == 1
    assert "エアコン" in alerts[0]
    assert "受信できていません" in alerts[0]


def test_watchdog_alerts_only_once(alerts):
    collector = FakeCollector({"エアコン": NOW - 2 * 3600, "冷蔵庫": NOW - 60})
    watchdog = make_watchdog(collector)

    watchdog.check(now=NOW)
    watchdog._last_check = 0.0  # noqa: SLF001
    watchdog.check(now=NOW + 120)

    assert len(alerts) == 1  # 2 回目のチェックでは再通知しない


def test_watchdog_notifies_recovery(alerts):
    collector = FakeCollector({"エアコン": NOW - 2 * 3600, "冷蔵庫": NOW - 60})
    watchdog = make_watchdog(collector)
    watchdog.check(now=NOW)

    # 受信が回復
    collector.last_received["エアコン"] = NOW + 300
    watchdog._last_check = 0.0  # noqa: SLF001
    watchdog.check(now=NOW + 360)

    assert len(alerts) == 2
    assert "回復" in alerts[1]


def test_watchdog_ignores_never_seen_device(alerts):
    collector = FakeCollector({"冷蔵庫": NOW - 60})  # エアコンは一度も受信なし
    watchdog = make_watchdog(collector)

    watchdog.check(now=NOW)

    assert alerts == []


def test_watchdog_throttles_check(alerts):
    collector = FakeCollector({"エアコン": NOW - 2 * 3600})
    watchdog = make_watchdog(collector)

    watchdog.check(now=NOW)
    # 60 秒以内の再チェックはスキップされる (状態は変わらない)
    collector.last_received["エアコン"] = NOW
    watchdog.check(now=NOW + 10)

    assert len(alerts) == 1


# ---------- calibrate ----------


def test_compute_scale():
    from sharp_hems_calibrate import compute_scale

    # 実測がプラグ合計の 1.2 倍 → 倍率も 1.2 倍
    wattmeter = [100.0, 200.0, 300.0]
    smartmeter = [120.0, 240.0, 360.0]

    scale, samples = compute_scale(1.5, wattmeter, smartmeter)
    assert scale == pytest.approx(1.8)
    assert samples == 3


def test_compute_scale_skips_missing():
    from sharp_hems_calibrate import compute_scale

    wattmeter = [100.0, None, 300.0, 0.0]
    smartmeter = [110.0, 240.0, None, 400.0]

    scale, samples = compute_scale(1.0, wattmeter, smartmeter)
    assert samples == 1
    assert scale == pytest.approx(1.1)


def test_compute_scale_no_pairs():
    from sharp_hems_calibrate import compute_scale

    scale, samples = compute_scale(1.5, [None], [None])
    assert scale is None
    assert samples == 0
