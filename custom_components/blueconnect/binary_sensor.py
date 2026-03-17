"""Support for BlueConnect Go BLE binary sensors."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
)

from .BlueConnectGo import BlueConnectGoDevice
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_FIT50_MODE,
    CONF_PUMP_ENTITY,
    DEVICE_TYPE_PLUS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BlueConnect Go BLE binary sensor entities."""

    coordinator: TimestampDataUpdateCoordinator[BlueConnectGoDevice] = hass.data[DOMAIN][
        entry.entry_id
    ]

    entities: list[BinarySensorEntity] = [
        Fit50ModeBinarySensor(coordinator, entry),
    ]

    # Only add the pump state sensor if Fit50 mode is enabled and a pump entity is configured
    fit50_mode = entry.data.get(CONF_FIT50_MODE, False)
    pump_entity = entry.data.get(CONF_PUMP_ENTITY)
    if fit50_mode and pump_entity:
        entities.append(PumpStateBinarySensor(coordinator, hass, entry))

    async_add_entities(entities)


def _build_device_info(
    coordinator: TimestampDataUpdateCoordinator,
    entry: ConfigEntry,
) -> DeviceInfo:
    """Build DeviceInfo shared by all binary sensor entities."""
    device_address = entry.unique_id

    device_name = entry.data.get(CONF_DEVICE_NAME)
    if not device_name and coordinator.data:
        device_name = f"{coordinator.data.name} {coordinator.data.identifier}"
    elif not device_name:
        device_name = f"BlueConnect {device_address}"

    device_type = entry.data.get(CONF_DEVICE_TYPE)
    model = "Blue Connect Plus" if device_type == DEVICE_TYPE_PLUS else "Blue Connect Go"

    hw_version = coordinator.data.hw_version if coordinator.data else None
    sw_version = coordinator.data.sw_version if coordinator.data else None

    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, device_address)},
        name=device_name,
        manufacturer="Blueriiot",
        model=model,
        hw_version=hw_version,
        sw_version=sw_version,
    )


class Fit50ModeBinarySensor(
    CoordinatorEntity[TimestampDataUpdateCoordinator[BlueConnectGoDevice]], BinarySensorEntity
):
    """Binary sensor indicating whether Fit50 mode is enabled on this device."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:pipe-valve"

    def __init__(
        self,
        coordinator: TimestampDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Fit50 mode binary sensor."""
        super().__init__(coordinator)
        self.entry = entry

        device_address = entry.unique_id
        self._attr_unique_id = f"{device_address}_fit50_mode"
        self._attr_name = "Fit50 Mode"
        self._attr_device_info = _build_device_info(coordinator, entry)

    @property
    def is_on(self) -> bool:
        """Return True if Fit50 mode is enabled."""
        return self.entry.data.get(CONF_FIT50_MODE, False)


class PumpStateBinarySensor(
    CoordinatorEntity[TimestampDataUpdateCoordinator[BlueConnectGoDevice]], BinarySensorEntity
):
    """Binary sensor mirroring the current state of the configured circulation pump."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:pump"

    def __init__(
        self,
        coordinator: TimestampDataUpdateCoordinator,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the pump state binary sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._pump_entity_id: str | None = entry.data.get(CONF_PUMP_ENTITY)

        device_address = entry.unique_id
        self._attr_unique_id = f"{device_address}_pump_state"
        self._attr_name = "Circulation Pump"
        self._attr_device_info = _build_device_info(coordinator, entry)

    async def async_added_to_hass(self) -> None:
        """Subscribe to pump entity state changes for real-time updates."""
        await super().async_added_to_hass()
        if self._pump_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    self._pump_entity_id,
                    self._handle_pump_state_change,
                )
            )

    @callback
    def _handle_pump_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle pump entity state changes and push an updated state to HA."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True if the pump is running, False if off, None if unavailable."""
        if not self._pump_entity_id:
            return None
        pump_state = self.hass.states.get(self._pump_entity_id)
        if pump_state is None:
            return None
        return pump_state.state == STATE_ON
