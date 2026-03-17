"""Config flow for BlueConnect Go integration."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from bleak import BleakError
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .BlueConnectGo import BlueConnectGoBluetoothDeviceData, BlueConnectGoDevice
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_FIT50_MODE,
    CONF_PUMP_ENTITY,
    DEVICE_TYPE_GO,
    DEVICE_TYPE_PLUS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class Discovery:
    """A discovered bluetooth device."""

    name: str
    discovery_info: BluetoothServiceInfo
    device: BlueConnectGoDevice


def get_name(device: BlueConnectGoDevice) -> str:
    """Generate name with identifier for device."""

    return f"{device.name}"


class BCGoDeviceUpdateError(Exception):
    """Custom error class for device updates."""


class BCGoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blue Connect BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: Discovery | None = None
        self._discovered_devices: dict[str, Discovery] = {}
        self._device_type: str | None = None
        self._device_name: str | None = None
        self._fit50_mode: bool = False
        self._pump_entity: str | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return BCGoOptionsFlow()

    async def _get_device_data(
        self, discovery_info: BluetoothServiceInfo
    ) -> BlueConnectGoDevice:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, discovery_info.address
        )
        _LOGGER.debug("in _get_device_data")
        if ble_device is None:
            _LOGGER.debug("no ble_device in _get_device_data")
            raise BCGoDeviceUpdateError("No ble_device")

        _LOGGER.debug("Getting Device")
        bcgo = BlueConnectGoBluetoothDeviceData(_LOGGER)
        _LOGGER.debug("Got Device Device")
        try:
            _LOGGER.debug("Try Update")
            data = await bcgo.update_device(ble_device, skip_query=True)
            _LOGGER.debug("Got Data")
            # data.name = discovery_info.advertisement.local_name
            data.name = discovery_info.address
            data.address = discovery_info.address
            data.identifier = discovery_info.advertisement.local_name
        except BleakError as err:
            _LOGGER.error(
                "Error connecting to and getting data from %s: %s",
                discovery_info.address,
                err,
            )
            raise BCGoDeviceUpdateError("Failed getting device data") from err
        except Exception as err:
            _LOGGER.error(
                "Unknown error occurred from %s: %s", discovery_info.address, err
            )
            raise
        return data

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered BT device: %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        try:
            device = await self._get_device_data(discovery_info)
        except BCGoDeviceUpdateError:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except  # noqa: BLE001
            return self.async_abort(reason="unknown")

        name = get_name(device)
        self.context["title_placeholders"] = {"name": name}
        self._discovered_device = Discovery(name, discovery_info, device)

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return await self.async_step_device_type()

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device type selection."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_fit50()

        return self.async_show_form(
            step_id="device_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_GO): vol.In(
                        {
                            DEVICE_TYPE_GO: "Blue Connect Go",
                            DEVICE_TYPE_PLUS: "Blue Connect Plus",
                        }
                    ),
                }
            ),
            description_placeholders=self.context.get("title_placeholders", {}),
        )

    async def async_step_fit50(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Fit50 adapter configuration."""
        if user_input is not None:
            self._fit50_mode = user_input.get(CONF_FIT50_MODE, False)
            if self._fit50_mode:
                return await self.async_step_pump_entity()
            else:
                return await self.async_step_device_name()

        return self.async_show_form(
            step_id="fit50",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FIT50_MODE, default=False): bool,
                }
            ),
            description_placeholders=self.context.get("title_placeholders", {}),
        )

    async def async_step_pump_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle circulation pump entity selection."""
        from homeassistant.helpers import selector

        if user_input is not None:
            self._pump_entity = user_input.get(CONF_PUMP_ENTITY)
            return await self.async_step_device_name()

        return self.async_show_form(
            step_id="pump_entity",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PUMP_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["switch", "binary_sensor"]
                        )
                    ),
                }
            ),
            description_placeholders=self.context.get("title_placeholders", {}),
        )

    async def async_step_device_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device naming."""
        if user_input is not None:
            self._device_name = user_input[CONF_DEVICE_NAME]

            # Prepare config data
            config_data = {
                CONF_DEVICE_TYPE: self._device_type,
                CONF_DEVICE_NAME: self._device_name,
                CONF_FIT50_MODE: self._fit50_mode,
            }

            # Add pump entity if Fit50 mode is enabled
            if self._fit50_mode and self._pump_entity:
                config_data[CONF_PUMP_ENTITY] = self._pump_entity

            return self.async_create_entry(
                title=self._device_name,
                data=config_data,
            )

        # Get default name from discovered device
        default_name = self.context.get("title_placeholders", {}).get("name", "")

        return self.async_show_form(
            step_id="device_name",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=default_name): str,
                }
            ),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            discovery = self._discovered_devices[address]

            self.context["title_placeholders"] = {
                "name": discovery.name,
            }

            self._discovered_device = discovery

            return await self.async_step_device_type()

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            ##
            if not address.startswith("00:A0"):
                _LOGGER.info(f"Skipping device: {address}")  # noqa: G004
                continue

            _LOGGER.info(f"Found BlueConnect Go Device: {address}")  # noqa: G004
            _LOGGER.debug("BCGo Discovery address: %s", address)
            _LOGGER.debug("BCGo Man Data: %s", discovery_info.manufacturer_data)
            _LOGGER.debug("BCGo advertisement: %s", discovery_info.advertisement)
            _LOGGER.debug("BCGo device: %s", discovery_info.device)
            _LOGGER.debug("BCGo service data: %s", discovery_info.service_data)
            _LOGGER.debug("BCGo service uuids: %s", discovery_info.service_uuids)
            _LOGGER.debug("BCGo rssi: %s", discovery_info.rssi)
            _LOGGER.debug(
                "BCGo advertisement: %s", discovery_info.advertisement.local_name
            )
            try:
                device = await self._get_device_data(discovery_info)
                _LOGGER.debug("Getting Device Data")
            except BCGoDeviceUpdateError:
                _LOGGER.debug("Cannot Connect")
                return self.async_abort(reason="cannot_connect")
            except Exception:  # pylint: disable=broad-except  # noqa: BLE001
                _LOGGER.debug("Cannot Connect - Unknown")
                return self.async_abort(reason="unknown")
            _LOGGER.debug("Getting Name")
            name = get_name(device)
            self._discovered_devices[address] = Discovery(name, discovery_info, device)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        titles = {
            address: get_name(discovery.device)
            for (address, discovery) in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(titles),
                },
            ),
        )


