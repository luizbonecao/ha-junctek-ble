"""Config flow: find the Junctek over Bluetooth and add it with one click."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CAPACITY_AH,
    DEFAULT_CAPACITY_AH,
    DOMAIN,
    NAME_PREFIXES,
    SERVICE_UUID,
)

CAPACITY_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=1, max=2000, step=1, mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="Ah",
    )
)


def _looks_like_junctek(info: BluetoothServiceInfoBleak) -> bool:
    name = (info.name or "").upper()
    return name.startswith(NAME_PREFIXES) or SERVICE_UUID in info.service_uuids


class JunctekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Junctek KG-F Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._found: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """A Junctek was heard by a Bluetooth adapter or proxy."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the discovered device and ask the battery capacity."""
        assert self._discovery is not None
        name = self._discovery.name or self._discovery.address
        if user_input is not None:
            return self._create(self._discovery.address, name, user_input)
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CAPACITY_AH, default=DEFAULT_CAPACITY_AH
                    ): CAPACITY_SELECTOR
                }
            ),
            description_placeholders={"name": name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a Junctek from the devices currently heard over Bluetooth."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            name = self._found.get(address) or ""
            if not name or name == address or name == "Sem nome":
                for info in async_discovered_service_info(self.hass, connectable=True):
                    if info.address == address and info.name and info.name != address:
                        name = info.name
                        break
            if not name or name == "Sem nome":
                name = address
            return self._create(address, name, user_input)

        configured = self._async_current_ids(include_ignore=False)
        self._found = {}
        others: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in configured:
                continue
            label = f"{info.name or 'Sem nome'} ({info.address})"
            if _looks_like_junctek(info):
                self._found[info.address] = info.name or info.address
            else:
                others[info.address] = label
        if not self._found and not others:
            return self.async_abort(reason="no_devices_found")

        options = [
            selector.SelectOptionDict(value=addr, label=f"{name} ({addr})")
            for addr, name in self._found.items()
        ] + [
            selector.SelectOptionDict(value=addr, label=label)
            for addr, label in sorted(others.items(), key=lambda x: x[1])
        ]
        for addr, label in others.items():
            self._found.setdefault(addr, label.split(" (")[0])
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    ),
                    vol.Required(
                        CONF_CAPACITY_AH, default=DEFAULT_CAPACITY_AH
                    ): CAPACITY_SELECTOR,
                }
            ),
        )

    @callback
    def _create(
        self, address: str, name: str, user_input: dict[str, Any]
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title=f"Junctek {name}",
            data={
                CONF_ADDRESS: address,
                CONF_NAME: name,
                CONF_CAPACITY_AH: float(user_input[CONF_CAPACITY_AH]),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options: change the battery capacity later."""
        return JunctekOptionsFlow()


class JunctekOptionsFlow(OptionsFlow):
    """Change the battery capacity."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_CAPACITY_AH: float(user_input[CONF_CAPACITY_AH])}
            )
        current = self.config_entry.options.get(
            CONF_CAPACITY_AH,
            self.config_entry.data.get(CONF_CAPACITY_AH, DEFAULT_CAPACITY_AH),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_CAPACITY_AH, default=current): CAPACITY_SELECTOR}
            ),
        )
