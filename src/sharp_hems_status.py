#!/usr/bin/env python3
"""
定義されたデバイスに対しで電力データが取得できているかチェックします．

Usage:
  sharp_hmes_status.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-T] [-d]

Options:
  -c CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -d                : デバッグモードで動作します．
"""

import logging

import my_lib.sensor_data

import sharp_hems.device

# def fetch_data(  # noqa: PLR0913
#     db_config,
#     measure,
#     hostname,
#     field,
#     start="-30h",
#     stop="now()",
#     every_min=1,
#     window_min=3,
#     create_empty=True,
#     last=False,
# ):


def hems_status_check(config, dev_define_file):
    sharp_hems.device.reload(dev_define_file)

    for dev_name in sharp_hems.device.get_list():
        data_valid = my_lib.sensor_data.fetch_data(
            config["influxdb"],
            "{tag}.{label}".format(
                tag=config["fluentd"]["data"]["tag"], label=config["fluentd"]["data"]["label"]
            ),
            dev_name,
            config["fluentd"]["data"]["field"],
            "-1h",
        )["valid"]
        if data_valid:
            logging.info("{name:0s}: OK".format(name=dev_name))
        else:
            logging.error("{name:0s}: NG".format(name=dev_name))


######################################################################
if __name__ == "__main__":
    import pathlib

    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-d"]

    my_lib.logger.init("hems.wattmeter-sharp", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file)

    dev_define_file = pathlib.Path(config["device"]["define"])

    hems_status_check(config, dev_define_file)
