#!/usr/bin/env python3
import logging
import re
import time

import pytest
import requests
from playwright.sync_api import expect

APP_URL_TMPL = "http://{host}:{port}/wattmeter-sharp/metrics/"


@pytest.fixture(autouse=True)
def _page_init(page, host, port, webserver):
    # If webserver fixture is used, it will already have started the server
    # Otherwise, wait for an externally started server
    if webserver is None:
        wait_for_server_ready(host, port)

    time.sleep(1)

    page.on("console", lambda msg: print(msg.text))  # noqa: T201
    page.set_viewport_size({"width": 2400, "height": 1600})


def wait_for_server_ready(host, port):
    TIMEOUT_SEC = 60

    start_time = time.time()
    while time.time() - start_time < TIMEOUT_SEC:
        try:
            res = requests.get(get_app_url(host, port))  # noqa: S113
            if res.ok:
                logging.info("サーバが %.1f 秒後に起動しました。", time.time() - start_time)
                # NOTE: ページのロードに時間がかかるので、少し待つ
                time.sleep(5)
                return
        except Exception:  # noqa: S110
            pass
        time.sleep(2)

    raise RuntimeError(f"サーバーが {TIMEOUT_SEC}秒以内に起動しませんでした。")


def get_app_url(host, port):
    return APP_URL_TMPL.format(host=host, port=port)


######################################################################
def test_power_dashboard(page, host, port):
    """電力タブ (メイン画面) の基本構成をテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    # ページタイトルとメイン要素の確認
    expect(page.get_by_test_id("app-title")).to_contain_text("おうち電力モニター")
    expect(page.get_by_test_id("app")).to_have_count(1)

    # ヒーロー (現在の合計消費電力)
    expect(page.get_by_test_id("power-hero")).to_be_visible()
    expect(page.get_by_test_id("total-watt")).to_contain_text("W")
    expect(page.get_by_test_id("conn-summary")).to_contain_text("/")

    # 電力推移チャートと期間セレクタ
    expect(page.get_by_test_id("trend-chart")).to_be_visible()
    for key in ["3h", "24h", "7d", "30d"]:
        expect(page.get_by_test_id(f"range-{key}")).to_be_visible()

    # デバイス別カード
    expect(page.get_by_test_id("device-grid")).to_be_visible()
    expect(page.get_by_test_id("device-card").first).to_be_visible()

    # 電力量ランキング
    expect(page.get_by_test_id("energy-ranking")).to_be_visible()

    # フッター
    expect(page.get_by_test_id("footer")).to_have_count(1)

    # エラーバナーがないことを確認
    expect(page.get_by_test_id("error-banner")).to_have_count(0)


def test_range_selector(page, host, port):
    """電力推移チャートの期間切り替えをテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    expect(page.get_by_test_id("range-24h")).to_have_class(re.compile(r"active"))

    page.get_by_test_id("range-3h").click()
    expect(page.get_by_test_id("range-3h")).to_have_class(re.compile(r"active"))
    expect(page.get_by_test_id("range-24h")).not_to_have_class(re.compile(r"active"))

    # 切り替え後もチャートカードが表示されたまま
    expect(page.get_by_test_id("trend-chart")).to_be_visible()


def test_connection_status_tab(page, host, port):
    """接続状態タブの構成をテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    page.get_by_test_id("tab-connection").click()
    expect(page.get_by_test_id("connection-status")).to_be_visible()

    # 受信状態テーブル
    table = page.get_by_test_id("sensor-table")
    expect(table).to_be_visible()

    expect(table.locator("th").nth(0)).to_contain_text("デバイス")
    expect(table.locator("th").nth(1)).to_contain_text("状態")
    expect(table.locator("th").nth(2)).to_contain_text("受信率 (24時間)")
    expect(table.locator("th").nth(3)).to_contain_text("受信率 (累計)")
    expect(table.locator("th").nth(4)).to_contain_text("最終受信")

    rows = table.locator("tbody tr")
    expect(rows.first).to_be_visible()

    if rows.count() > 0:
        first_row = rows.first
        cells = first_row.locator("td")

        # デバイス名 (文字列)
        expect(cells.nth(0)).not_to_be_empty()

        # 状態 (チップ)
        expect(cells.nth(1).locator(".chip")).to_contain_text(re.compile(r"^(接続中|不安定|切断|長期切断)$"))

        # 受信率 (%付きの数値)
        expect(cells.nth(2)).to_contain_text("%")
        expect(cells.nth(3)).to_contain_text("%")

    # 切断ヒストグラムと切断ログ
    expect(page.get_by_test_id("error-chart")).to_be_visible()
    expect(page.get_by_test_id("error-table")).to_be_visible()


def test_sensor_table_sorting(page, host, port):
    """受信状態テーブルのソート機能をテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    page.get_by_test_id("tab-connection").click()
    table = page.get_by_test_id("sensor-table")

    name_header = table.locator("th").filter(has_text="デバイス")
    name_header.click()
    expect(name_header).to_contain_text("▲")  # 昇順ソート

    name_header.click()
    expect(name_header).to_contain_text("▼")  # 降順ソート


def test_tab_switching(page, host, port):
    """タブ切り替えをテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    # 初期状態は電力タブ
    expect(page.get_by_test_id("tab-power")).to_have_class(re.compile(r"active"))
    expect(page.get_by_test_id("power-hero")).to_be_visible()

    # 接続状態タブへ
    page.get_by_test_id("tab-connection").click()
    expect(page.get_by_test_id("tab-connection")).to_have_class(re.compile(r"active"))
    expect(page.get_by_test_id("connection-status")).to_be_visible()

    # 電力タブへ戻る
    page.get_by_test_id("tab-power").click()
    expect(page.get_by_test_id("power-hero")).to_be_visible()


def test_error_handling(page, host, port):
    """エラーハンドリングをテストします。"""
    # 存在しないエンドポイントにアクセス
    page.goto(get_app_url(host, port) + "nonexistent")

    # 404エラーページまたはエラーメッセージが表示されることを期待
    # (実際の実装に依存するため、基本的なページ構造のチェックのみ)
    expect(page).to_have_title("404 Not Found")


def test_responsive_design(page, host, port):
    """レスポンシブデザインをテストします。"""
    page.goto(get_app_url(host, port), wait_until="domcontentloaded")

    # デスクトップサイズ
    page.set_viewport_size({"width": 1920, "height": 1080})
    expect(page.get_by_test_id("app")).to_be_visible()

    # タブレットサイズ
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.get_by_test_id("app")).to_be_visible()
    expect(page.get_by_test_id("device-grid")).to_be_visible()

    # モバイルサイズ
    page.set_viewport_size({"width": 375, "height": 667})
    expect(page.get_by_test_id("app")).to_be_visible()
    expect(page.get_by_test_id("device-grid")).to_be_visible()
