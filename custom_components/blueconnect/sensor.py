"""Support for BlueConnect Go ble sensors."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfConductivity,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
)
from datetime import datetime
import homeassistant.util.dt as dt_util

from .BlueConnectGo import BlueConnectGoDevice
from .const import CONF_DEVICE_NAME, CONF_DEVICE_TYPE, DEVICE_TYPE_PLUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "EC": SensorEntityDescription(
        key="EC",
        name="Conductivity",
        native_unit_of_measurement=UnitOfConductivity.MICROSIEMENS_PER_CM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:resistor",
        suggested_display_precision=0,
    ),
    "salt": SensorEntityDescription(
        key="salt",
        name="Salinity",
        native_unit_of_measurement="g/L",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-opacity",
        suggested_display_precision=3,
    ),
    "ORP": SensorEntityDescription(
        key="ORP",
        name="Sanitation (ORP)",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:bacteria-outline",
        suggested_display_precision=0,
    ),
    "pH": SensorEntityDescription(
        key="pH",
        name="pH",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ph",
        suggested_display_precision=1,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        name="Battery",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "battery_voltage": SensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:battery",
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:pool-thermometer",
        suggested_display_precision=2,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go BLE sensors."""

    coordinator: TimestampDataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
        entry.entry_id
    ]
    sensors_mapping = SENSORS_MAPPING_TEMPLATE.copy()

    # Get device type from config entry
    device_type = entry.data.get(CONF_DEVICE_TYPE)

    # Remove salinity and conductivity sensors if device is not Plus
    if device_type != DEVICE_TYPE_PLUS:
        sensors_mapping.pop("EC", None)
        sensors_mapping.pop("salt", None)

    entities = []

    # Only iterate over sensors if coordinator.data is available
    if coordinator.data and coordinator.data.sensors:
        _LOGGER.debug("got sensors: %s", coordinator.data.sensors)
        for sensor_type, sensor_value in coordinator.data.sensors.items():
            if sensor_type not in sensors_mapping:
                _LOGGER.debug(
                    "Unknown sensor type detected: %s, %s",
                    sensor_type,
                    sensor_value,
                )
                continue
            entities.append(
                BlueConnectSensor(
                    coordinator, sensors_mapping[sensor_type], entry
                )
            )
    else:
        # If no data yet, create sensors based on sensors_mapping
        _LOGGER.debug("No data available yet, creating sensors from mapping")
        for sensor_type, sensor_description in sensors_mapping.items():
            entities.append(
                BlueConnectSensor(
                    coordinator, sensor_description, entry
                )
            )

    # Add last successful measurement timestamp sensor
    entities.append(
        LastMeasurementTimestampSensor(coordinator, entry)
    )

    async_add_entities(entities)


class BlueConnectSensor(
    CoordinatorEntity[TimestampDataUpdateCoordinator[BlueConnectGoDevice]], SensorEntity
):
    """BlueConnect Go BLE sensors for the device."""

    # _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TimestampDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        entry: config_entries.ConfigEntry,
    ) -> None:
        """Populate the BlueConnect Go entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description

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

        self._attr_unique_id = f"{device_address}_{entity_description.key}"

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
                    CONNECTION_BLUETOOTH,
                    device_address,
                )
            },
            name=device_name,
            manufacturer="Blueriiot",
            model=model,
            hw_version=hw_version,
            sw_version=sw_version,
        )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        try:
            return self.coordinator.data.sensors[self.entity_description.key]
        except KeyError:
            return None


class LastMeasurementTimestampSensor(
    CoordinatorEntity[TimestampDataUpdateCoordinator[BlueConnectGoDevice]], SensorEntity
):
    """Sensor that shows the last successful measurement timestamp."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(
        self,
        coordinator: TimestampDataUpdateCoordinator,
        entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize the last measurement timestamp sensor."""
        super().__init__(coordinator)

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

        self._attr_unique_id = f"{device_address}_last_measurement"
        self._attr_name = "Last Successful Measurement"

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
                    CONNECTION_BLUETOOTH,
                    device_address,
                )
            },
            name=device_name,
            manufacturer="Blueriiot",
            model=model,
            hw_version=hw_version,
            sw_version=sw_version,
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last successful update."""
        if self.coordinator.last_update_success and self.coordinator.last_update_success_time:
            return self.coordinator.last_update_success_time
        return None
