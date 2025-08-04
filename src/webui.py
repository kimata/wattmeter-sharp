#!/usr/bin/env python3
"""
電力計のデータ収集状況を表示する Web サーバです。

Usage:
  webui.py [-c CONFIG] [-p PORT] [-D]

Options:
  -c CONFIG         : 通常モードで使う設定ファイルを指定します。[default: config.yaml]
  -p PORT           : WEB サーバのポートを指定します。[default: 5000]
  -D                : デバッグモードで動作します。
"""

import logging
import os
import pathlib
import signal

import flask
import flask_cors
import my_lib.config
import my_lib.logger

SCHEMA_CONFIG = "config.schema"


def term():
    # 子プロセスを終了
    my_lib.proc_util.kill_child()

    # プロセス終了
    logging.info("Graceful shutdown completed")
    os._exit(0)


def sig_handler(num, frame):  # noqa: ARG001
    logging.warning("receive signal %d", num)

    if num in (signal.SIGTERM, signal.SIGINT):
        term()


def create_app(config):
    # NOTE: アクセスログは無効にする
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    import my_lib.webapp.config

    my_lib.webapp.config.URL_PREFIX = "/wattmeter-sharp"
    my_lib.webapp.config.init(config)

    import my_lib.webapp.base
    import my_lib.webapp.util

    import sharp_hems.webui.webapi.sensor_stat

    app = flask.Flask("wattmeter-sharp")

    flask_cors.CORS(app)

    app.config["CONFIG"] = config

    app.register_blueprint(my_lib.webapp.base.blueprint, url_prefix=my_lib.webapp.config.URL_PREFIX)
    app.register_blueprint(my_lib.webapp.base.blueprint_default)
    app.register_blueprint(my_lib.webapp.util.blueprint, url_prefix=my_lib.webapp.config.URL_PREFIX)
    app.register_blueprint(
        sharp_hems.webui.webapi.sensor_stat.blueprint, url_prefix=my_lib.webapp.config.URL_PREFIX
    )

    my_lib.webapp.config.show_handler_list(app)

    return app


if __name__ == "__main__":
    import docopt

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    port = args["-p"]
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, pathlib.Path(SCHEMA_CONFIG))

    app = create_app(config)

    signal.signal(signal.SIGTERM, sig_handler)

    # Flaskアプリケーションを実行
    try:
        # NOTE: スクリプトの自動リロード停止したい場合は use_reloader=False にする
        app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=True, debug=debug_mode)  # noqa: S104
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt, shutting down...")
        sig_handler(signal.SIGINT, None)
