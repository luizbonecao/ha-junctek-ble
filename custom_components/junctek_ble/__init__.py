"""Junctek KG-F battery monitor over Bluetooth."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CAPACITY_AH, DEFAULT_CAPACITY_AH
from .device import JunctekDevice

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type JunctekConfigEntry = ConfigEntry[JunctekDevice]


def _capacity(entry: ConfigEntry) -> float:
    return float(
        entry.options.get(
            CONF_CAPACITY_AH, entry.data.get(CONF_CAPACITY_AH, DEFAULT_CAPACITY_AH)
        )
    )


async def async_setup_entry(hass: HomeAssistant, entry: JunctekConfigEntry) -> bool:
    """Set up a Junctek monitor from a config entry."""
    device = JunctekDevice(
        hass,
        entry.data[CONF_ADDRESS],
        entry.data.get(CONF_NAME) or entry.title,
        _capacity(entry),
    )
    entry.runtime_data = device
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await device.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: JunctekConfigEntry) -> None:
    entry.runtime_data.set_capacity(_capacity(entry))


async def async_unload_entry(hass: HomeAssistant, entry: JunctekConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
