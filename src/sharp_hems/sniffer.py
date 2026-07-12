#!/usr/bin/env python3
"""JH-AG01 のシリアルパケットを解析して、電力センサーの計測値を復元します。"""

import json
import logging
import pathlib
import pickle
import struct

# 電力に掛けるデフォルトの倍率
# NOTE:
# 電力会社のスマートメータの読み値と比較すると常に電力が小さいので、
# 一定の倍率を掛ける。config.yaml の sensor.watt_scale、および
# device.yaml のデバイス毎の scale で変更できる。
WATT_SCALE_DEFAULT = 1.5

PACKET_TYPE_IEEE_ADDR = 0x08
PACKET_TYPE_DEV_ID = 0x12
PACKET_TYPE_MEASURE = 0x2C


def dump_packet(data):
    return ",".join(f"{x:02X}" for x in list(data))


def parse_packet_ieee_addr(packet):
    return ":".join(f"{x:02X}" for x in reversed(list(packet[4:12])))


def read_dev_id_map(dev_cache_file):
    """
    dev_id キャッシュを読み込み、(dev_id_map, is_legacy_format) を返す。

    JSON 形式を優先し、旧フォーマット (pickle) にもフォールバックする。
    """
    dev_cache_file = pathlib.Path(dev_cache_file)
    if not dev_cache_file.exists():
        return {}, False

    raw = dev_cache_file.read_bytes()

    try:
        return {int(dev_id): addr for dev_id, addr in json.loads(raw).items()}, False
    except (ValueError, UnicodeDecodeError):
        pass

    return pickle.loads(raw), True  # noqa: S301


def parse_packet_dev_id(packet):
    dev_id = struct.unpack("<H", packet[4:6])[0]
    index = packet[6]

    return {
        "dev_id": dev_id,
        "index": index,
    }


