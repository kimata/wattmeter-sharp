#!/usr/bin/env python3
# ruff: noqa: S101
import contextlib
import logging
import pathlib
import pickle
import random
import socket
import threading
import time
from unittest import mock

import pytest

CONFIG_FILE = "config.example.yaml"
SCHEMA_CONFIG = "config.schema"


class MockZMQSocket:
    """ZMQソケットのモッククラス"""

    def __init__(self, packet_data):
        """Initialize with packet data."""
        self.packet_data = packet_data
        self.index = 0

    def recv_string(self):
        """packet.dumpからデータを読み出してZMQメッセージ形式で返す"""
        if self.index >= len(self.packet_data):
            # データが終わったら最初に戻る（無限ループテスト用）
            self.index = 0

        timestamp, header, payload = self.packet_data[self.index]
        self.index += 1

        # ZMQメッセージ形式: "serial header_hex payload_hex"
        header_hex = header.hex()
        payload_hex = payload.hex()
        return f"serial {header_hex} {payload_hex}"

    def connect(self, address):
        """接続のモック（何もしない）"""

    def setsockopt_string(self, option, value):
        """オプション設定のモック（何もしない）"""


def load_packet_dump(dump_file_path="tests/data/packet.dump"):
    """
    packet.dumpファイルを読み込んでパケットデータを返す

    Args:
        dump_file_path: packet.dumpファイルのパス

    Returns:
        list: [timestamp, header, payload]のリスト

    """
    dump_path = pathlib.Path(dump_file_path)
    if not dump_path.exists():
        raise FileNotFoundError(f"packet.dump file not found: {dump_file_path}")  # noqa: TRY003, EM102

    with dump_path.open("rb") as f:
        return pickle.load(f)  # noqa: S301


def create_mock_socket_context(dump_file_path="tests/data/packet.dump"):
    """
    packet.dumpからデータを読み込むモックソケットコンテキストを作成

    Args:
        dump_file_path: packet.dumpファイルのパス

    Returns:
        mock.Mock: モックされたZMQコンテキスト

    """
    packet_data = load_packet_dump(dump_file_path)
    mock_socket = MockZMQSocket(packet_data)

    mock_context = mock.Mock()
    mock_context.socket.return_value = mock_socket

    return mock_context


def mock_serial_server(dump_file_path="tests/data/packet.dump"):
    """
    serial_pubsub.start_serverをモックして、packet.dumpからデータを読み込むデコレータ

    このデコレータを使用すると、シリアルポートとZMQコンテキストの両方がモックされ、
    packet.dumpファイルから読み込んだデータでシリアルサーバーのテストが可能になります。

    Args:
        dump_file_path: packet.dumpファイルのパス (デフォルト: "tests/data/packet.dump")

    Usage:
        @mock_serial_server()
        def test_server():
            # この中でserial_pubsub.start_serverが呼ばれると、
            # packet.dumpからデータが読み込まれ、シリアルデータとして返される
            sharp_hems.serial_pubsub.start_server("/dev/mock", 4444, liveness_file)

    """

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # シリアルポートとZMQコンテキストをモック
            mock_serial = create_mock_serial_server(dump_file_path)

            # ZMQソケットとシリアルをモック
            received_messages = []

            class MockZMQSocket:
                def bind(self, address):
                    pass

                def send_string(self, message):
                    received_messages.append(message)
                    logging.info("ZMQ sent: %s", message)
                    # すべてのパケットデータを処理したかチェック
                    try:
                        packet_data = load_packet_dump(dump_file_path)
                        if len(received_messages) >= len(packet_data):
                            import sharp_hems.serial_pubsub

                            sharp_hems.serial_pubsub.stop_server()
                    except FileNotFoundError:
                        # packet.dumpがない場合は3つで停止
                        if len(received_messages) >= 3:
                            import sharp_hems.serial_pubsub

                            sharp_hems.serial_pubsub.stop_server()

            class MockZMQContext:
                def socket(self, socket_type):  # noqa: ARG002
                    return MockZMQSocket()

            with (
                mock.patch("sharp_hems.serial_pubsub.serial.Serial") as mock_serial_class,
                mock.patch("sharp_hems.serial_pubsub.zmq.Context") as mock_zmq_context,
            ):
                mock_serial_class.return_value = mock_serial
                mock_zmq_context.return_value = MockZMQContext()

                # received_messagesをテスト関数に渡せるように、kwargsに追加
                kwargs["received_messages"] = received_messages
                return test_func(*args, **kwargs)

        return wrapper

    return decorator


