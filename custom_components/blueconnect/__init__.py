"""The BlueConnect Go BLE integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator, UpdateFailed

from .BlueConnectGo import BlueConnectGoBluetoothDeviceData
from .const import CONF_FIT50_MODE, CONF_PUMP_ENTITY, DEFAULT_MEASUREMENT_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BlueConnect Go BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id

    _LOGGER.debug("async_setup_entry")
    assert address is not None

    ble_device = bluetooth.async_ble_device_from_address(hass, address)

    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find BlueConnect Go device with address {address}"
        )

    async def _async_update_method():
        """Get data from BlueConnect Go BLE."""
        _LOGGER.debug("async_update_method")

        # Check if Fit50 mode is enabled
        fit50_mode = entry.data.get(CONF_FIT50_MODE, False)
        pump_entity = entry.data.get(CONF_PUMP_ENTITY)

        # If Fit50 mode is enabled, check pump state (but skip check for first measurement)
        if fit50_mode and pump_entity and coordinator.data is not None:
            pump_state = hass.states.get(pump_entity)
            if pump_state is None:
                _LOGGER.warning(f"Pump entity {pump_entity} not found")
            elif pump_state.state not in ["on", "true", "1"]:
                _LOGGER.debug(f"Pump is off (state: {pump_state.state}), skipping measurement")
                # Return current data without updating
                return coordinator.data

        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        bcgo = BlueConnectGoBluetoothDeviceData(_LOGGER)

        try:
            data = await bcgo.update_device(ble_device)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data

    # Use default interval initially - will be updated by the number entity
    coordinator = TimestampDataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=int(DEFAULT_MEASUREMENT_INTERVAL * 3600)),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
