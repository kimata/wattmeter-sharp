# SHARP HEMS ワットメータ

[![CI](https://gitlab.green-rabbit.net/kimata/wattmeter-sharp/badges/master/pipeline.svg)](https://gitlab.green-rabbit.net/kimata/wattmeter-sharp/-/pipelines)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 概要

シャープの HEMS コントローラ JH-AG01 のバイナリ形式の内部通信を解析し，電力センサーの計測値を取得するスクリプトです．

![JH-AG01](./img/JH-AG01.jpg)

## 準備

JH-AG01 を分解し，写真のようにコネクタターミナルから線だしを行い，Raspbeery Pi 等の UART 端子と接続します．

線だしするのは以下の端子になります．

| 端子                 | 信号名    |
|:---------------------|:----------|
| LANコネクタ側から2番目| GND      |
| LANコネクタ側から4番目| TX [^1]  |

[^1]: 基板上のシルクは Zigbee モジュール視点で書かれています．

## 必要な環境

- Python 3.10以上
- uv (Python のパッケージマネージャー)

## インストール

### uv のインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### プロジェクトの依存関係のインストール

```bash
uv sync
```

## 使い方

シリアルポートが `/dev/ttyAMA0` の場合，下記のようにします．

```bash
uv run python src/sharp_hems/serial_pubsub.py
```

実行してからしばらくすると，HEMS コントローラが収集したデータが下図のように表示されます．

![スクリーンショット](./img/screenshot.png)

値の意味は下記のとおりです．

| ラベル    | 内容                                            |
|:----------|:------------------------------------------------|
| dev_id    | デバイスID (プラグ個体値)                       |
| cur_time  | 現在の時刻(秒, 0xFFFF になると 0に戻ります)     |
| cur_power | 現在の積算電力(0xFFFFFFFF になると 0に戻ります) |
| pre_time  | 前回の時刻(秒, 0xFFFF になると 0に戻ります)     |
| pre_power | 前回の積算電力(0xFFFFFFFF になると 0に戻ります) |
| watt      | 前回と現在の時刻と積算電力から計算した平均電力  |

データの収集は6分間隔で行われるようなので，時刻は 240 づつ増加します．

## 開発・テスト

### テストの実行

```bash
uv run pytest
```

### コードフォーマット・リント

設定ファイルのフォーマットチェック：

```bash
uv run python scripts/check_config_format.py
```

## 応用

`src/sharp_hems_server.py` と `src/sharp_hems_logger.py` を使うと，定期的に電力計測し，Fluentd に送信することができます．
設定は `config.yaml` と `device.yaml` で行います．

2つのスクリプトは ZMQ で PubSub パターンでデータを受け渡すようになっていて，別のホストで実行可能です．

### サーバーの起動

```bash
uv run python src/sharp_hems_server.py
```

### ロガーの起動

```bash
uv run python src/sharp_hems_logger.py
```

## Docker での実行

### イメージのビルド

```bash
docker build -t wattmeter-sharp .
```

### コンテナの実行

```bash
docker run -d --name wattmeter-sharp wattmeter-sharp
```

## ヒント

HEMS コントローラの IP アドレスにアクセスすると，Web インターフェースを表示できます．ID，パスワード共に root でログインできます．

接続されているコンセントや動作ログ等が確認できるので便利です．

## ライセンス

MIT License

## 作者

KIMATA Tetsuya (kimata@green-rabbit.net)