def mock_serial_pubsub_client(dump_file_path="tests/data/packet.dump"):
    """
    serial_pubsub.start_clientをモックして、packet.dumpからデータを読み込むデコレータ

    このデコレータを使用すると、ZMQソケットの recv_string() メソッドが
    packet.dumpファイルから読み込んだデータを返すようにモックされます。

    packet.dumpファイルは src/sharp_hems_dump.py で生成された pickle 形式で、
    [timestamp, header_bytes, payload_bytes] のリストが格納されています。

    Args:
        dump_file_path: packet.dumpファイルのパス (デフォルト: "tests/data/packet.dump")

    Usage:
        @mock_serial_pubsub_client()
        def test_something():
            # この中でserial_pubsub.start_clientが呼ばれると、
            # packet.dumpからデータが読み込まれ、ZMQメッセージ形式
            # "serial header_hex payload_hex" で返される
            sharp_hems.serial_pubsub.start_client(
                "localhost", 4444, handle, packet_handler
            )

    """

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # sharp_hems.serial_pubsub モジュール内のzmqをモック
            with mock.patch("sharp_hems.serial_pubsub.zmq.Context") as mock_zmq_context:
                mock_context = create_mock_socket_context(dump_file_path)
                mock_zmq_context.return_value = mock_context
                return test_func(*args, **kwargs)

        return wrapper

    return decorator


######################################################################
# テスト例
@mock_serial_pubsub_client()
def test_packet_processing_with_dump_data():
    """packet.dumpからのデータを使ったパケット処理のテスト例"""
    import sharp_hems.serial_pubsub

    processed_packets = []

    def test_packet_handler(handle, header, payload):  # noqa: ARG001
        """テスト用のパケットハンドラ"""
        processed_packets.append(
            {"header": header, "payload": payload, "header_hex": header.hex(), "payload_hex": payload.hex()}
        )
        # 最初の3パケットを処理したら終了
        if len(processed_packets) >= 3:
            msg = "Test completed"
            raise KeyboardInterrupt(msg)

    with contextlib.suppress(KeyboardInterrupt):
        # モックされたstart_clientを呼び出し
        sharp_hems.serial_pubsub.start_client("localhost", 4444, {}, test_packet_handler)

    # パケットが正常に処理されたことを確認
    assert len(processed_packets) == 3
    assert all("header" in p and "payload" in p for p in processed_packets)


def test_load_packet_dump():
    """packet.dumpファイルの読み込みテスト"""
    try:
        packet_data = load_packet_dump()
        assert isinstance(packet_data, list)
        assert len(packet_data) > 0

        # 最初のパケットの構造を確認
        timestamp, header, payload = packet_data[0]
        assert isinstance(timestamp, (int, float))
        assert isinstance(header, bytes)
        assert isinstance(payload, bytes)

    except FileNotFoundError:
        pytest.skip("packet.dump file not found - this is expected in CI")


def test_mock_zmq_socket():
    """MockZMQSocketのテスト"""
    # テストデータを作成
    test_data = [
        [0.0, b"\x10\x20", b"\x30\x40\x50"],
        [1.0, b"\x11\x21", b"\x31\x41\x51"],
    ]

    mock_socket = MockZMQSocket(test_data)

    # 最初のパケット
    msg1 = mock_socket.recv_string()
    assert msg1 == "serial 1020 304050"

    # 2番目のパケット
    msg2 = mock_socket.recv_string()
    assert msg2 == "serial 1121 314151"

    # 3番目のパケット（最初に戻る）
    msg3 = mock_socket.recv_string()
    assert msg3 == "serial 1020 304050"


