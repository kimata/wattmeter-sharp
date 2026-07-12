#!/usr/bin/env python3
# ruff: noqa: S101
"""MetricsCollector (スロット計算・受信率・retention) の単体テスト"""

import datetime

import pytest

from sharp_hems.metrics.collector import SLOTS_PER_DAY, TIME_SLOT_SEC, MetricsCollector

SENSOR = "テストセンサー"

# テストの基準時刻: 2026-07-01 00:00:00 UTC (スロット境界に一致)
BASE = int(datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC).timestamp())
assert BASE % TIME_SLOT_SEC == 0


@pytest.fixture
def collector(tmp_path):
    return MetricsCollector(tmp_path / "metrics.db")


def record_slots(collector, sensor, start_ts, count, step=TIME_SLOT_SEC, skip=()):  # noqa: PLR0913
    """start_ts から step 間隔で count 回ハートビートを記録する (skip 番目は欠測)"""
    for i in range(count):
        if i in skip:
            continue
        # 境界猶予の影響を受けないようスロット中央に記録する
        collector.record_heartbeat(sensor, timestamp=start_ts + i * step + TIME_SLOT_SEC // 2)


# ---------- record_heartbeat ----------


def test_record_heartbeat_slot(collector):
    ts = BASE + TIME_SLOT_SEC // 2
    collector.record_heartbeat(SENSOR, timestamp=ts)

    assert collector.get_latest_heartbeat(SENSOR) == ts


def test_record_heartbeat_boundary_grace(collector):
    """スロット境界直後のデータは、前スロットが空いていれば前スロットに記録される"""
    boundary = BASE + TIME_SLOT_SEC * 10

    # 境界の 10 秒後 (猶予 30 秒以内) → 前スロットが空 → 前スロットに記録
    collector.record_heartbeat(SENSOR, timestamp=boundary + 10)

    with collector.get_connection() as conn:
        slots = [row[0] for row in conn.execute("SELECT time_slot FROM sensor_heartbeats")]
    assert slots == [boundary // TIME_SLOT_SEC - 1]

    # 同じ境界直後にもう 1 件 → 前スロットは埋まっている → 現在のスロットに記録
    collector.record_heartbeat(SENSOR, timestamp=boundary + 20)
    with collector.get_connection() as conn:
        slots = sorted(row[0] for row in conn.execute("SELECT time_slot FROM sensor_heartbeats"))
    assert slots == [boundary // TIME_SLOT_SEC - 1, boundary // TIME_SLOT_SEC]


# ---------- 通信エラー検出 ----------


def test_detect_communication_errors(collector):
    # スロット 0, 1 受信 → 2, 3 欠測 → 4 受信
    record_slots(collector, SENSOR, BASE, 5, skip=(2, 3))

    errors = collector.get_latest_communication_errors()
    error_slots = sorted(e["timestamp"] // TIME_SLOT_SEC for e in errors)
    assert error_slots == [BASE // TIME_SLOT_SEC + 2, BASE // TIME_SLOT_SEC + 3]


def test_detect_communication_errors_long_gap(collector):
    """5 スロットを超える欠測 (長期切断) はエラーとして記録しない"""
    record_slots(collector, SENSOR, BASE, 1)
    # 10 スロット後に受信再開
    record_slots(collector, SENSOR, BASE + 10 * TIME_SLOT_SEC, 1)

    assert collector.get_latest_communication_errors() == []


# ---------- 受信率 ----------


def test_availability_between_full(collector):
    record_slots(collector, SENSOR, BASE, 10)
    end = BASE + 10 * TIME_SLOT_SEC

    assert collector.calculate_availability_between(SENSOR, BASE, end) == 100.0


def test_availability_between_partial(collector):
    record_slots(collector, SENSOR, BASE, 10, skip=(1, 3, 5, 7, 9))
    end = BASE + 10 * TIME_SLOT_SEC

    # 期待 10 スロット (現在スロットは受信なしのため含まない) 中 5 受信
    availability = collector.calculate_availability_between(SENSOR, BASE, end)
    assert availability == pytest.approx(50.0, abs=0.01)


def test_availability_between_no_data(collector):
    assert collector.calculate_availability_between(SENSOR, BASE, BASE + 86400) == 0.0


def test_availability_starts_from_first_data(collector):
    """期間よりデータ開始が遅い場合、データ開始以降のみを期待値とする"""
    start = BASE + 5 * TIME_SLOT_SEC
    record_slots(collector, SENSOR, start, 5)
    end = start + 5 * TIME_SLOT_SEC

    # BASE からの期間を指定しても、データ開始 (start) 以降で計算され 100% になる
    assert collector.calculate_availability_between(SENSOR, BASE, end) == 100.0


# ---------- retention (日次サマリーへの畳み込み) ----------


def test_cleanup_folds_old_heartbeats(collector):
    # 40 日前から 3 日分 (全スロット受信) + 現在まで少量
    old_start = BASE
    record_slots(collector, SENSOR, old_start, SLOTS_PER_DAY * 3)

    now = BASE + 40 * 86400
    record_slots(collector, SENSOR, now - 2 * TIME_SLOT_SEC, 2)

    total_before = collector.calculate_total_availability(SENSOR, now)

    collector.cleanup(retention_days=30, now=now)

    # 古いハートビートは削除され、日次サマリーに畳み込まれている
    with collector.get_connection() as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM sensor_heartbeats").fetchone()[0]
        summaries = conn.execute(
            "SELECT date, total_expected, total_received FROM sensor_availability ORDER BY date"
        ).fetchall()

    assert remaining == 2
    # データのあった 3 日分 + データ開始後の完全欠測日 (received=0) がサマリー化される
    assert len(summaries) == 10
    assert all(expected == SLOTS_PER_DAY for _, expected, _ in summaries)
    assert [received for _, _, received in summaries[:3]] == [SLOTS_PER_DAY] * 3
    assert all(received == 0 for _, _, received in summaries[3:])

    # 累計受信率は畳み込みの前後でほぼ変わらない
    total_after = collector.calculate_total_availability(SENSOR, now)
    assert total_after == pytest.approx(total_before, abs=0.1)


def test_cleanup_records_empty_days(collector):
    """データが 1 件も無い日も received=0 のサマリーが残ること (受信率の水増し防止)"""
    # 1 日目は受信、2 日目は完全欠測、3 日目は受信
    record_slots(collector, SENSOR, BASE, SLOTS_PER_DAY)
    record_slots(collector, SENSOR, BASE + 2 * 86400, SLOTS_PER_DAY)

    now = BASE + 40 * 86400
    collector.cleanup(retention_days=30, now=now)

    with collector.get_connection() as conn:
        summaries = dict(conn.execute("SELECT date, total_received FROM sensor_availability").fetchall())

    assert summaries["2026-07-01"] == SLOTS_PER_DAY
    assert summaries["2026-07-02"] == 0
    assert summaries["2026-07-03"] == SLOTS_PER_DAY


def test_cleanup_noop_when_no_old_data(collector):
    record_slots(collector, SENSOR, BASE, 5)

    collector.cleanup(retention_days=30, now=BASE + 86400)

    with collector.get_connection() as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM sensor_heartbeats").fetchone()[0]
        summaries = conn.execute("SELECT COUNT(*) FROM sensor_availability").fetchone()[0]

    assert remaining == 5
    assert summaries == 0


def test_start_date_prefers_summary(collector):
    record_slots(collector, SENSOR, BASE, SLOTS_PER_DAY)
    now = BASE + 40 * 86400
    record_slots(collector, SENSOR, now - TIME_SLOT_SEC, 1)

    assert collector.get_start_date() == "2026-07-01"

    collector.cleanup(retention_days=30, now=now)

    # 畳み込み後もサマリーから開始日が取得できる
    assert collector.get_start_date() == "2026-07-01"


# ---------- ヒストグラム ----------


def test_histogram_counts_errors(collector):
    record_slots(collector, SENSOR, BASE, 5, skip=(2,))

    import time as time_module

    # ヒストグラムは現在時刻から遡るため、十分大きい hours を指定
    hours = int((time_module.time() - BASE) / 3600) + 24
    histogram = collector.get_communication_errors_histogram(hours=hours)

    assert histogram["total_errors"] == 1
    assert sum(histogram["bins"]) == 1
