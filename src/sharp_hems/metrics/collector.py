"""センサーデータのメトリクス収集機能を提供します。"""

import datetime
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import my_lib.sqlite_util
import my_lib.time

# タイムスロットの長さ (秒)。センサーの送信周期 (約 6 分) に対応する。
TIME_SLOT_SEC = 360
SLOTS_PER_DAY = 86400 // TIME_SLOT_SEC

# 生ハートビートの保持日数。これより古い分は日次サマリーに畳み込まれる。
RETENTION_DAYS_DEFAULT = 30


class MetricsCollector:
    """センサーメトリクス収集クラス。"""

    def __init__(self, db_path: Path):
        """コレクターを初期化します。"""
        self.db_path = db_path
        self._last_cleanup = 0.0
        self._init_database()

    def close(self):
        """メトリクスコレクターをクローズします。"""
        # 現在の実装では都度接続・切断しているため、
        # 特別な処理は不要だが、将来的な拡張に備えて実装
        logging.debug("Closing MetricsCollector for %s", self.db_path)

    def _init_database(self):
        """データベースとテーブルを初期化します。"""
        with my_lib.sqlite_util.connect(self.db_path) as conn:
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

    @contextmanager
    def _get_connection(self):
        """SQLite接続のコンテキストマネージャー。"""
        with my_lib.sqlite_util.connect(self.db_path) as conn:
            yield conn

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

    def get_first_heartbeat(self, sensor_name: str | None = None) -> int | None:
        """最古のハートビート時刻を取得します (sensor_name 省略時は全センサー)。"""
        with self._get_connection() as conn:
            if sensor_name is None:
                cursor = conn.execute("SELECT MIN(timestamp) FROM sensor_heartbeats")
            else:
                cursor = conn.execute(
                    "SELECT MIN(timestamp) FROM sensor_heartbeats WHERE sensor_name = ?",
                    (sensor_name,),
                )
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None

    def _get_summary_totals(self, sensor_name: str) -> tuple[int, int, str | None]:
        """日次サマリーの (期待スロット合計, 受信スロット合計, 最終日付) を返します。"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COALESCE(SUM(total_expected), 0), COALESCE(SUM(total_received), 0), MAX(date)
                FROM sensor_availability
                WHERE sensor_name = ?
                """,
                (sensor_name,),
            )
            expected, received, last_date = cursor.fetchone()
            return expected, received, last_date

    def _count_slots(self, sensor_name: str, start_slot: int, end_slot: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT time_slot)
                FROM sensor_heartbeats
                WHERE sensor_name = ? AND time_slot >= ? AND time_slot <= ?
                """,
                (sensor_name, start_slot, end_slot),
            )
            return cursor.fetchone()[0]

    def _raw_slot_stats(self, sensor_name: str, start_timestamp: int, end_timestamp: int):
        """
        生ハートビートから (期待スロット数, 受信スロット数) を計算します。

        現在のタイムスロットは、そのスロットでデータを受信している場合のみ期待に含める。
        """
        start_slot = start_timestamp // TIME_SLOT_SEC
        current_slot = end_timestamp // TIME_SLOT_SEC

        has_current_slot_data = self._count_slots(sensor_name, current_slot, current_slot) > 0

        if has_current_slot_data:
            expected_slots = current_slot - start_slot + 1
            end_slot = current_slot
        else:
            expected_slots = current_slot - start_slot
            end_slot = current_slot - 1

            if expected_slots <= 0:
                expected_slots = 1
                end_slot = start_slot

        received_slots = self._count_slots(sensor_name, start_slot, end_slot)
        return expected_slots, received_slots

    def calculate_availability_between(
        self, sensor_name: str, start_timestamp: int, end_timestamp: int
    ) -> float:
        """
        指定期間の受信率 (%) を生ハートビートから計算します。

        センサーのデータ開始が期間より遅い場合は、データ開始以降のみを期待値とする。
        期間は retention 期間内である必要がある (それより古い部分は日次サマリーに
        畳み込まれているため)。
        """
        first_timestamp = self.get_first_heartbeat(sensor_name)
        if first_timestamp is None:
            return 0.0

        actual_start = max(start_timestamp, first_timestamp)
        if actual_start >= end_timestamp:
            return 0.0

        expected_slots, received_slots = self._raw_slot_stats(sensor_name, actual_start, end_timestamp)
        if expected_slots <= 0:
            return 0.0

        return round((received_slots / expected_slots) * 100, 2)

    def calculate_total_availability(self, sensor_name: str, end_timestamp: int) -> float:
        """
        データ収集開始から現在までの累計受信率 (%) を計算します。

        retention で畳み込まれた日次サマリーと、残っている生ハートビートを合算する。
        """
        summary_expected, summary_received, summary_last_date = self._get_summary_totals(sensor_name)

        # 生データの計算開始点: サマリーがあればその翌日 0 時 (UTC)、無ければデータ開始
        if summary_last_date is not None:
            last_date = datetime.datetime.strptime(summary_last_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
            raw_start = int(last_date.timestamp()) + 86400
        else:
            raw_start = self.get_first_heartbeat(sensor_name)

        raw_expected = 0
        raw_received = 0
        if raw_start is not None and raw_start < end_timestamp:
            raw_expected, raw_received = self._raw_slot_stats(sensor_name, raw_start, end_timestamp)

        total_expected = summary_expected + raw_expected
        total_received = summary_received + raw_received

        if total_expected <= 0:
            return 0.0

        return round((total_received / total_expected) * 100, 2)

    def get_start_date(self) -> str | None:
        """メトリクス収集の開始日 (YYYY-MM-DD、UTC) を返します。"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT MIN(date) FROM sensor_availability")
            result = cursor.fetchone()
            summary_start = result[0] if result else None

        first_timestamp = self.get_first_heartbeat()
        raw_start = (
            datetime.datetime.fromtimestamp(first_timestamp, datetime.UTC).strftime("%Y-%m-%d")
            if first_timestamp is not None
            else None
        )

        candidates = [d for d in (summary_start, raw_start) if d is not None]
        return min(candidates) if candidates else None

    def cleanup(self, retention_days: int = RETENTION_DAYS_DEFAULT, now: int | None = None):
        """
        古いハートビートを日次サマリーに畳み込んで削除します (B-8/F-2)。

        - retention_days より古い UTC 日付のハートビートは、センサー毎の日次サマリー
          (sensor_availability) に集約してから削除する
        - データが 1 件も無い日も、そのセンサーのデータ開始後であれば received=0 の
          サマリーを残す (累計受信率が水増しされないようにするため)
        - 通信エラーはサマリー対象外なので retention_days の 3 倍で削除する
        """
        if now is None:
            now = int(time.time())

        # NOTE: 24 時間受信率の計算が生データだけで完結するよう、最低 2 日は残す
        retention_days = max(retention_days, 2)

        boundary = datetime.datetime.fromtimestamp(now, datetime.UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - datetime.timedelta(days=retention_days)
        boundary_ts = int(boundary.timestamp())

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sensor_heartbeats WHERE timestamp < ?", (boundary_ts,)
            )
            if cursor.fetchone()[0] == 0:
                return

            # 対象センサー毎に、データ開始日から boundary 前日までの日次サマリーを作成
            cursor = conn.execute(
                "SELECT sensor_name, MIN(timestamp) FROM sensor_heartbeats GROUP BY sensor_name"
            )
            sensor_first = dict(cursor.fetchall())

            for sensor_name, first_ts in sensor_first.items():
                first_day = datetime.datetime.fromtimestamp(first_ts, datetime.UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day = first_day
                while day < boundary:
                    day_start_slot = int(day.timestamp()) // TIME_SLOT_SEC
                    day_end_slot = day_start_slot + SLOTS_PER_DAY - 1

                    cursor = conn.execute(
                        """
                        SELECT COUNT(DISTINCT time_slot) FROM sensor_heartbeats
                        WHERE sensor_name = ? AND time_slot >= ? AND time_slot <= ?
                        """,
                        (sensor_name, day_start_slot, day_end_slot),
                    )
                    received = cursor.fetchone()[0]

                    date_str = day.strftime("%Y-%m-%d")
                    conn.execute(
                        """
                        INSERT INTO sensor_availability
                        (sensor_name, date, total_expected, total_received, availability_percent)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(sensor_name, date) DO NOTHING
                        """,
                        (
                            sensor_name,
                            date_str,
                            SLOTS_PER_DAY,
                            received,
                            round(received / SLOTS_PER_DAY * 100, 2),
                        ),
                    )
                    day += datetime.timedelta(days=1)

            deleted_heartbeats = conn.execute(
                "DELETE FROM sensor_heartbeats WHERE timestamp < ?", (boundary_ts,)
            ).rowcount
            deleted_errors = conn.execute(
                "DELETE FROM communication_errors WHERE timestamp < ?",
                (now - retention_days * 3 * 86400,),
            ).rowcount
            conn.commit()

            logging.info(
                "Cleanup metrics: folded %d heartbeats and %d errors older than %s",
                deleted_heartbeats,
                deleted_errors,
                boundary.strftime("%Y-%m-%d"),
            )

            conn.execute("VACUUM")

    def maybe_cleanup(self, retention_days: int = RETENTION_DAYS_DEFAULT):
        """前回実行から 1 日以上経過していれば cleanup を実行します。"""
        now = time.time()
        if now - self._last_cleanup < 86400:
            return

        self._last_cleanup = now
        try:
            self.cleanup(retention_days, now=int(now))
        except sqlite3.Error:
            logging.exception("Failed to cleanup metrics")

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
            時間帯別ヒストグラムデータ（30分刻みで固定）

        """
        now = int(time.time())
        start_timestamp = now - (hours * 3600)  # hours時間前

        # 常に48 binのヒストグラム（30分刻みで時間帯別に集計）
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

            # 常に時間帯別に集計（過去のデータも含めて時間帯ごとに集計）
            for row in cursor.fetchall():
                error_timestamp = row[0]
                # UTCタイムスタンプを日本時間に変換
                utc_datetime = datetime.datetime.fromtimestamp(error_timestamp, datetime.UTC)
                jst_datetime = utc_datetime.astimezone(my_lib.time.get_zoneinfo())

                # 日本時間での0時からの経過秒数に変換（日付に関係なく時間帯で集計）
                hour = jst_datetime.hour
                minute = jst_datetime.minute
                seconds_from_midnight = hour * 3600 + minute * 60 + jst_datetime.second

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
                dt = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
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