class MockSerial:
    """シリアルポートのモッククラス"""

    def __init__(self, packet_data, inject_dummy_data=False):
        """Initialize with packet data from packet.dump."""
        self.packet_data = packet_data
        self.index = 0
        self.read_position = 0  # 現在のパケット内での読み取り位置
        self.current_packet_data = b""  # 現在処理中のパケットの完全データ
        self.inject_dummy_data = inject_dummy_data
        self.dummy_data_queue = []  # ダミーデータのキュー

    def _generate_dummy_data(self):
        """ダミーデータを生成（0バイト、1バイト、不正データなど）"""
        dummy_types = [
            b"",  # 0バイト（タイムアウト相当）
            b"\x00",  # 1バイト（不完全なヘッダー）
            b"\xff",  # 1バイト（不完全なヘッダー）
            b"\xfe",  # 1バイト（不完全なヘッダー）
        ]
        return random.choice(dummy_types)  # noqa: S311

    def read(self, size):
        """シリアルからのデータ読み取りをシミュレート"""
        # ダミーデータの注入（20%の確率）
        if self.inject_dummy_data and random.random() < 0.2 and size == 2:  # noqa: S311
            dummy_data = self._generate_dummy_data()
            logging.debug(
                "Injecting dummy data: %s (%d bytes)",
                dummy_data.hex() if dummy_data else "empty",
                len(dummy_data),
            )
            return dummy_data

        if self.index >= len(self.packet_data):
            # データが終わったら空のデータを返す（終了条件）
            return b""

        # 新しいパケットの開始
        if self.read_position == 0:
            timestamp, header, payload = self.packet_data[self.index]
            # ヘッダー + ペイロードを結合してシリアルデータを再構成
            self.current_packet_data = header + payload
            logging.debug(
                "Starting packet %d/%d: %s",
                self.index + 1,
                len(self.packet_data),
                self.current_packet_data.hex(),
            )

        # 要求されたサイズ分のデータを返す
        start_pos = self.read_position
        end_pos = min(start_pos + size, len(self.current_packet_data))
        data = self.current_packet_data[start_pos:end_pos]

        self.read_position = end_pos

        # パケットの終端に達したら次のパケットに進む
        if self.read_position >= len(self.current_packet_data):
            self.index += 1
            self.read_position = 0

        logging.debug("Serial read(%d) -> %s", size, data.hex())
        return data


def create_mock_serial_server(dump_file_path="tests/data/packet.dump", inject_dummy_data=False):
    """
    packet.dumpからデータを読み込むモックシリアルサーバーを作成

    Args:
        dump_file_path: packet.dumpファイルのパス
        inject_dummy_data: ダミーデータを注入するかどうか

    Returns:
        MockSerial: モックされたシリアルオブジェクト

    """
    packet_data = load_packet_dump(dump_file_path)
    return MockSerial(packet_data, inject_dummy_data=inject_dummy_data)


@mock_serial_pubsub_client()
def test_sniffer():
    """snifferモジュールのテスト"""
    import my_lib.pretty

    import sharp_hems.serial_pubsub
    import sharp_hems.sniffer

    PACKET_COUNT = 30
    processed_count = 0
    sense_data_list = []

    def process_packet(handle, header, payload):
        nonlocal processed_count
        sharp_hems.sniffer.process_packet(handle, header, payload, lambda data: sense_data_list.append(data))
        processed_count += 1
        if processed_count >= PACKET_COUNT:
            msg = "Test completed"
            raise KeyboardInterrupt(msg)

    with contextlib.suppress(KeyboardInterrupt):
        sharp_hems.serial_pubsub.start_client(
            "localhost", 4444, {"device": {"cache": pathlib.Path("data/dev_id_test.dat")}}, process_packet
        )

    logging.info(my_lib.pretty.format(sense_data_list))

    # パケットが処理されたことを確認
    assert processed_count == PACKET_COUNT
    assert len(sense_data_list) != 0


