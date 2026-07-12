#!/usr/bin/env python3
"""
設定ファイル (config.yaml / device.yaml) の検証。

JSON Schema (config.schema / device.schema) の代替として、Pydantic モデルで
構造を検証する。アクセス側の互換性のため、検証後も元の dict / list を返す。
"""

import logging

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    # NOTE: 本番 config には my_lib 等が使う追加キーがあるため、未知のキーは許容する
    model_config = ConfigDict(extra="allow")


class SerialConfig(_Model):
    port: str


class FluentdDataConfig(_Model):
    tag: str
    label: str
    field: str


class FluentdConfig(_Model):
    host: str
    data: FluentdDataConfig


class InfluxDBConfig(_Model):
    url: str
    token: str
    org: str
    bucket: str


class DeviceFileConfig(_Model):
    define: str
    cache: str


class MetricsConfig(_Model):
    data: str
    retention_days: int = Field(default=30, ge=2)


class SensorConfig(_Model):
    watt_scale: float = Field(default=1.5, gt=0)


class AlertConfig(_Model):
    timeout_min: int = Field(default=30, gt=0)


class SmartMeterConfig(_Model):
    measure: str
    hostname: str
    field: str = "power"


class CalibrationConfig(_Model):
    smartmeter: SmartMeterConfig


class LivenessFileConfig(_Model):
    measure: str


class LivenessConfig(_Model):
    file: LivenessFileConfig


class AppConfig(_Model):
    serial: SerialConfig
    fluentd: FluentdConfig
    influxdb: InfluxDBConfig
    device: DeviceFileConfig
    metrics: MetricsConfig
    liveness: LivenessConfig
    webapp: dict
    sensor: SensorConfig | None = None
    alert: AlertConfig | None = None
    calibration: CalibrationConfig | None = None


class DeviceEntry(_Model):
    addr: str
    name: str
    scale: float | None = Field(default=None, gt=0)


def validate_config(config: dict) -> dict:
    """config.yaml の内容を検証し、そのまま返す。"""
    AppConfig.model_validate(config)
    logging.debug("Config validation passed")
    return config


def validate_device_list(dev_list: list) -> list:
    """device.yaml の内容を検証し、そのまま返す。"""
    if not isinstance(dev_list, list) or len(dev_list) == 0:
        msg = "device.yaml はデバイス定義のリストである必要があります"
        raise ValueError(msg)

    for entry in dev_list:
        DeviceEntry.model_validate(entry)

    return dev_list


def load(config_file, *, validate: bool = True) -> dict:
    """config.yaml をロードして検証する。"""
    import my_lib.config

    config = my_lib.config.load(config_file)
    if validate:
        validate_config(config)
    return config
