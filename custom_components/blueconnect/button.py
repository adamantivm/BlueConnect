from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .BlueConnectGo import BlueConnectGoDevice
from .const import CONF_DEVICE_NAME, CONF_DEVICE_TYPE, DEVICE_TYPE_PLUS, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go button."""
    
    coordinator: DataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
        entry.entry_id
    ]

    async_add_entities([
        TakeMeasurementImmediately(coordinator, hass, entry),
    ])


class TakeMeasurementImmediately(
    CoordinatorEntity[DataUpdateCoordinator[BlueConnectGoDevice]], ButtonEntity
):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the BlueConnect Go button."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry

        # Get the device address from entry unique_id (MAC address)
        device_address = entry.unique_id

        # Use custom device name from config entry if available
        device_name = entry.data.get(CONF_DEVICE_NAME)
        if not device_name and coordinator.data:
            # Fallback to default name from device
            device_name = f"{coordinator.data.name} {coordinator.data.identifier}"
        elif not device_name:
            # Final fallback if device is not available
            device_name = f"BlueConnect {device_address}"

        self._attr_unique_id = f"{device_address}_take_measurement".lower().replace(":", "_").replace(" ", "_")
        self._attr_name = "Take Measurement"
        self._id = device_address

        # Get device model from config entry
        device_type = entry.data.get(CONF_DEVICE_TYPE)
        if device_type == DEVICE_TYPE_PLUS:
            model = "Blue Connect Plus"
        else:
            model = "Blue Connect Go"

        # Get hardware and software versions from device if available
        hw_version = coordinator.data.hw_version if coordinator.data else None
        sw_version = coordinator.data.sw_version if coordinator.data else None

        self._attr_device_info = DeviceInfo(
            connections={
                (
                    "bluetooth",
                    device_address,
                )
            },
            name=device_name,
            manufacturer="Blueriiot",
            model=model,
            hw_version=hw_version,
            sw_version=sw_version,
        )

    async def async_press(self) -> None:
        """Trigger a measurement via Bluetooth."""
        # Get the device address from entry unique_id (MAC address)
        device_address = self.entry.unique_id

        _LOGGER.info(f"Button pressed: starting measurement for device at {device_address}")

        # Trigger coordinator refresh which will properly update last_update_success_time
        await self.coordinator.async_request_refresh()
