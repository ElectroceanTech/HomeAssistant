# EOT Home Integration for Home Assistant

A Home Assistant custom integration for EOT Home smart devices with optional real-time MQTT updates.

## Features

- ✅ Control lights, switches, fans, covers, and scenes
- ✅ Brightness and color temperature control
- ✅ Fan speed control
- ✅ Cover/curtain position control
- ✅ Scene activation
- ✅ Real-time state updates via MQTT
- ✅ Google Assistant device compatibility
- ✅ Alexa device compatibility

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL
6. Click "Install"
7. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "EOT Home"
4. Enter your credentials:
   - Email
   - Password
5. Click **Submit**

Your devices will be automatically discovered and added to Home Assistant with real-time MQTT updates enabled.

## Supported Devices

| Device Type | Support | Features |
|-------------|---------|----------|
| **Lights** | ✅ | On/Off, Brightness, Color Temperature |
| **Switches** | ✅ | On/Off |
| **Fans** | ✅ | On/Off, Speed Control (0-100%) |
| **Covers/Curtains** | ✅ | Open/Close
| **Scenes** | ✅ | Activate Scene |

## Usage

### Control from Home Assistant

All devices appear in Home Assistant automatically. You can:

- Turn devices on/off
- Adjust brightness (lights)
- Change color temperature (lights)
- Set fan speed (fans)
- Open/close covers (curtains)
- Activate scenes

### Automations

Use your EOT Home devices in Home Assistant automations:

```yaml
automation:
  - alias: "Turn on lights at sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness: 255
```

## Troubleshooting

### Devices Not Showing Up

1. Check your credentials are correct
2. Restart Home Assistant
3. Check logs: **Settings** → **System** → **Logs**

### State Not Updating

States update instantly when devices change externally (via mobile app, voice assistant, or physical controls) through real-time MQTT updates.

## Support

- **Issues**: Report issues on GitHub
- **Questions**: Open a discussion on GitHub

## Technical Details

### API Integration

This integration uses the EOT Home API with Google Assistant protocol:
- **SYNC**: Discovers devices
- **QUERY**: Gets device states
- **EXECUTE**: Controls devices

### MQTT Integration

Automatically connects to AWS IoT Core for real-time updates:
- **Endpoint**: AWS IoT MQTT broker
- **Authentication**: Custom authorizer with token
- **Protocol**: MQTT over TLS with ALPN
- **Real-time Updates**: Instant state synchronization when devices change externally

## Version History

### v1.0.0
- Initial release
- Support for lights, switches, fans, covers, and scenes
- Built-in MQTT support for real-time updates
- Google Assistant and Alexa compatibility

## License

This project is licensed under the MIT License.

## Credits

Developed for the EOT Home ecosystem.

