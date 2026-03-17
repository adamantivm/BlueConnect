from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .BlueConnectGo import BlueConnectGoDevice, BlueConnectGoBluetoothDeviceData
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
        TakeMeasurementImmediately(coordinator, coordinator.data, hass, entry),
    ])


class TakeMeasurementImmediately(
    CoordinatorEntity[DataUpdateCoordinator[BlueConnectGoDevice]], ButtonEntity
):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        blueconnect_go_device: BlueConnectGoDevice,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the BlueConnect Go button."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self.device = blueconnect_go_device

        # Use custom device name from config entry if available
        device_name = entry.data.get(CONF_DEVICE_NAME)
        if not device_name:
            # Fallback to default name
            device_name = f"{blueconnect_go_device.name} {blueconnect_go_device.identifier}"

        self._attr_unique_id = f"{blueconnect_go_device.address}_take_measurement".lower().replace(":", "_").replace(" ", "_")
        self._attr_name = "Take Measurement"
        self._id = blueconnect_go_device.address

        # Get device model from config entry
        device_type = entry.data.get(CONF_DEVICE_TYPE)
        if device_type == DEVICE_TYPE_PLUS:
            model = "Blue Connect Plus"
        else:
            model = "Blue Connect Go"

        self._attr_device_info = DeviceInfo(
            connections={
                (
                    "bluetooth",
                    blueconnect_go_device.address,
                )
            },
            name=device_name,
            manufacturer="Blueriiot",
            model=model,
            hw_version=blueconnect_go_device.hw_version,
            sw_version=blueconnect_go_device.sw_version,
        )

    async def async_press(self) -> None:
        """Trigger a measurement via Bluetooth."""
        _LOGGER.info(f"Button pressed: starting measurement for {self.device.name} ({self.device.address})")

        ble_device = async_ble_device_from_address(self.hass, self.device.address)
        if not ble_device:
            _LOGGER.error(f"No Bluetooth device found at address {self.device.address}")
            raise UpdateFailed("Bluetooth device not found")

        bcgo = BlueConnectGoBluetoothDeviceData(_LOGGER)

        try:
            data = await bcgo.update_device(ble_device)
            _LOGGER.info("Measurement taken successfully.")
            self.coordinator.async_set_updated_data(data)
            _LOGGER.info("Coordinator has been updated.")
        except Exception as err:
            _LOGGER.error(f"Error while reading data: {err}")
            raise UpdateFailed(f"Error while reading data: {err}") from err
