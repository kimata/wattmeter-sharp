"""デバイス情報を返す Flask API。"""

import logging
from pathlib import Path

import flask
import my_lib.flask_util

import sharp_hems.device
import sharp_hems.sniffer

blueprint = flask.Blueprint("webapi-device", __name__)


@blueprint.route("/api/devices/unknown", methods=["GET"])
@my_lib.flask_util.support_jsonp
def devices_unknown():
    """
    観測されたが device.yaml に未登録のデバイスを返すAPI。

    Returns:
        JSON: {
            "devices": [
                {"dev_id": "0x1234", "addr": "00:12:4b:..."}
            ]
        }

    """
    try:
        config = flask.current_app.config["CONFIG"]

        dev_id_map, _ = sharp_hems.sniffer.read_dev_id_map(config["device"]["cache"])
        sharp_hems.device.reload(Path(config["device"]["define"]))

        unknown = [
            {"dev_id": f"0x{dev_id:04X}", "addr": addr.lower()}
            for dev_id, addr in sorted(dev_id_map.items())
            if sharp_hems.device.get_name(addr) is None
        ]

        return flask.jsonify({"devices": unknown})

    except Exception as e:
        logging.exception("Failed to get unknown devices")
        flask.abort(500, f"Failed to get unknown devices: {e!s}")
