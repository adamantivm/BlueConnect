"""Constants for BlueConnect Go BLE parser."""

# How long to wait for a response from the BlueConnect Go device, in seconds
NOTIFY_TIMEOUT = 15

# BLE characteristic to request sensor reading
BUTTON_CHAR_UUID = "F3300002-F0A2-9B06-0C59-1BC4763B5C00"
# BLE characteristic to wait for sensor readings on
NOTIFY_CHAR_UUID = "F3300003-F0A2-9B06-0C59-1BC4763B5C00"

# Standard BLE Device Information Service (DIS) characteristics
# https://www.bluetooth.com/specifications/specs/device-information-service-1-1/
DIS_MANUFACTURER_NAME_UUID = "00002A29-0000-1000-8000-00805f9b34fb"
DIS_MODEL_NUMBER_UUID = "00002A24-0000-1000-8000-00805f9b34fb"
DIS_SERIAL_NUMBER_UUID = "00002A25-0000-1000-8000-00805f9b34fb"
DIS_HARDWARE_REVISION_UUID = "00002A27-0000-1000-8000-00805f9b34fb"
DIS_FIRMWARE_REVISION_UUID = "00002A26-0000-1000-8000-00805f9b34fb"
DIS_SOFTWARE_REVISION_UUID = "00002A28-0000-1000-8000-00805f9b34fb"
