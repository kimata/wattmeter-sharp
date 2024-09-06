#!/usr/bin/env python3
"""
センサーからのパケットを Pub-Sub パターンで配信します．

Usage:
  serial_pubsub.py -S [-t SERIAL_PORT] [-p SERVER_PORT] [-d]
  serial_pubsub.py [-s SERVER_HOST] [-p SERVER_PORT] [-c CONFIG] [-d]

Options:
  -S                : サーバーモードで動作します．
  -s SERVER_HOST    : サーバーのホスト名を指定します． [default: localhost]
  -t SERIAL_PORT    : HEMS 中継器を接続するシリアルポートを指定します． [default: /dev/ttyUSB0]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -c CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -d                : デバッグモードで動作します．
"""

import logging

import serial
import zmq

CH = "serial"
SER_BAUD = 115200
SER_TIMEOUT = 10


def start_server(serial_port, server_port, liveness_file=None):
    logging.info("Start serial server...")

    context = zmq.Context()

    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{server_port}")

    ser = serial.Serial(serial_port, SER_BAUD, timeout=SER_TIMEOUT)

    logging.info("Server initialize done.")

    while True:
        header = ser.read(2)

        if len(header) == 0:
            continue
        elif len(header) == 1:  # noqa: RET507
            logging.debug("Short packet")
            continue

        header_hex = header.hex()
        payload_hex = ser.read(header[1] + 5 - 2).hex()

        logging.debug("send %s %s", header_hex, payload_hex)
        socket.send_string(f"{CH} {header_hex} {payload_hex}")
        if liveness_file is not None:
            liveness_file.touch(exist_ok=True)


def start_client(server_host, server_port, handle, func):
    logging.info("Start serial client...")

    socket = zmq.Context().socket(zmq.SUB)
    socket.connect(f"tcp://{server_host}:{server_port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, CH)

    logging.info("Client initialize done.")

    while True:
        ch, header_hex, payload_hex = socket.recv_string().split(" ", 2)
        logging.debug("recv %s %s", header_hex, payload_hex)
        func(handle, bytes.fromhex(header_hex), bytes.fromhex(payload_hex))


if __name__ == "__main__":
    import pathlib

    import docopt
    import my_lib.config
    import my_lib.logger
    import sharp_hems.sniffer

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    is_server_mode = args["-S"]
    server_host = args["-s"]
    server_port = int(args["-p"])
    serial_port = args["-t"]
    debug_mode = args["-d"]

    my_lib.logger.init("test", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file)

    dev_cache_file = pathlib.Path(config["device"]["cache"])

    def log_data(data):
        logging.info(data)

    def process_packet(handle, header, payload):
        sharp_hems.sniffer.process_packet(handle, header, payload, log_data)

    if is_server_mode:
        logging.info("Start server")
        start_server(serial_port, server_port)
    else:
        logging.info("Start client")
        start_client(server_host, server_port, {"device": {"cache": dev_cache_file}}, process_packet)
