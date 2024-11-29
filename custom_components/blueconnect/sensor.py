"""Support for BlueConnect Go ble sensors."""

from __future__ import annotations

import logging

from .BlueConnectGo import BlueConnectGoDevice

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
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfConductivity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.unit_system import METRIC_SYSTEM

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "EC": SensorEntityDescription(
        key="EC",
        name="Electrical Conductivity",
        native_unit_of_measurement=UnitOfConductivity.MICROSIEMENS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-triangle-outline",
    ),
    "salt": SensorEntityDescription(
        key="salt",
        name="Salt",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker-outline",
    ),
    "ORP": SensorEntityDescription(
        key="ORP",
        name="Oxidation-Reduction Potential",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:alpha-v-circle",
    ),
    "pH": SensorEntityDescription(
        key="pH",
        name="pH",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ph",
    ),
    "battery": SensorEntityDescription(
        key="battery",
        name="Battery",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:pool-thermometer",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go BLE sensors."""
    is_metric = hass.config.units is METRIC_SYSTEM

    coordinator: DataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
        entry.entry_id
    ]
    sensors_mapping = SENSORS_MAPPING_TEMPLATE.copy()
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
                coordinator, coordinator.data, sensors_mapping[sensor_type]
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
    ) -> None:
        """Populate the BlueConnect Go entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        name = f"{blueconnect_go_device.name} {blueconnect_go_device.identifier}"

        self._attr_unique_id = f"{name}_{entity_description.key}"

        self._id = blueconnect_go_device.address
        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    blueconnect_go_device.address,
                )
            },
            name=name,
            manufacturer="Blue Riiot",
            model="Blue Connect Go",
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