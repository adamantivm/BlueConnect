# Blue Connect

Home Assistant BLE Integration for the Blueriiot Blue Connect Pool Monitor

This integration is heavily based (basiscally started as a copy/paste) on the [Yinmik BLE-YC01 Integration](https://github.com/jdeath/BLE-YC01) by @jdeath.

For discussion, details on the BLE decoding and other integration alternatives, please refer to the
[Blue Connect pool measurements topic](https://community.home-assistant.io/t/blue-connect-pool-measurements/118901)
in the Home Assistant Community forum.

All the BLE decoding details that made this integration possible are full credit of many generous community members
on that thread including @vampcp, @JosePortillo, @rzulian, @A.J.O and others.

# Installation

Install this repo in HACS, then add the Blue Connect integration. Restart Home Assistant. The device should be found automatically in a few minutes,
or you can add it manually via Settings > Devices and Services > + Add Integration

# Configuration

## Config Flow Process

When adding the BlueConnect integration, you'll go through the following steps:

1. **Device Discovery**: Home Assistant will automatically discover BlueConnect devices via Bluetooth, or you can manually select from available devices.

2. **Device Confirmation**: Confirm the discovered device you want to add.

3. **Device Type Selection**: Choose your device model:
   - **Blue Connect Go**: Standard pool monitor
   - **Blue Connect Plus**: Advanced pool monitor with additional sensors

4. **Fit50 Adapter**: Indicate whether you are using a **Fit50 adapter** with your Blue Connect device.
   - Select **Yes** if your Blue Connect is installed inside a Fit50 inline adapter connected to your pool's circulation system.
   - Select **No** (default) if your Blue Connect is used as a standalone device.
   - See the [Fit50 Feature](#fit50-feature) section below for more details.

5. **Pump Entity Selection** *(only shown when Fit50 is enabled)*: Select the Home Assistant entity (a `switch` or `binary_sensor`) that represents your pool's circulation pump. Measurements will only be taken when this entity is in the **on** state.

6. **Device Naming**: Provide a custom name for your device. This name will be used for all entities associated with the device.

## Device Types and Features

### Blue Connect Go
The standard model provides these sensors:
- **Temperature**: Pool water temperature
- **pH**: Pool pH level
- **ORP (Sanitation)**: Oxidation-reduction potential (measures sanitizer effectiveness)
- **Battery**: Battery percentage
- **Battery Voltage**: Voltage of the device battery

### Blue Connect Plus
The Plus model includes all the sensors from the Go model, plus:
- **Salinity**: Salt concentration in the pool water (g/L)
- **Electrical Conductivity (EC)**: Measures the water's ability to conduct electricity (μS/cm)

**Important**: Selecting the correct device type is crucial because it determines which sensors are available. If you select "Blue Connect Go" for a Plus device, the salinity and EC sensors will not be created.

## Fit50 Feature

The **Fit50** is an inline adapter made by Blue Riiot that allows the Blue Connect sensor to be permanently installed inside the pool's circulation system (plumbing). When using a Fit50, the sensor is always submerged in moving water, which means measurements should only be taken when the circulation pump is actually running — taking a reading with stagnant water would give inaccurate results.

When you enable Fit50 mode during configuration:
- You select the Home Assistant entity (a `switch` or `binary_sensor`) that controls or monitors your circulation pump.
- The integration will **only perform measurements when that pump entity is in the `on` state**.
- This ensures that all readings are taken from actively circulating, representative pool water.

If you are not using a Fit50 adapter and instead float or clip the Blue Connect directly in the pool, you should leave Fit50 mode disabled. In that case, measurements are taken on the normal schedule regardless of any pump state.

## Reconfiguring Your Device

You can change your device type, name, and Fit50 settings at any time after the initial setup:

1. Go to **Settings** > **Devices & Services**
2. Find your BlueConnect device
3. Click **Configure**
4. Update the device type, name, Fit50 mode, or pump entity as needed
5. The integration will automatically reload with the new settings

**Note**: Changing from Go to Plus will add the salinity and EC sensors. Changing from Plus to Go will remove them. Enabling or disabling Fit50 mode will start or stop pump-state-based measurement filtering. The integration will reload automatically to apply all changes.
