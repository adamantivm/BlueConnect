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
    CONCENTRATION_PARTS_PER_MILLION,
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
    DataUpdateCoordinator,
)

from .BlueConnectGo import BlueConnectGoDevice
from .const import CONF_DEVICE_NAME, CONF_DEVICE_TYPE, DEVICE_TYPE_PLUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "EC": SensorEntityDescription(
        key="EC",
        name="Electrical Conductivity",
        native_unit_of_measurement=UnitOfConductivity.MICROSIEMENS_PER_CM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-triangle-outline",
        suggested_display_precision=0,
    ),
    "salt": SensorEntityDescription(
        key="salt",
        name="Salinity",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker-outline",
    ),
    "ORP": SensorEntityDescription(
        key="ORP",
        name="Sanitation (ORP)",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:alpha-v-circle",
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
    "chlorine": SensorEntityDescription(
        key="chlorine",
        name="Free Chlorine",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        icon="mdi:chemical-weapon",
        suggested_display_precision=2,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go BLE sensors."""

    coordinator: DataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
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
                coordinator, coordinator.data, sensors_mapping[sensor_type], entry
            )
        )

    async_add_entities(entities)


class BlueConnectSensor(
    CoordinatorEntity[DataUpdateCoordinator[BlueConnectGoDevice]], SensorEntity
):
    """BlueConnect Go BLE sensors for the device."""

    # _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        blueconnect_go_device: BlueConnectGoDevice,
        entity_description: SensorEntityDescription,
        entry: config_entries.ConfigEntry,
    ) -> None:
        """Populate the BlueConnect Go entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        # Use custom device name from config entry if available
        device_name = entry.data.get(CONF_DEVICE_NAME)
        if not device_name:
            # Fallback to default name
            device_name = f"{blueconnect_go_device.name} {blueconnect_go_device.identifier}"

        self._attr_unique_id = f"{blueconnect_go_device.address}_{entity_description.key}"

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
                    CONNECTION_BLUETOOTH,
                    blueconnect_go_device.address,
                )
            },
            name=device_name,
            manufacturer="Blue Riiot",
            model=model,
            hw_version=blueconnect_go_device.hw_version,
            sw_version=blueconnect_go_device.sw_version,
        )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        try:
            return self.coordinator.data.sensors[self.entity_description.key]
        except KeyError:
            return None
