#!/usr/bin/env python3
import json
import logging
import pickle
import struct

counter_hist = {}
ieee_addr_list = []

# 電力に掛ける倍率
# NOTE:
# 電力会社のスマートメータの読み値と比較すると常に電力が小さいので、
# 一定の倍率を掛ける。
WATT_SCALE = 1.5


def dev_id_map_load(dev_cache_file):
    if dev_cache_file.exists():
        with dev_cache_file.open("rb") as f:
            return pickle.load(f)  # noqa: S301
    else:
        return {}


def dev_id_map_store(dev_cache_file, dev_id_map):
    logging.info("Store dev_id_map")

    with dev_cache_file.open("wb") as f:
        pickle.dump(dev_id_map, f)


def dump_packet(data):
    return ",".join(f"{x:02X}" for x in list(data))


def parse_packet_ieee_addr(packet):
    return ":".join(f"{x:02X}" for x in reversed(list(packet[4:12])))


def parse_packet_dev_id(packet):
    dev_id = struct.unpack("<H", packet[4:6])[0]
    index = packet[6]

    return {
        "dev_id": dev_id,
        "index": index,
    }


def parse_packet_measure(packet, dev_id_map):
    global counter_hist

    dev_id = struct.unpack("<H", packet[5:7])[0]
    counter = packet[14]
    cur_time = struct.unpack("<H", packet[19:21])[0]
    cur_power = struct.unpack("<I", packet[26:30])[0]
    pre_time = struct.unpack("<H", packet[35:37])[0]
    pre_power = struct.unpack("<I", packet[42:46])[0]

    if dev_id in dev_id_map:
        addr = dev_id_map[dev_id]
    else:
        addr = "UNKNOWN"
        logging.warning("dev_id = %s is unknown", f"0x{dev_id:04X}")
        logging.warning("dev_ip_map = %s", json.dumps(dev_id_map, indent=4))

    # NOTE: 同じデータが2回送られることがあるので、新しいデータ毎にインクリメント
    # しているフィールドを使ってはじく
    if dev_id in counter_hist and counter_hist[dev_id] == counter:
        logging.info("Packet duplication detected")
        return None
    counter_hist[dev_id] = counter

    dif_time = cur_time - pre_time
    if dif_time < 0:
        dif_time += 0x10000
    if dif_time == 0:
        logging.info("Packet duplication detected")
        return None

    dif_power = cur_power - pre_power
    if dif_power < 0:
        dif_power += 0x100000000

    data = {
        "addr": addr,
        "dev_id": dev_id,
        "dev_id_str": f"0x{dev_id:04X}",
        "cur_time": cur_time,
        "cur_power": cur_power,
        "pre_time": pre_time,
        "pre_power": pre_power,
        "watt": round(float(dif_power) / dif_time * WATT_SCALE, 2),
    }

    logging.debug("Receive packet: %s", data)

    return data


def process_packet(handle, header, payload, on_capture):
    global ieee_addr_list  # noqa: PLW0603

    dev_id_map = dev_id_map_load(handle["device"]["cache"])

    if header[1] == 0x08:
        logging.debug("IEEE addr payload: %s", dump_packet(payload))
        ieee_addr_list.append(parse_packet_ieee_addr(header + payload))
    elif header[1] == 0x12:
        logging.debug("Dev ID payload: %s", dump_packet(payload))
        data = parse_packet_dev_id(header + payload)
        if data["index"] < len(ieee_addr_list):
            if data["dev_id"] not in dev_id_map:
                logging.info("Find IEEE addr for dev_id=%s", "0x{:04X}".format(data["dev_id"]))
                dev_id_map[data["dev_id"]] = ieee_addr_list[data["index"]]
                dev_id_map_store(handle["device"]["cache"], dev_id_map)
            elif dev_id_map[data["dev_id"]] != ieee_addr_list[data["index"]]:
                logging.info("Update IEEE addr for dev_id=%s", "0x{:04X}".format(data["dev_id"]))
                dev_id_map[data["dev_id"]] = ieee_addr_list[data["index"]]
                dev_id_map_store(handle["device"]["cache"], dev_id_map)
        else:
            logging.warning("Unable to identify IEEE addr for dev_id=%s", "0x{:04X}".format(data["dev_id"]))

        if data["index"] == (len(ieee_addr_list) - 1):
            # NOTE: 次の周期に備えてリストをクリアする
            logging.debug("Clear IEEE addr list")
            ieee_addr_list = []

    elif header[1] == 0x2C:
        try:
            logging.debug("Measure payload: %s", dump_packet(payload))
            data = parse_packet_measure(header + payload, dev_id_map)
            if data is not None:
                on_capture(data)
        except Exception:
            logging.warning("Invalid packet: %s", dump_packet(header + payload))

    else:
        logging.debug("Unknown packet: %s", dump_packet(header + payload))