class BCGoOptionsFlow(OptionsFlow):
    """Handle options flow for BlueConnect integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        from homeassistant.helpers import selector

        if user_input is not None:
            # Prepare updated config data
            config_data = {
                **self.config_entry.data,
                CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                CONF_FIT50_MODE: user_input.get(CONF_FIT50_MODE, False),
            }

            # Add or remove pump entity based on Fit50 mode
            if user_input.get(CONF_FIT50_MODE, False) and user_input.get(CONF_PUMP_ENTITY):
                config_data[CONF_PUMP_ENTITY] = user_input[CONF_PUMP_ENTITY]
            elif CONF_PUMP_ENTITY in config_data:
                # Remove pump entity if Fit50 mode is disabled
                config_data.pop(CONF_PUMP_ENTITY, None)

            # Update config entry data with new values
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=config_data,
            )
            # Trigger reload to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Get current values or defaults
        current_device_type = self.config_entry.data.get(
            CONF_DEVICE_TYPE, DEVICE_TYPE_GO
        )
        current_device_name = self.config_entry.data.get(
            CONF_DEVICE_NAME, self.config_entry.title
        )
        current_fit50_mode = self.config_entry.data.get(CONF_FIT50_MODE, False)
        current_pump_entity = self.config_entry.data.get(CONF_PUMP_ENTITY)

        # Build schema based on Fit50 mode
        schema_dict = {
            vol.Required(
                CONF_DEVICE_TYPE, default=current_device_type
            ): vol.In(
                {
                    DEVICE_TYPE_GO: "Blue Connect Go",
                    DEVICE_TYPE_PLUS: "Blue Connect Plus",
                }
            ),
            vol.Required(CONF_DEVICE_NAME, default=current_device_name): str,
            vol.Required(CONF_FIT50_MODE, default=current_fit50_mode): bool,
        }

        # Add pump entity selector if Fit50 mode is currently enabled or if user wants to enable it
        if current_fit50_mode:
            schema_dict[vol.Optional(CONF_PUMP_ENTITY, default=current_pump_entity)] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["switch", "binary_sensor"]
                )
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
