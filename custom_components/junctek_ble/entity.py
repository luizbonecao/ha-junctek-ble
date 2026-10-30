"""Base entity for the Junctek KG-F Bluetooth integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription

from .const import DOMAIN, MANUFACTURER, MODEL
from .device import JunctekDevice


class JunctekEntity(Entity):
    """Common device info and update wiring."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: JunctekDevice, description: EntityDescription) -> None:
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.address)},
            connections={(CONNECTION_BLUETOOTH, device.address)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Junctek {device.name}",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._device.async_add_listener(self.async_write_ha_state))
