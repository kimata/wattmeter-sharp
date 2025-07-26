"""センサーデータのメトリクス収集機能を提供します。"""

import datetime
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class MetricsCollector:
    """センサーメトリクス収集クラス。"""

    def __init__(self, db_path: Path):
        """コレクターを初期化します。"""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """データベースとテーブルを初期化します。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_name TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    time_slot INTEGER NOT NULL,
                    UNIQUE(sensor_name, time_slot)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
                ON sensor_heartbeats(sensor_name, timestamp)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_expected INTEGER NOT NULL,
                    total_received INTEGER NOT NULL,
                    availability_percent REAL NOT NULL,
                    UNIQUE(sensor_name, date)
                )
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """SQLite接続のコンテキストマネージャー。"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_connection(self):
        """SQLite接続のコンテキストマネージャー（公開メソッド）。"""
        with self._get_connection() as conn:
            yield conn

    def record_heartbeat(
        self, sensor_name: str, timestamp: int | None = None, boundary_grace_seconds: int = 30
    ):
        """
        センサーのハートビートを記録します。

        タイムスロット境界付近のデータは、前のスロットが空いていれば前のスロットに記録します。

        Args:
            sensor_name: センサー名
            timestamp: UNIX時刻（指定しない場合は現在時刻）
            boundary_grace_seconds: 境界後の猶予秒数（デフォルト30秒）

        """
        if timestamp is None:
            timestamp = int(time.time())

        # 6分（360秒）単位のタイムスロットを計算
        current_slot = timestamp // 360
        slot_boundary = current_slot * 360

        # タイムスロット境界からの経過秒数
        seconds_into_slot = timestamp - slot_boundary

        # 使用するタイムスロットを決定
        target_slot = current_slot

        # 境界付近（猶予秒数以内）の場合、前のスロットの状態を確認
        if seconds_into_slot <= boundary_grace_seconds and current_slot > 0:
            previous_slot = current_slot - 1

            # 前のスロットが空いているか確認
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM sensor_heartbeats
                    WHERE sensor_name = ? AND time_slot = ?
                """,
                    (sensor_name, previous_slot),
                )

                if cursor.fetchone()[0] == 0:
                    # 前のスロットが空いている場合は前のスロットに記録
                    target_slot = previous_slot
                    logging.debug(
                        "Using previous slot %d for %s (boundary grace applied)", previous_slot, sensor_name
                    )

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sensor_heartbeats
                    (sensor_name, timestamp, time_slot)
                    VALUES (?, ?, ?)
                """,
                    (sensor_name, timestamp, target_slot),
                )
                conn.commit()

            logging.debug(
                "Recorded heartbeat for %s at slot %d (timestamp: %d, seconds_into_slot: %d)",
                sensor_name,
                target_slot,
                timestamp,
                seconds_into_slot,
            )
        except sqlite3.Error:
            logging.exception("Failed to record heartbeat")
            raise

    def get_latest_heartbeat(self, sensor_name: str) -> int | None:
        """
        指定されたセンサーの最新のハートビート時刻を取得します。

        Args:
            sensor_name: センサー名

        Returns:
            最新のタイムスタンプ（UNIX時刻）、データがない場合はNone

        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT MAX(timestamp)
                FROM sensor_heartbeats
                WHERE sensor_name = ?
            """,
                (sensor_name,),
            )

            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None

    def calculate_availability(self, sensor_name: str, date: str) -> dict:
        """
        指定された日のセンサーの可用性を計算します。

        Args:
            sensor_name: センサー名
            date: 日付（YYYY-MM-DD形式）

        Returns:
            可用性情報を含む辞書

        """
        # 1日は24時間 * 60分 / 6分 = 240スロット
        expected_slots = 240

        # 指定日の開始と終了のタイムスロットを計算

        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        start_timestamp = int(date_obj.timestamp())
        end_timestamp = start_timestamp + 86400  # 24時間後

        start_slot = start_timestamp // 360
        end_slot = end_timestamp // 360

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT time_slot)
                FROM sensor_heartbeats
                WHERE sensor_name = ?
                AND time_slot >= ?
                AND time_slot < ?
            """,
                (sensor_name, start_slot, end_slot),
            )

            received_slots = cursor.fetchone()[0]

        availability_percent = (received_slots / expected_slots) * 100

        return {
            "sensor_name": sensor_name,
            "date": date,
            "total_expected": expected_slots,
            "total_received": received_slots,
            "availability_percent": round(availability_percent, 2),
        }

    def update_availability_summary(self, sensor_name: str, date: str):
        """
        指定された日のセンサーの可用性サマリーを更新します。

        Args:
            sensor_name: センサー名
            date: 日付（YYYY-MM-DD形式）

        """
        availability = self.calculate_availability(sensor_name, date)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sensor_availability
                (sensor_name, date, total_expected, total_received, availability_percent)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    availability["sensor_name"],
                    availability["date"],
                    availability["total_expected"],
                    availability["total_received"],
                    availability["availability_percent"],
                ),
            )
            conn.commit()
