#!/usr/bin/env python3
# ruff: noqa: S101
"""sniffer (パケット解析) と serial_pubsub (フレーミング) の単体テスト"""

import json
import pickle
import struct

import pytest

from sharp_hems.sniffer import (
    PACKET_TYPE_DEV_ID,
    PACKET_TYPE_IEEE_ADDR,
    PACKET_TYPE_MEASURE,
    PacketSniffer,
)

ADDR_A = "00:12:4B:00:00:00:00:0A"
ADDR_B = "00:12:4B:00:00:00:00:0B"


# ---------- パケットビルダー ----------


def build_ieee_addr_packet(addr):
    payload_len = PACKET_TYPE_IEEE_ADDR + 3
    packet = bytearray(2 + payload_len)
    packet[0] = 0xFE
    packet[1] = PACKET_TYPE_IEEE_ADDR
    addr_bytes = bytes(int(x, 16) for x in reversed(addr.split(":")))
    packet[4:12] = addr_bytes
    return bytes(packet[:2]), bytes(packet[2:])


def build_dev_id_packet(dev_id, index):
    payload_len = PACKET_TYPE_DEV_ID + 3
    packet = bytearray(2 + payload_len)
    packet[0] = 0xFE
    packet[1] = PACKET_TYPE_DEV_ID
    struct.pack_into("<H", packet, 4, dev_id)
    packet[6] = index
    return bytes(packet[:2]), bytes(packet[2:])


def build_measure_packet(dev_id, counter=1, cur_time=100, cur_power=1000, pre_time=40, pre_power=400):  # noqa: PLR0913
    payload_len = PACKET_TYPE_MEASURE + 3
    packet = bytearray(2 + payload_len)
    packet[0] = 0xFE
    packet[1] = PACKET_TYPE_MEASURE
    struct.pack_into("<H", packet, 5, dev_id)
    packet[14] = counter
    struct.pack_into("<H", packet, 19, cur_time)
    struct.pack_into("<I", packet, 26, cur_power)
    struct.pack_into("<H", packet, 35, pre_time)
    struct.pack_into("<I", packet, 42, pre_power)
    return bytes(packet[:2]), bytes(packet[2:])


@pytest.fixture
def sniffer(tmp_path):
    return PacketSniffer(tmp_path / "dev_id.dat", watt_scale=1.0)


def capture(sniffer, header, payload):
    captured = []
    sniffer.process(header, payload, captured.append)
    return captured


# ---------- 計測値の復元 ----------


def test_measure_basic(sniffer):
    sniffer.dev_id_map = {0x1234: ADDR_A}

    # 600 秒間に 600 電力増 → 1.0 W (scale=1.0)
    header, payload = build_measure_packet(
        0x1234, counter=1, cur_time=700, cur_power=1000, pre_time=100, pre_power=400
    )
    captured = capture(sniffer, header, payload)

    assert len(captured) == 1
    assert captured[0]["addr"] == ADDR_A
    assert captured[0]["watt"] == 1.0


def test_measure_duplicate_counter(sniffer):
    sniffer.dev_id_map = {0x1234: ADDR_A}

    header, payload = build_measure_packet(0x1234, counter=5)
    assert len(capture(sniffer, header, payload)) == 1
    # 同一カウンタの再送は棄却される
    assert len(capture(sniffer, header, payload)) == 0
    # カウンタが進めば受理される
    header, payload = build_measure_packet(0x1234, counter=6)
    assert len(capture(sniffer, header, payload)) == 1


def test_measure_time_wrap(sniffer):
    sniffer.dev_id_map = {0x1234: ADDR_A}

    # cur_time が 16bit で折り返すケース: 0xFF00 → 0x0100 (経過 512)
    header, payload = build_measure_packet(
        0x1234, counter=1, cur_time=0x0100, cur_power=1024, pre_time=0xFF00, pre_power=512
    )
    captured = capture(sniffer, header, payload)
    assert captured[0]["watt"] == 1.0


def test_measure_unknown_dev_id(sniffer):
    header, payload = build_measure_packet(0x9999)
    captured = capture(sniffer, header, payload)
    assert captured[0]["addr"] == "UNKNOWN"


def test_measure_scale(tmp_path):
    scale_map = {ADDR_A: 2.0}
    sniffer = PacketSniffer(tmp_path / "dev_id.dat", watt_scale=1.5, scale_resolver=scale_map.get)
    sniffer.dev_id_map = {0x0001: ADDR_A, 0x0002: ADDR_B}

    header, payload = build_measure_packet(
        0x0001, counter=1, cur_time=700, cur_power=1000, pre_time=100, pre_power=400
    )
    assert capture(sniffer, header, payload)[0]["watt"] == 2.0  # デバイス固有の倍率

    header, payload = build_measure_packet(
        0x0002, counter=1, cur_time=700, cur_power=1000, pre_time=100, pre_power=400
    )
    assert capture(sniffer, header, payload)[0]["watt"] == 1.5  # グローバル倍率


# ---------- dev_id と IEEE アドレスのマッピング ----------


def process_cycle(sniffer, addr_list, dev_id_list):
    for addr in addr_list:
        header, payload = build_ieee_addr_packet(addr)
        sniffer.process(header, payload, lambda _: None)
    for index, dev_id in enumerate(dev_id_list):
        if dev_id is None:
            continue
        header, payload = build_dev_id_packet(dev_id, index)
        sniffer.process(header, payload, lambda _: None)


