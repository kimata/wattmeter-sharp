#!/usr/bin/env python3
"""
定義されたデバイスに対して電力データが取得できているかチェックします。

Usage:
  sharp_hems_status.py [-c CONFIG] [-D]

Options:
  -c CONFIG         : 設定ファイルを指定します。 [default: config.yaml]
  -D                : デバッグモードで動作します。
"""

import logging
import pathlib

import my_lib.sensor_data

import sharp_hems.device

SCHEMA_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config.schema"


def hems_status_check(config, dev_define_file):
    sharp_hems.device.reload(dev_define_file)

    db_config = my_lib.sensor_data.InfluxDBConfig.parse(config["influxdb"])

    for dev_name in sharp_hems.device.get_list():
        data_valid = my_lib.sensor_data.fetch_data(
            db_config,
            "{tag}.{label}".format(
                tag=config["fluentd"]["data"]["tag"], label=config["fluentd"]["data"]["label"]
            ),
            dev_name,
            config["fluentd"]["data"]["field"],
            "-1h",
        ).valid
        if data_valid:
            logging.info("%0s: OK", dev_name)
        else:
            logging.error("%0s: NG", dev_name)


######################################################################
if __name__ == "__main__":
    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-D"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, SCHEMA_CONFIG)

    dev_define_file = pathlib.Path(config["device"]["define"])

    hems_status_check(config, dev_define_file)