@mock_serial_server()
def test_serial_server(**kwargs):
    """start_serverのテスト（シリアルポートをモック）"""
    import threading
    import time

    import sharp_hems.serial_pubsub

    # デコレータから渡されたreceived_messagesを取得
    received_messages = kwargs["received_messages"]

    # liveness_fileのモック
    liveness_file = pathlib.Path("tests/evidence/test_liveness.txt")

    def run_server():
        try:
            sharp_hems.serial_pubsub.start_server("/dev/mock", 4444, liveness_file)
        except Exception as e:
            logging.info("Server stopped: %s", e)

    # サーバーを別スレッドで実行
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # サーバーが起動してメッセージを処理するまで待機
    timeout = 10
    start_time = time.time()
    while len(received_messages) < 3 and time.time() - start_time < timeout:
        time.sleep(0.1)

    # 結果の確認
    assert len(received_messages) >= 3, f"Expected at least 3 messages, got {len(received_messages)}"

    # メッセージの形式確認（"serial header_hex payload_hex"）
    for message in received_messages:
        parts = message.split(" ")
        assert len(parts) == 3, f"Invalid message format: {message}"
        assert parts[0] == "serial", f"Expected 'serial' channel, got {parts[0]}"
        # ヘッダーとペイロードが16進文字列であることを確認
        try:
            bytes.fromhex(parts[1])  # header
            bytes.fromhex(parts[2])  # payload
        except ValueError:
            pytest.fail(f"Invalid hex data in message: {message}")

    logging.info("Successfully processed %d serial packets", len(received_messages))


def test_serial_server_with_dummy_data():
    """start_serverのテスト（ダミーデータ注入付き）"""
    import threading
    import time

    import sharp_hems.serial_pubsub

    # ダミーデータ注入有効でシリアルポートをモック
    mock_serial = create_mock_serial_server(inject_dummy_data=True)

    # 処理されたメッセージを格納するリスト
    received_messages = []

    # liveness_fileのモック
    liveness_file = pathlib.Path("tests/evidence/test_liveness.txt")

    # ZMQソケットをモック
    class MockZMQSocket:
        def bind(self, address):
            pass

        def send_string(self, message):
            received_messages.append(message)
            logging.info("ZMQ sent: %s", message)
            # 5つのメッセージを受信したらサーバーを停止
            if len(received_messages) >= 5:
                sharp_hems.serial_pubsub.stop_server()

    class MockZMQContext:
        def socket(self, socket_type):  # noqa: ARG002
            return MockZMQSocket()

    def run_server():
        try:
            sharp_hems.serial_pubsub.start_server("/dev/mock", 4444, liveness_file)
        except Exception as e:
            logging.info("Server stopped: %s", e)

    # シリアルポートとZMQをモック
    with (
        mock.patch("sharp_hems.serial_pubsub.serial.Serial") as mock_serial_class,
        mock.patch("sharp_hems.serial_pubsub.zmq.Context") as mock_zmq_context,
    ):
        mock_serial_class.return_value = mock_serial
        mock_zmq_context.return_value = MockZMQContext()

        # サーバーを別スレッドで実行
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # サーバーが起動してメッセージを処理するまで待機
        # （ダミーデータ注入で時間がかかる可能性があるため長めに設定）
        timeout = 15
        start_time = time.time()
        while len(received_messages) < 5 and time.time() - start_time < timeout:
            time.sleep(0.1)

    # 結果の確認
    assert len(received_messages) >= 3, f"Expected at least 3 messages, got {len(received_messages)}"

    # メッセージの形式確認（"serial header_hex payload_hex"）
    for message in received_messages:
        parts = message.split(" ")
        assert len(parts) == 3, f"Invalid message format: {message}"
        assert parts[0] == "serial", f"Expected 'serial' channel, got {parts[0]}"
        # ヘッダーとペイロードが16進文字列であることを確認
        try:
            bytes.fromhex(parts[1])  # header
            bytes.fromhex(parts[2])  # payload
        except ValueError:
            pytest.fail(f"Invalid hex data in message: {message}")

    logging.info("Successfully processed %d serial packets with dummy data injection", len(received_messages))