def test_mapping_basic(sniffer):
    process_cycle(sniffer, [ADDR_A, ADDR_B], [0x0001, 0x0002])

    assert sniffer.dev_id_map == {0x0001: ADDR_A, 0x0002: ADDR_B}
    assert sniffer.ieee_addr_list == []  # 最後の 0x12 でクリアされる


def test_mapping_survives_lost_last_dev_id(sniffer):
    """最後の 0x12 を取りこぼしても、次周期で誤マッピングしないこと (B-5)"""
    # 周期1: 最後の dev_id (index=1) をロスト → リストが残留する
    process_cycle(sniffer, [ADDR_A, ADDR_B], [0x0001, None])
    assert len(sniffer.ieee_addr_list) == 2

    # 周期2: 順序が入れ替わった状態で全パケット受信
    process_cycle(sniffer, [ADDR_B, ADDR_A], [0x0002, 0x0001])

    # 周期1 の残留リストに index がずれて適用されないこと
    assert sniffer.dev_id_map == {0x0002: ADDR_B, 0x0001: ADDR_A}


def test_mapping_discards_cycle_on_lost_ieee_addr(sniffer):
    """0x08 の取りこぼしで index が範囲外になった周期は破棄されること"""
    sniffer.dev_id_map = {}

    # 0x08 が 1 件しか届いていないのに index=1 の 0x12 が来た
    header, payload = build_ieee_addr_packet(ADDR_A)
    sniffer.process(header, payload, lambda _: None)
    header, payload = build_dev_id_packet(0x0002, 1)
    sniffer.process(header, payload, lambda _: None)

    assert sniffer.dev_id_map == {}
    assert sniffer.ieee_addr_list == []


# ---------- dev_id キャッシュの永続化 ----------


def test_dev_id_cache_json_roundtrip(tmp_path):
    cache_file = tmp_path / "dev_id.dat"

    sniffer = PacketSniffer(cache_file)
    process_cycle(sniffer, [ADDR_A], [0x0001])

    # JSON として保存されている
    stored = json.loads(cache_file.read_text())
    assert stored == {"1": ADDR_A}

    # 新しいインスタンスで読み戻せる (キーは int に復元)
    sniffer2 = PacketSniffer(cache_file)
    assert sniffer2.dev_id_map == {0x0001: ADDR_A}


def test_dev_id_cache_pickle_migration(tmp_path):
    """旧フォーマット (pickle) から JSON へ移行されること (R-5)"""
    cache_file = tmp_path / "dev_id.dat"
    with cache_file.open("wb") as f:
        pickle.dump({0x0001: ADDR_A}, f)

    sniffer = PacketSniffer(cache_file)
    assert sniffer.dev_id_map == {0x0001: ADDR_A}

    # ファイルは JSON に書き換わっている
    assert json.loads(cache_file.read_text()) == {"1": ADDR_A}


def test_dev_id_cache_broken_file(tmp_path):
    cache_file = tmp_path / "dev_id.dat"
    cache_file.write_bytes(b"\x80broken")

    sniffer = PacketSniffer(cache_file)
    assert sniffer.dev_id_map == {}


# ---------- シリアルフレーミング (B-4) ----------


class FakeSerial:
    def __init__(self, stream):
        """テスト用のバイト列を保持します。"""
        self.stream = stream
        self.pos = 0

    def read(self, size):
        data = self.stream[self.pos : self.pos + size]
        self.pos += len(data)
        return data


def read_all_packets(stream):
    import sharp_hems.serial_pubsub

    ser = FakeSerial(stream)
    packets = []
    # FakeSerial は末尾に達すると空バイトを返す (タイムアウト相当)
    for _ in range(len(stream) + 8):
        packet = sharp_hems.serial_pubsub.read_packet(ser)
        if packet is not None:
            packets.append(packet)
    return packets


def test_read_packet_normal():
    h1, p1 = build_ieee_addr_packet(ADDR_A)
    h2, p2 = build_measure_packet(0x0001)

    packets = read_all_packets(h1 + p1 + h2 + p2)

    assert packets == [(h1, p1), (h2, p2)]


def test_read_packet_resync_after_garbage():
    """先頭にゴミバイトがあっても同期バイトで再同期できること"""
    h1, p1 = build_ieee_addr_packet(ADDR_A)

    packets = read_all_packets(b"\x00\x12\x34" + h1 + p1)

    assert packets == [(h1, p1)]


def test_read_packet_discards_short_payload():
    """途切れたパケットは破棄し、後続のパケットは正しく読めること"""
    h1, p1 = build_ieee_addr_packet(ADDR_A)
    h2, p2 = build_measure_packet(0x0001)

    # h1 のペイロードが途中で途切れている (残りはタイムアウトで尽きる)
    packets = read_all_packets(h1 + p1[:3])
    assert packets == []

    # 途切れの後に完全なパケットが続く場合、ペイロード読みが後続を食うが
    # 再同期によりストリームは最終的に回復する (h2 は 0xFE 開始)
    stream = h1 + p1[:3] + h2 + p2 + h2 + p2
    packets = read_all_packets(stream)
    assert (h2, p2) in packets
