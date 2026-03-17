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

        # Get the device address from entry unique_id (MAC address)
        device_address = entry.unique_id

        # Use custom device name from config entry if available
        device_name = entry.data.get(CONF_DEVICE_NAME)
        if not device_name and blueconnect_go_device:
            # Fallback to default name from device
            device_name = f"{blueconnect_go_device.name} {blueconnect_go_device.identifier}"
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
        hw_version = blueconnect_go_device.hw_version if blueconnect_go_device else None
        sw_version = blueconnect_go_device.sw_version if blueconnect_go_device else None

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

        ble_device = async_ble_device_from_address(self.hass, device_address)
        if not ble_device:
            _LOGGER.error(f"No Bluetooth device found at address {device_address}")
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