@pytest.fixture
def server_port():
    """空きポートを見つけて返すフィクスチャ"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def config():
    import pathlib

    import my_lib.config

    return my_lib.config.load(CONFIG_FILE, pathlib.Path(SCHEMA_CONFIG))


def test_server_all_packets(server_port):  # noqa: C901
    """packet.dumpのすべてのデータを使ったサーバーテスト"""
    import sharp_hems.serial_pubsub

    # packet.dumpからすべてのデータを取得
    try:
        packet_data = load_packet_dump()
        expected_packet_count = len(packet_data)
        logging.info("Loaded %d packets from dump file", expected_packet_count)
    except FileNotFoundError:
        pytest.skip("packet.dump file not found - skipping integration test")

    # シリアルポートをモック
    mock_serial = create_mock_serial_server()

    # 処理されたメッセージを格納するリスト
    received_messages = []

    # liveness_fileのモック
    liveness_file = pathlib.Path("tests/evidence/test_liveness.txt")

    # ZMQソケットをモック
    class MockZMQSocket:
        def bind(self, address):
            pass

        def send_string(self, message):
            received_messages.append(message)
            logging.info("ZMQ sent: %s", message)
            # すべてのパケットデータを処理したかチェック
            if len(received_messages) >= expected_packet_count:
                sharp_hems.serial_pubsub.stop_server()

    class MockZMQContext:
        def socket(self, socket_type):  # noqa: ARG002
            return MockZMQSocket()

    def run_server():
        """サーバーを別スレッドで実行"""
        try:
            sharp_hems.serial_pubsub.start_server("/dev/mock", server_port, liveness_file)
        except Exception as e:
            logging.info("Server stopped: %s", e)

    # シリアルポートとZMQをモック
    with (
        mock.patch("sharp_hems.serial_pubsub.serial.Serial") as mock_serial_class,
        mock.patch("sharp_hems.serial_pubsub.zmq.Context") as mock_zmq_context,
    ):
        mock_serial_class.return_value = mock_serial
        mock_zmq_context.return_value = MockZMQContext()

        # サーバーを別スレッドで実行
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # すべてのパケットが処理されるまで待機（最大30秒）
        max_wait_time = 30
        start_time = time.time()
        while len(received_messages) < expected_packet_count and time.time() - start_time < max_wait_time:
            time.sleep(0.1)

    # 結果の検証
    logging.info("Received %d messages, expected %d", len(received_messages), expected_packet_count)
    assert len(received_messages) == expected_packet_count, (
        f"Expected {expected_packet_count} ZMQ messages, got {len(received_messages)}"
    )

    # すべてのメッセージの形式確認
    for i, message in enumerate(received_messages):
        parts = message.split(" ")
        assert len(parts) == 3, f"Invalid ZMQ message format at index {i}: {message}"
        assert parts[0] == "serial", f"Expected 'serial' channel at index {i}, got {parts[0]}"
        # ヘッダーとペイロードが16進文字列であることを確認
        try:
            header_bytes = bytes.fromhex(parts[1])  # header
            payload_bytes = bytes.fromhex(parts[2])  # payload

            # 元のpacket.dumpデータと比較
            timestamp, original_header, original_payload = packet_data[i]
            combined_original = original_header + original_payload
            combined_received = header_bytes + payload_bytes

            assert combined_received == combined_original, (
                f"Message {i + 1} data mismatch: "
                f"expected {combined_original.hex()}, got {combined_received.hex()}"
            )

        except ValueError:
            pytest.fail(f"Invalid hex data in message {i + 1}: {message}")

    logging.info("Successfully tested all %d packets from dump file", len(received_messages))
