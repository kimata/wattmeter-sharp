#!/usr/bin/env python3
import logging
import re
import time

import pytest
import requests
from playwright.sync_api import expect

APP_URL_TMPL = "http://{host}:{port}/wattmeter-sharp/"


@pytest.fixture(autouse=True)
def _page_init(page, host, port, webserver):
    # If webserver fixture is used, it will already have started the server
    # Otherwise, wait for an externally started server
    if webserver is None:
        wait_for_server_ready(host, port)

    time.sleep(3)

    page.on("console", lambda msg: print(msg.text))  # noqa: T201
    page.set_viewport_size({"width": 2400, "height": 1600})


def wait_for_server_ready(host, port):
    TIMEOUT_SEC = 60

    start_time = time.time()
    while time.time() - start_time < TIMEOUT_SEC:
        try:
            res = requests.get(app_url(host, port))  # noqa: S113
            if res.ok:
                logging.info("サーバが %.1f 秒後に起動しました。", time.time() - start_time)
                # NOTE: ページのロードに時間がかかるので、少し待つ
                time.sleep(15)
                return
        except Exception:  # noqa: S110
            pass
        time.sleep(2)

    raise RuntimeError(f"サーバーが {TIMEOUT_SEC}秒以内に起動しませんでした。")


def app_url(host, port):
    return APP_URL_TMPL.format(host=host, port=port)


######################################################################
def test_sensor_monitoring_app(page, host, port):
    """センサー監視アプリの基本機能をテストします。"""
    page.goto(app_url(host, port))

    # ページタイトルとメイン要素の確認
    expect(page.get_by_test_id("app-title")).to_have_text("SHARP HEMS センサー稼働状態")
    expect(page.get_by_test_id("app")).to_have_count(1)

    # データ情報の確認
    expect(page.get_by_test_id("data-info")).to_have_count(1)
    expect(page.get_by_test_id("data-info")).to_contain_text("データ収集開始日")

    # チャートの確認
    expect(page.get_by_test_id("availability-chart")).to_have_count(1)

    # テーブルの確認
    expect(page.get_by_test_id("sensor-table")).to_have_count(1)
    expect(page.get_by_test_id("sensors-table")).to_have_count(1)

    # フッターの確認
    expect(page.get_by_test_id("footer")).to_have_count(1)

    # エラー要素がないことを確認
    expect(page.get_by_test_id("error")).to_have_count(0)


def test_sensor_table_columns(page, host, port):
    """センサーテーブルの列構成をテストします。"""
    page.goto(app_url(host, port))

    # テーブルヘッダーの確認
    table = page.get_by_test_id("sensors-table")
    expect(table).to_be_visible()

    # 列ヘッダーの存在確認
    expect(table.locator("th:nth-child(1)")).to_contain_text("#")
    expect(table.locator("th:nth-child(2)")).to_contain_text("センサー名")
    expect(table.locator("th:nth-child(3)")).to_contain_text("累計稼働率")
    expect(table.locator("th:nth-child(4)")).to_contain_text("過去24時間")
    expect(table.locator("th:nth-child(5)")).to_contain_text("消費電力")
    expect(table.locator("th:nth-child(6)")).to_contain_text("最終受信")
    expect(table.locator("th:nth-child(7)")).to_contain_text("状態")


def test_sensor_table_sorting(page, host, port):
    """センサーテーブルのソート機能をテストします。"""
    page.goto(app_url(host, port))

    table = page.get_by_test_id("sensors-table")

    # センサー名でソート
    sensor_name_header = table.locator("th").filter(has_text="センサー名")
    sensor_name_header.click()

    # ソートアイコンが表示されることを確認
    expect(sensor_name_header).to_contain_text("▼")  # 降順ソート

    # 再度クリックで昇順ソート
    sensor_name_header.click()
    expect(sensor_name_header).to_contain_text("▲")  # 昇順ソート


def test_sensor_table_data_format(page, host, port):
    """センサーテーブルのデータ形式をテストします。"""
    page.goto(app_url(host, port))

    table = page.get_by_test_id("sensors-table")

    # テーブルにデータ行があることを確認
    rows = table.locator("tbody tr")
    expect(rows.first).to_be_visible()

    # 最初のデータ行をチェック
    if rows.count() > 0:
        first_row = rows.first

        # 各列のデータ形式を確認
        cells = first_row.locator("td")

        # インデックス番号（数字）
        expect(cells.nth(0)).to_contain_text(re.compile(r"^\d+$"))

        # センサー名（文字列）
        expect(cells.nth(1)).not_to_be_empty()

        # 稼働率（%付きの数値）
        expect(cells.nth(2)).to_contain_text("%")
        expect(cells.nth(3)).to_contain_text("%")

        # 消費電力（W単位またはN/A）
        power_cell = cells.nth(4)
        expect(power_cell).to_contain_text(re.compile(r"^(\d{1,3}(,\d{3})*\s*W|N/A)$"))

        # 最終受信（日付形式または-）
        last_received_cell = cells.nth(5)
        expect(last_received_cell).to_contain_text(
            re.compile(r"^(\d{1,2}/\d{1,2}\s+\d{2}:\d{2}:\d{2}.*|-|)$")
        )

        # 状態（タグ）
        status_cell = cells.nth(6)
        expect(status_cell.locator(".tag")).to_have_count(1)
        expect(status_cell.locator(".tag")).to_contain_text(re.compile(r"^(正常|警告|異常)$"))


def test_error_handling(page, host, port):
    """エラーハンドリングをテストします。"""
    # 存在しないエンドポイントにアクセス
    page.goto(f"http://{host}:{port}/wattmeter-sharp/nonexistent")

    # 404エラーページまたはエラーメッセージが表示されることを期待
    # (実際の実装に依存するため、基本的なページ構造のチェックのみ)
    expect(page).to_have_title("404 Not Found")


def test_responsive_design(page, host, port):
    """レスポンシブデザインをテストします。"""
    page.goto(app_url(host, port))

    # デスクトップサイズ
    page.set_viewport_size({"width": 1920, "height": 1080})
    expect(page.get_by_test_id("app")).to_be_visible()

    # タブレットサイズ
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.get_by_test_id("app")).to_be_visible()
    expect(page.get_by_test_id("sensor-table")).to_be_visible()

    # モバイルサイズ
    page.set_viewport_size({"width": 375, "height": 667})
    expect(page.get_by_test_id("app")).to_be_visible()
    expect(page.get_by_test_id("sensor-table")).to_be_visible()
