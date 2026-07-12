#!/usr/bin/env python3
# ruff: noqa: S101
"""WebUI API の契約テスト (Flask test_client、InfluxDB はモック)"""

import datetime
import json
import time

import pytest

from sharp_hems.metrics.collector import MetricsCollector

URL_PREFIX = "/wattmeter-sharp/metrics"

# device.example.yaml に定義されているアドレス (リビングエアコン)
KNOWN_ADDR = "00:12:4b:00:02:1b:b9:94"
UNKNOWN_ADDR = "aa:bb:cc:dd:ee:ff:00:11"

SENSOR = "リビングエアコン"


@pytest.fixture
def client(tmp_path):
    # 合成メトリクス DB (直近 10 スロット受信)
    metrics_db = tmp_path / "metrics.db"
    collector = MetricsCollector(metrics_db)
    now = int(time.time())
    for i in range(10):
        collector.record_heartbeat(SENSOR, timestamp=now - i * 360 - 60)

    # dev_id キャッシュ (既知 1 台 + 未登録 1 台)
    cache_file = tmp_path / "dev_id.dat"
    cache_file.write_text(json.dumps({"4660": KNOWN_ADDR, "4661": UNKNOWN_ADDR}))

    config = {
        "serial": {"port": "/dev/null"},
        "fluentd": {"host": "localhost", "data": {"tag": "hems", "label": "sharp", "field": "power"}},
        "influxdb": {"url": "http://localhost:8086", "token": "DUMMY", "org": "home", "bucket": "sensor"},
        "device": {"define": "device.example.yaml", "cache": str(cache_file)},
        "metrics": {"data": str(metrics_db)},
        "webapp": {
            "timezone": {"offset": "+9", "name": "JST", "zone": "Asia/Tokyo"},
            "static_dir_path": "frontend/dist",
        },
        "liveness": {"file": {"measure": str(tmp_path / "healthz")}},
    }

    import webui

    app = webui.create_app(config)
    app.config["TESTING"] = True

    # NOTE: power API のモジュールレベルキャッシュをテスト間でリセットする
    import sharp_hems.webui.api.power

    sharp_hems.webui.api.power._cache.clear()  # noqa: SLF001

    return app.test_client()


def test_sensor_stat(client):
    response = client.get(f"{URL_PREFIX}/api/sensor_stat")
    assert response.status_code == 200

    data = response.get_json()
    assert "start_date" in data
    assert len(data["sensors"]) > 0

    by_name = {s["name"]: s for s in data["sensors"]}
    sensor = by_name[SENSOR]
    assert sensor["availability_24h"] > 0
    assert sensor["last_received_ts"] is not None
    # 受信していないデバイスは 0%
    assert by_name["冷蔵庫"]["availability_24h"] == 0.0


def test_communication_errors(client):
    response = client.get(f"{URL_PREFIX}/api/communication_errors")
    assert response.status_code == 200

    data = response.get_json()
    assert len(data["histogram"]["bins"]) == 48
    assert "latest_errors" in data


def test_devices_unknown(client):
    response = client.get(f"{URL_PREFIX}/api/devices/unknown")
    assert response.status_code == 200

    devices = response.get_json()["devices"]
    addrs = [d["addr"] for d in devices]
    assert UNKNOWN_ADDR in addrs
    assert KNOWN_ADDR not in addrs


def test_power_current(client, monkeypatch):
    import my_lib.sensor_data as sd

    async def fake_fetch(_db_config, requests):
        now = datetime.datetime.now(datetime.UTC)
        return [
            sd.SensorDataResult(value=[100.0], time=[now], valid=True, raw_record_count=1) for _ in requests
        ]

    monkeypatch.setattr(sd, "fetch_data_parallel", fake_fetch)

    response = client.get(f"{URL_PREFIX}/api/power/current")
    assert response.status_code == 200

    data = response.get_json()
    assert data["total"] == pytest.approx(100.0 * len(data["devices"]))
    assert all(d["watt"] == 100.0 for d in data["devices"])


def test_power_history(client, monkeypatch):
    import my_lib.sensor_data as sd

    base = datetime.datetime.now(datetime.UTC).replace(second=0, microsecond=0)

    async def fake_fetch(_db_config, requests):
        times = [base - datetime.timedelta(minutes=15 * i) for i in range(4)][::-1]
        return [
            sd.SensorDataResult(value=[10.0, 20.0, None, 40.0], time=times, valid=True, raw_record_count=4)
            for _ in requests
        ]

    monkeypatch.setattr(sd, "fetch_data_parallel", fake_fetch)

    response = client.get(f"{URL_PREFIX}/api/power/history?range=24h")
    assert response.status_code == 200

    data = response.get_json()
    assert data["range"] == "24h"
    assert len(data["times"]) == 4
    series = data["series"][0]
    # 欠損 (index 2) は 1 スロット以内なので直前値で補完される
    assert series["values"] == [10.0, 20.0, 20.0, 40.0]
    # 電力量は実データのみで計算される (10+20+40 = 70 → 0.25h 換算)
    assert series["energy_wh"] == pytest.approx(70 * 0.25, abs=0.01)


def test_power_history_invalid_range(client):
    response = client.get(f"{URL_PREFIX}/api/power/history?range=1y")
    assert response.status_code == 400
