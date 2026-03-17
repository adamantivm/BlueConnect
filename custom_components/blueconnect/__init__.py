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
from .const import CONF_FIT50_MODE, CONF_MEASUREMENT_INTERVAL, CONF_PUMP_ENTITY, DEFAULT_MEASUREMENT_INTERVAL, DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.BINARY_SENSOR]

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

        # If Fit50 mode is enabled, check pump state before taking any measurement
        if fit50_mode and pump_entity:
            pump_state = hass.states.get(pump_entity)
            if pump_state is None:
                _LOGGER.warning(f"Pump entity {pump_entity} not found")
            elif pump_state.state not in ["on", "true", "1"]:
                _LOGGER.debug(f"Pump is off (state: {pump_state.state}), skipping measurement")
                # Only return current data if we actually have previous data;
                # on first refresh, coordinator.data is None so we must take a measurement.
                if coordinator.data is not None:
                    return coordinator.data
                _LOGGER.debug(
                    "No previous data available while pump is off; performing initial measurement"
                )

        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        bcgo = BlueConnectGoBluetoothDeviceData(_LOGGER)

        try:
            data = await bcgo.update_device(ble_device)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data

    # Get the measurement interval from config entry, or use default
    measurement_interval = entry.data.get(CONF_MEASUREMENT_INTERVAL, DEFAULT_MEASUREMENT_INTERVAL)

    # Use the stored interval (or default if not set)
    coordinator = TimestampDataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=int(measurement_interval * 3600)) if measurement_interval > 0 else None,
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
