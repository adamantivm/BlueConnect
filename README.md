# Blue Connect Go

Home Assistant BLE Integration for the Blueriiot Blue Connect Go Pool Monitor

This integration is heavily based (basiscally started as a copy/paste) on the [Yinmik BLE-YC01 Integration](https://github.com/jdeath/BLE-YC01) by @jdeath.

For discussion, details on the BLE decoding and other integration alternatives, please refer to the
[Blue Connect pool measurements topic](https://community.home-assistant.io/t/blue-connect-pool-measurements/118901)
in the Home Assistant Community forum.

All the BLE decoding details that made this integration possible are full credit of many generous community members
on that thread including @vampcp, @JosePortillo, @rzulian, @A.J.O and others.

# Installation

Install this repo in HACS, then add the Blue Connect Go integration. Restart Home Assistant. The device should be found automatically in a few minutes,
or you can add it manually via Settings > Devices and Services > + Add Integration

# Configuration

## Config Flow Process

When adding the BlueConnect integration, you'll go through the following steps:

1. **Device Discovery**: Home Assistant will automatically discover BlueConnect devices via Bluetooth, or you can manually select from available devices.

2. **Device Confirmation**: Confirm the discovered device you want to add.

3. **Device Type Selection**: Choose your device model:
   - **Blue Connect Go**: Standard pool monitor
   - **Blue Connect Plus**: Advanced pool monitor with additional sensors

4. **Device Naming**: Provide a custom name for your device. This name will be used for all entities associated with the device.

## Device Types and Features

### Blue Connect Go
The standard model provides these sensors:
- **Temperature**: Pool water temperature
- **pH**: Pool pH level
- **ORP (Sanitation)**: Oxidation-reduction potential (measures sanitizer effectiveness)
- **Free Chlorine**: Chlorine concentration in the pool
- **Battery**: Battery percentage
- **Battery Voltage**: Voltage of the device battery

### Blue Connect Plus
The Plus model includes all the sensors from the Go model, plus:
- **Salinity**: Salt concentration in the pool water (PPM)
- **Electrical Conductivity (EC)**: Measures the water's ability to conduct electricity (μS/cm)

**Important**: Selecting the correct device type is crucial because it determines which sensors are available. If you select "Blue Connect Go" for a Plus device, the salinity and EC sensors will not be created.

## Reconfiguring Your Device

You can change your device type and name at any time after the initial setup:

1. Go to **Settings** > **Devices & Services**
2. Find your BlueConnect device
3. Click **Configure**
4. Update the device type or name as needed
5. The integration will automatically reload with the new settings

**Note**: Changing from Go to Plus will add the salinity and EC sensors. Changing from Plus to Go will remove them. The integration will reload automatically to apply changes.
