"""Support for BlueConnect Go BLE number entities."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .BlueConnectGo import BlueConnectGoDevice
from .const import CONF_DEVICE_NAME, CONF_DEVICE_TYPE, DEFAULT_MEASUREMENT_INTERVAL, DEVICE_TYPE_PLUS, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go BLE number entities."""

    coordinator: DataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
        entry.entry_id
    ]

    async_add_entities([
        MeasurementIntervalNumber(coordinator, coordinator.data, entry),
    ])


class MeasurementIntervalNumber(
    CoordinatorEntity[DataUpdateCoordinator[BlueConnectGoDevice]], NumberEntity
):
    """Number entity for measurement interval configuration."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 999  # Effectively unlimited
    _attr_native_step = 0.25
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        blueconnect_go_device: BlueConnectGoDevice,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the measurement interval number entity."""
        super().__init__(coordinator)
        self.entry = entry

        # Use custom device name from config entry if available
        device_name = entry.data.get(CONF_DEVICE_NAME)
        if not device_name:
            # Fallback to default name
            device_name = f"{blueconnect_go_device.name} {blueconnect_go_device.identifier}"

        self._attr_unique_id = f"{blueconnect_go_device.address}_measurement_interval"
        self._attr_name = "Measurement Interval"

        # Get device model from config entry
        device_type = entry.data.get(CONF_DEVICE_TYPE)
        if device_type == DEVICE_TYPE_PLUS:
            model = "Blue Connect Plus"
        else:
            model = "Blue Connect Go"

        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    blueconnect_go_device.address,
                )
            },
            name=device_name,
            manufacturer="Blueriiot",
            model=model,
            hw_version=blueconnect_go_device.hw_version,
            sw_version=blueconnect_go_device.sw_version,
        )

    @property
    def native_value(self) -> float:
        """Return the current measurement interval in hours."""
        # Get from coordinator's update_interval if available, else use default
        if hasattr(self.coordinator, 'update_interval') and self.coordinator.update_interval:
            return self.coordinator.update_interval.total_seconds() / 3600
        return DEFAULT_MEASUREMENT_INTERVAL

    async def async_set_native_value(self, value: float) -> None:
        """Update the measurement interval."""
        from datetime import timedelta

        _LOGGER.info(f"Setting measurement interval to {value} hours")

        # Convert hours to seconds
        interval_seconds = int(value * 3600)

        if interval_seconds == 0:
            # 0 means no automatic measurement
            _LOGGER.info("Disabling automatic measurements")
            self.coordinator.update_interval = None
        else:
            # Update coordinator's update interval
            _LOGGER.info(f"Setting update interval to {interval_seconds} seconds")
            self.coordinator.update_interval = timedelta(seconds=interval_seconds)

        # Force a refresh of the coordinator to apply the new interval
        await self.coordinator.async_refresh()
