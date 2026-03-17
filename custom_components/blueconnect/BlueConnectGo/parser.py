"""Parser for BlueConnect Go BLE devices."""

from __future__ import annotations

import asyncio
from asyncio import Event
import dataclasses
from functools import partial
import logging
from logging import Logger

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from .const import BUTTON_CHAR_UUID, NOTIFY_CHAR_UUID, NOTIFY_TIMEOUT

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class BlueConnectGoDevice:
    """Response data with information about the Blue Connect Go device."""

    hw_version: str = ""
    sw_version: str = ""
    name: str = ""
    identifier: str = ""
    address: str = ""
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=lambda: {}
    )


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
class BlueConnectGoBluetoothDeviceData:
    """Data for Blue Connect Go BLE sensors."""

    _event: asyncio.Event | None
    _command_data: bytearray | None

    def __init__(
        self,
        logger: Logger,
    ) -> None:
        """Initialize the class."""
        super().__init__()
        self.logger = logger
        self.logger.debug("In Device Data")

    async def _get_status(
        self, client: BleakClient, device: BlueConnectGoDevice
    ) -> BlueConnectGoDevice:
        _LOGGER.debug("Getting Status")

        data_ready_event = Event()

        await client.start_notify(
            NOTIFY_CHAR_UUID, partial(self._receive_status, device, data_ready_event)
        )
        await client.write_gatt_char(BUTTON_CHAR_UUID, b"\x01", response=True)
        _LOGGER.debug("Write sent")

        try:
            await asyncio.wait_for(data_ready_event.wait(), timeout=NOTIFY_TIMEOUT)
        except TimeoutError:
            _LOGGER.warning("Timer expired")

        _LOGGER.debug("Status acquisition finished")
        return device

    async def _receive_status(
        self,
        device: BlueConnectGoDevice,
        data_ready_event: Event,
        char_specifier: str,
        data: bytearray,
    ) -> None:
        _LOGGER.debug("Got new data")
        data_ready_event.set()

        _LOGGER.debug(
            f"  -> frame array hex: {":".join([f"{byte:02X}" for byte in data])}"  # noqa: G004
        )

        # TODO: All these readings need to be reviewed and improved

        raw_temp = int.from_bytes(data[1:3], byteorder="little")
        device.sensors["temperature"] = raw_temp / 100.0

        raw_ph = int.from_bytes(data[3:5], byteorder="little")
        device.sensors["pH"] = (2048 - raw_ph) / 232.0 + 7.0

        raw_orp = int.from_bytes(data[5:7], byteorder="little")
        # device.sensors["ORP"] = raw_orp / 3.86 - 21.57826
        device.sensors["ORP"] = raw_orp / 4.0 - 5.0

        raw_cond = int.from_bytes(data[7:9], byteorder="little")
        if raw_cond != 0:
            device.sensors["EC"] = 1.0 / (raw_cond * 0.000001) * 1.0615
            device.sensors["salt"] = 1.0 / (raw_cond * 0.001) * 1.0615 * 500.0 / 1000.0
        else:
            device.sensors["EC"] = None
            device.sensors["salt"] = None

        raw_batt = int.from_bytes(data[9:11], byteorder="little")  # raw value in mV
        device.sensors["battery_voltage"] = raw_batt / 1000.0
        BATT_MAX_MV = 3640
        BATT_MIN_MV = 3400
        batt_percent = (raw_batt - BATT_MIN_MV) / (BATT_MAX_MV - BATT_MIN_MV) * 100.0
        device.sensors["battery"] = max(0, min(batt_percent * 100, 100))

        _LOGGER.debug("Got Status")
        return device

    async def update_device(
        self, ble_device: BLEDevice, skip_query=False
    ) -> BlueConnectGoDevice:
        """Connect to the device through BLE and retrieves relevant data."""
        _LOGGER.debug("Update Device")

        device = BlueConnectGoDevice()
        device.name = ble_device.address
        device.address = ble_device.address
        _LOGGER.debug("device.name: %s", device.name)
        _LOGGER.debug("device.address: %s", device.address)

        if not skip_query:
            client = await establish_connection(
                BleakClient, ble_device, ble_device.address
            )
            _LOGGER.debug("Got Client")
            await self._get_status(client, device)
            _LOGGER.debug("got Status")
            await client.disconnect()

        return device
