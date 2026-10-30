"""Sensors for the Junctek KG-F Bluetooth integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JunctekConfigEntry
from .device import JunctekDevice
from .entity import JunctekEntity
from .parser import JunctekState

AMPERE_HOUR = "Ah"


@dataclass(frozen=True, kw_only=True)
class JunctekSensorDescription(SensorEntityDescription):
    """Describes a Junctek sensor and how to restore it after a restart."""

    restore: Callable[[JunctekState, float], None] | None = None


def _set(attr: str) -> Callable[[JunctekState, float], None]:
    def _restore(state: JunctekState, value: float) -> None:
        if getattr(state, attr) is None:
            setattr(state, attr, value)

    return _restore


def _restore_current(state: JunctekState, value: float) -> None:
    if state.current_abs is None:
        state.current_abs = abs(value)
        state.charging = value > 0


def _restore_power(state: JunctekState, value: float) -> None:
    if state.power_abs is None:
        state.power_abs = abs(value)


SENSORS: tuple[JunctekSensorDescription, ...] = (
    JunctekSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        restore=_set("voltage"),
    ),
    JunctekSensorDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        restore=_restore_current,
    ),
    JunctekSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        restore=_restore_power,
    ),
    JunctekSensorDescription(
        key="soc",
        translation_key="soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    JunctekSensorDescription(
        key="remaining_ah",
        translation_key="remaining_ah",
        native_unit_of_measurement=AMPERE_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:battery-charging-outline",
        restore=_set("remaining_ah"),
    ),
    JunctekSensorDescription(
        key="time_left",
        translation_key="time_left",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        restore=_set("minutes_left"),
    ),
    JunctekSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        restore=_set("temperature"),
    ),
    JunctekSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=["charging", "discharging", "idle"],
    ),
    JunctekSensorDescription(
        key="charged_ah",
        translation_key="charged_ah",
        native_unit_of_measurement=AMPERE_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-plus-outline",
        restore=_set("charged_ah"),
    ),
    JunctekSensorDescription(
        key="discharged_ah",
        translation_key="discharged_ah",
        native_unit_of_measurement=AMPERE_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-minus-outline",
        restore=_set("discharged_ah"),
    ),
)

RSSI_SENSOR = JunctekSensorDescription(
    key="rssi",
    translation_key="rssi",
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JunctekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the Junctek sensors."""
    device = entry.runtime_data
    entities: list[JunctekEntity] = [JunctekSensor(device, d) for d in SENSORS]
    entities.append(JunctekRssiSensor(device, RSSI_SENSOR))
    async_add_entities(entities)


class JunctekSensor(JunctekEntity, RestoreSensor):
    """A value decoded from the monitor."""

    entity_description: JunctekSensorDescription

    def __init__(self, device: JunctekDevice, description: JunctekSensorDescription) -> None:
        super().__init__(device, description)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # The monitor only sends values that change, so keep the last known
        # value across Home Assistant restarts until a new one arrives.
        if self.entity_description.restore is None:
            return
        last = await self.async_get_last_sensor_data()
        if last is None or last.native_value is None:
            return
        try:
            value = float(last.native_value)
        except (TypeError, ValueError):
            return
        self.entity_description.restore(self._device.parser.state, value)

    @property
    def native_value(self) -> float | str | None:
        return self._device.data.get(self.entity_description.key)


class JunctekRssiSensor(JunctekEntity, RestoreSensor):
    """Bluetooth signal strength of the monitor."""

    @property
    def native_value(self) -> int | None:
        return self._device.rssi