class PacketSniffer:
    """
    パケット列から dev_id と IEEE アドレスの対応を学習し、計測値を復元する。

    JH-AG01 は周期的に「IEEE アドレス通知 (0x08) の列 → dev_id 通知 (0x12) の列」を
    送信するため、その順序対応からマッピングを構築する。
    """

    def __init__(self, dev_cache_file, watt_scale=WATT_SCALE_DEFAULT, scale_resolver=None):
        """スニッファを初期化します。"""
        self.dev_cache_file = pathlib.Path(dev_cache_file)
        self.watt_scale = watt_scale
        # NOTE: IEEE アドレスからデバイス固有の倍率を返す callable (無ければ None)
        self.scale_resolver = scale_resolver

        self.dev_id_map = self._load_dev_id_map()
        self.counter_hist = {}
        self.ieee_addr_list = []
        self.last_packet_type = None

    # ---------- dev_id キャッシュ ----------

    def _load_dev_id_map(self):
        try:
            dev_id_map, is_legacy = read_dev_id_map(self.dev_cache_file)
        except Exception:
            logging.exception("Failed to load dev_id_map, starting fresh")
            return {}

        if is_legacy:
            # NOTE: 旧フォーマット (pickle) からの移行
            logging.info("Migrate dev_id_map from pickle to JSON")
            self._store_dev_id_map(dev_id_map)

        return dev_id_map

    def _store_dev_id_map(self, dev_id_map=None):
        if dev_id_map is None:
            dev_id_map = self.dev_id_map

        logging.info("Store dev_id_map")

        # NOTE: プロセス異常終了によるファイル破損を避けるためアトミックに書き込む
        tmp_file = self.dev_cache_file.with_name(self.dev_cache_file.name + ".tmp")
        tmp_file.write_text(json.dumps({str(dev_id): addr for dev_id, addr in dev_id_map.items()}, indent=2))
        tmp_file.replace(self.dev_cache_file)

    # ---------- パケット処理 ----------

    def process(self, header, payload, on_capture):
        packet_type = header[1]

        try:
            if packet_type == PACKET_TYPE_IEEE_ADDR:
                self._process_ieee_addr(header, payload)
            elif packet_type == PACKET_TYPE_DEV_ID:
                self._process_dev_id(header, payload)
            elif packet_type == PACKET_TYPE_MEASURE:
                self._process_measure(header, payload, on_capture)
            else:
                logging.debug("Unknown packet: %s", dump_packet(header + payload))
        finally:
            self.last_packet_type = packet_type

    def _process_ieee_addr(self, header, payload):
        logging.debug("IEEE addr payload: %s", dump_packet(payload))

        # NOTE: 0x08 の列の先頭 = 新しい通知周期の開始とみなしてリストをリセットする。
        # 前周期の最後の 0x12 を取りこぼしても、ここで古いエントリが破棄されるため
        # index とアドレスの対応がずれない。
        if self.last_packet_type != PACKET_TYPE_IEEE_ADDR and self.ieee_addr_list:
            logging.debug("Reset IEEE addr list (new cycle)")
            self.ieee_addr_list = []

        self.ieee_addr_list.append(parse_packet_ieee_addr(header + payload))

    def _process_dev_id(self, header, payload):
        logging.debug("Dev ID payload: %s", dump_packet(payload))
        data = parse_packet_dev_id(header + payload)

        if data["index"] >= len(self.ieee_addr_list):
            # NOTE: 0x08 の取りこぼし等で対応が取れない周期は、誤ったマッピングを
            # 保存しないよう丸ごと破棄して次の周期を待つ
            logging.warning(
                "Unable to identify IEEE addr for dev_id=0x%04X (index=%d, list=%d), discard cycle",
                data["dev_id"],
                data["index"],
                len(self.ieee_addr_list),
            )
            self.ieee_addr_list = []
            return

        addr = self.ieee_addr_list[data["index"]]
        if data["dev_id"] not in self.dev_id_map:
            logging.info("Find IEEE addr for dev_id=0x%04X", data["dev_id"])
            self.dev_id_map[data["dev_id"]] = addr
            self._store_dev_id_map()
        elif self.dev_id_map[data["dev_id"]] != addr:
            logging.info("Update IEEE addr for dev_id=0x%04X", data["dev_id"])
            self.dev_id_map[data["dev_id"]] = addr
            self._store_dev_id_map()

        if data["index"] == (len(self.ieee_addr_list) - 1):
            # NOTE: 次の周期に備えてリストをクリアする
            logging.debug("Clear IEEE addr list")
            self.ieee_addr_list = []

    def _process_measure(self, header, payload, on_capture):
        try:
            logging.debug("Measure payload: %s", dump_packet(payload))
            data = self.parse_packet_measure(header + payload)
            if data is not None:
                on_capture(data)
        except Exception:
            logging.warning("Invalid packet: %s", dump_packet(header + payload))

    def parse_packet_measure(self, packet):
        dev_id = struct.unpack("<H", packet[5:7])[0]
        counter = packet[14]
        cur_time = struct.unpack("<H", packet[19:21])[0]
        cur_power = struct.unpack("<I", packet[26:30])[0]
        pre_time = struct.unpack("<H", packet[35:37])[0]
        pre_power = struct.unpack("<I", packet[42:46])[0]

        if dev_id in self.dev_id_map:
            addr = self.dev_id_map[dev_id]
        else:
            addr = "UNKNOWN"
            logging.warning("dev_id = 0x%04X is unknown", dev_id)
            logging.warning("dev_id_map = %s", json.dumps(self.dev_id_map, indent=4))

        # NOTE: 同じデータが2回送られることがあるので、新しいデータ毎にインクリメント
        # しているフィールドを使ってはじく
        if self.counter_hist.get(dev_id) == counter:
            logging.info("Packet duplication detected")
            return None
        self.counter_hist[dev_id] = counter

        dif_time = cur_time - pre_time
        if dif_time < 0:
            dif_time += 0x10000
        if dif_time == 0:
            logging.info("Packet duplication detected")
            return None

        dif_power = cur_power - pre_power
        if dif_power < 0:
            dif_power += 0x100000000

        scale = self.scale_resolver(addr) if self.scale_resolver is not None else None
        if scale is None:
            scale = self.watt_scale

        data = {
            "addr": addr,
            "dev_id": dev_id,
            "dev_id_str": f"0x{dev_id:04X}",
            "cur_time": cur_time,
            "cur_power": cur_power,
            "pre_time": pre_time,
            "pre_power": pre_power,
            "watt": round(float(dif_power) / dif_time * scale, 2),
        }

        logging.debug("Receive packet: %s", data)

        return data


def process_packet(handle, header, payload, on_capture):
    """
    従来の handle 辞書ベースの互換インターフェース。

    handle["_sniffer"] に PacketSniffer を保持し、以降のパケットで再利用する。
    """
    sniffer = handle.get("_sniffer")
    if sniffer is None:
        sensor_config = handle.get("sensor", {})
        sniffer = PacketSniffer(
            handle["device"]["cache"],
            watt_scale=sensor_config.get("watt_scale", WATT_SCALE_DEFAULT),
            scale_resolver=sensor_config.get("scale_resolver"),
        )
        handle["_sniffer"] = sniffer

    sniffer.process(header, payload, on_capture)
