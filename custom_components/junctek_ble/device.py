"""Keeps a Bluetooth connection to the Junctek monitor and decodes its data."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from .const import NOTIFY_UUID, PUBLISH_INTERVAL, RECONNECT_DELAY
from .parser import JunctekParser

_LOGGER = logging.getLogger(__name__)


class JunctekDevice:
    """One Junctek monitor: connection loop, decoding and listeners."""

    def __init__(
        self, hass: HomeAssistant, address: str, name: str, capacity_ah: float
    ) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.parser = JunctekParser(capacity_ah)
        self.connected = False
        self.rssi: int | None = None
        self._client: BleakClient | None = None
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._disconnected = asyncio.Event()
        self._seen = asyncio.Event()
        self._publish_handle: asyncio.TimerHandle | None = None
        self._unsub_bt: CALLBACK_TYPE | None = None

    # ------------------------------------------------------------ listeners
    @callback
    def async_add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an entity update callback."""
        self._listeners.append(update)

        @callback
        def _remove() -> None:
            self._listeners.remove(update)

        return _remove

    @callback
    def _notify_listeners(self) -> None:
        self._publish_handle = None
        for update in list(self._listeners):
            update()

    @callback
    def _schedule_publish(self) -> None:
        """Limit state writes: the monitor sends many frames per second."""
        if self._publish_handle is None:
            self._publish_handle = self.hass.loop.call_later(
                PUBLISH_INTERVAL, self._notify_listeners
            )

    @property
    def data(self) -> dict[str, Any]:
        """Current values for the sensors."""
        return self.parser.state.as_dict()

    def set_capacity(self, capacity_ah: float) -> None:
        """Change the battery capacity used for the percentage."""
        self.parser.state.capacity_ah = capacity_ah
        self._schedule_publish()

    # ------------------------------------------------------------ lifecycle
    async def async_start(self) -> None:
        """Start listening for the device and connecting to it."""
        self._unsub_bt = bluetooth.async_register_callback(
            self.hass,
            self._async_on_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=self.address, connectable=True),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        self._task = self.hass.async_create_background_task(
            self._run(), f"junctek_ble {self.address}"
        )

    async def async_stop(self) -> None:
        """Disconnect and stop the connection loop."""
        self._stop.set()
        self._seen.set()
        self._disconnected.set()
        if self._unsub_bt:
            self._unsub_bt()
            self._unsub_bt = None
        if self._publish_handle:
            self._publish_handle.cancel()
            self._publish_handle = None
        if self._client is not None:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    @callback
    def _async_on_advertisement(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        self.rssi = service_info.rssi
        self._seen.set()

    # ------------------------------------------------------------ connection
    def _ble_device(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    @callback
    def _on_disconnect(self, _client: BleakClient) -> None:
        _LOGGER.debug("%s: disconnected", self.name)
        self.connected = False
        self._disconnected.set()
        self._notify_listeners()

    def _on_notify(self, _sender: Any, data: bytearray) -> None:
        if self.parser.feed(data):
            self.hass.loop.call_soon_threadsafe(self._schedule_publish)

    async def _run(self) -> None:
        while not self._stop.is_set():
            ble_device = self._ble_device()
            if ble_device is None:
                # wait until a Bluetooth adapter or proxy hears the device
                self._seen.clear()
                try:
                    await asyncio.wait_for(self._seen.wait(), timeout=60)
                except TimeoutError:
                    pass
                continue
            try:
                await self._connect_and_listen(ble_device)
            except (BleakError, TimeoutError, OSError) as err:
                _LOGGER.debug("%s: connection failed: %s", self.name, err)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _LOGGER.exception("%s: unexpected error", self.name)
            finally:
                self.connected = False
                self._client = None
            if not self._stop.is_set():
                await asyncio.sleep(RECONNECT_DELAY)

    async def _connect_and_listen(self, ble_device: BLEDevice) -> None:
        self._disconnected.clear()
        self.parser.reset_stream()
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.name,
            disconnected_callback=self._on_disconnect,
            max_attempts=3,
            ble_device_callback=self._ble_device,
        )
        self._client = client
        try:
            await client.start_notify(NOTIFY_UUID, self._on_notify)
            self.connected = True
            _LOGGER.info("%s: connected", self.name)
            self._notify_listeners()
            await self._disconnected.wait()
        finally:
            if client.is_connected:
                try:
                    await client.disconnect()
                except BleakError:
                    pass
