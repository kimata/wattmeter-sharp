"""センサーデータのメトリクス収集機能を提供します。"""

import datetime
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import my_lib.sqlite_util
import my_lib.time


class MetricsCollector:
    """センサーメトリクス収集クラス。"""

    def __init__(self, db_path: Path):
        """コレクターを初期化します。"""
        self.db_path = db_path
        self._init_database()

    def close(self):
        """メトリクスコレクターをクローズします。"""
        # 現在の実装では都度接続・切断しているため、
        # 特別な処理は不要だが、将来的な拡張に備えて実装
        logging.debug("Closing MetricsCollector for %s", self.db_path)

    def _init_database(self):
        """データベースとテーブルを初期化します。"""
        conn = my_lib.sqlite_util.create(self.db_path)

        try:
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

            conn.execute("""
                CREATE TABLE IF NOT EXISTS communication_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_name TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    time_slot INTEGER NOT NULL,
                    error_type TEXT NOT NULL DEFAULT 'consecutive_failure'
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_comm_errors_sensor_timestamp
                ON communication_errors(sensor_name, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_comm_errors_timestamp
                ON communication_errors(timestamp)
            """)

            conn.commit()
        finally:
            conn.close()

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

            # 通信エラー検出を実行
            self._detect_communication_errors(sensor_name, target_slot)

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

    def _detect_communication_errors(self, sensor_name: str, current_slot: int):
        """
        通信エラーを検出し、データベースに記録します。

        受信できたスロットをnとして、n-1, n-2, n-3, n-4, n-5のいずれかで
        受信成功している場合、最後に受信成功したスロットからn-1までの
        全スロットを通信エラーとして記録します。

        Args:
            sensor_name: センサー名
            current_slot: 現在受信成功したタイムスロット（n）

        """
        try:
            with self._get_connection() as conn:
                # 過去5スロット（n-1 から n-5）で受信成功したスロットを検索
                past_slots = [current_slot - i for i in range(1, 6)]  # [n-1, n-2, n-3, n-4, n-5]

                placeholders = ",".join("?" * len(past_slots))
                query = f"""
                    SELECT MAX(time_slot) FROM sensor_heartbeats
                    WHERE sensor_name = ? AND time_slot IN ({placeholders})
                    """  # noqa: S608
                cursor = conn.execute(
                    query,
                    (sensor_name, *past_slots),
                )

                result = cursor.fetchone()
                last_success_slot = result[0] if result and result[0] is not None else None

                # 過去5スロットで受信成功していない場合は通信エラーとして扱わない
                if last_success_slot is None:
                    return

                # 最後に受信成功したスロットから現在のスロットの直前までが失敗スロット
                failed_slots = list(range(last_success_slot + 1, current_slot))

                if not failed_slots:
                    return  # 連続失敗がない場合

                # 既に記録済みのエラーを除外
                existing_placeholders = ",".join("?" * len(failed_slots))
                query = f"""
                    SELECT time_slot FROM communication_errors
                    WHERE sensor_name = ? AND time_slot IN ({existing_placeholders})
                    """  # noqa: S608
                cursor = conn.execute(
                    query,
                    (sensor_name, *failed_slots),
                )

                existing_error_slots = {row[0] for row in cursor.fetchall()}
                new_error_slots = [slot for slot in failed_slots if slot not in existing_error_slots]

                # 新しい通信エラーを記録
                for slot in new_error_slots:
                    error_timestamp = slot * 360  # スロットをタイムスタンプに変換
                    conn.execute(
                        """
                        INSERT INTO communication_errors
                        (sensor_name, timestamp, time_slot, error_type)
                        VALUES (?, ?, ?, ?)
                        """,
                        (sensor_name, error_timestamp, slot, "consecutive_failure"),
                    )

                    logging.info(
                        "Detected communication error for %s at slot %d (timestamp: %d)",
                        sensor_name,
                        slot,
                        error_timestamp,
                    )

                if new_error_slots:
                    conn.commit()
                    logging.debug(
                        "Recorded %d communication errors for %s (slots %d-%d)",
                        len(new_error_slots),
                        sensor_name,
                        min(new_error_slots),
                        max(new_error_slots),
                    )

        except sqlite3.Error:
            logging.exception("Failed to detect communication errors")

    def get_communication_errors_histogram(self, hours: int = 24) -> dict:
        """
        指定された時間内の通信エラーのヒストグラムを取得します。

        Args:
            hours: 遡る時間数（デフォルト24時間）

        Returns:
            48個のbinに分けられたヒストグラムデータ

        """
        now = int(time.time())
        start_timestamp = now - (hours * 3600)  # hours時間前

        # 48 binのヒストグラム（30分刻み）を初期化
        histogram = [0] * 48

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT timestamp FROM communication_errors
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
                """,
                (start_timestamp, now),
            )

            for row in cursor.fetchall():
                error_timestamp = row[0]

                # UTCタイムスタンプを日本時間に変換
                utc_datetime = datetime.datetime.fromtimestamp(error_timestamp, datetime.timezone.utc)
                jst_datetime = utc_datetime.astimezone(my_lib.time.get_zoneinfo())

                # 日本時間での今日の0時からの経過秒数に変換
                midnight_jst = jst_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                seconds_from_midnight = int((jst_datetime - midnight_jst).total_seconds())

                # 30分刻みのbin（0-47）に分類
                bin_index = min(int(seconds_from_midnight // 1800), 47)  # 1800秒 = 30分
                histogram[bin_index] += 1

        return {
            "bins": histogram,
            "bin_labels": [f"{i // 2:02d}:{(i % 2) * 30:02d}" for i in range(48)],
            "total_errors": sum(histogram),
        }

    def get_latest_communication_errors(self, limit: int = 50) -> list:
        """
        最新の通信エラーログを取得します。

        Args:
            limit: 取得する件数（デフォルト50件）

        Returns:
            通信エラーログのリスト

        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT sensor_name, timestamp, error_type
                FROM communication_errors
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            errors = []
            for row in cursor.fetchall():
                sensor_name, timestamp, error_type = row

                # タイムスタンプを日時文字列に変換
                dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
                formatted_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")

                errors.append(
                    {
                        "sensor_name": sensor_name,
                        "datetime": formatted_datetime,
                        "timestamp": timestamp,
                        "error_type": error_type,
                    }
                )

            return errors
