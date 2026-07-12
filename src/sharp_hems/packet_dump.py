#!/usr/bin/env python3
"""
packet.dump ファイルの読み書き。

書き込みは JSONL 形式 (1 行 = 1 パケット) の追記で行い、
読み込みは JSONL と旧フォーマット (pickle) の両方に対応する。
"""

import json
import pathlib
import pickle


def append(dump_file, elapsed, header, payload):
    """パケットを 1 件追記する。"""
    record = {
        "elapsed": round(elapsed, 3),
        "header": header.hex(),
        "payload": payload.hex(),
    }
    with pathlib.Path(dump_file).open("a") as f:
        f.write(json.dumps(record) + "\n")


def load(dump_file):
    """ダンプファイルを読み込み、[elapsed, header(bytes), payload(bytes)] のリストを返す。"""
    dump_path = pathlib.Path(dump_file)
    raw = dump_path.read_bytes()

    try:
        packet_list = []
        for line in raw.decode().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            packet_list.append(
                [record["elapsed"], bytes.fromhex(record["header"]), bytes.fromhex(record["payload"])]
            )
    except (ValueError, UnicodeDecodeError):
        # NOTE: 旧フォーマット (pickle) からの読み込み
        return pickle.loads(raw)  # noqa: S301
    else:
        return packet_list
