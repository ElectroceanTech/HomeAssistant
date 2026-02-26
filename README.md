# EOT Home Integration for Home Assistant

> **Version 2.0.0** — Add your EOT Home smart devices to Home Assistant with real-time MQTT updates and full voice assistant compatibility.

---

## 🏠 Add to Home Assistant

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eot_home)

Click the button above to directly add **EOT Home** to Home Assistant.

---

## 🚀 Installation (HACS)

### Install via HACS (Official Method)

1. Open **HACS**
2. Go to **Integrations**
3. Click **Explore & Download Repositories**
4. Search for **EOT Home**
5. Click **Download**
6. Restart Home Assistant
7. Go to **Settings → Devices & Services**
8. Click **Add Integration**
9. Search for **EOT Home**
10. Enter your credentials

---

## ✨ Features

- ✅ Control lights, switches, fans, covers, and scenes
- ✅ Brightness and color temperature control
- ✅ Fan speed control (0–100%)
- ✅ Cover/curtain position control
- ✅ Scene activation
- ✅ Real-time state updates via MQTT
- ✅ Google Assistant compatibility
- ✅ Alexa compatibility

---

## 🔌 Supported Devices

| Device Type     | Support | Features                                    |
|-----------------|---------|---------------------------------------------|
| Lights          | ✅       | On/Off, Brightness, Color Temperature       |
| Switches        | ✅       | On/Off                                      |
| Fans            | ✅       | On/Off, Speed Control (0–100%)              |
| Covers/Curtains | ✅       | Open / Close                                |
| Scenes          | ✅       | Activate Scene                              |

---

## ⚙️ Configuration

After installation:

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **EOT Home**
4. Enter:
   - Email
   - Password
5. Click **Submit**

Your devices will be automatically discovered and added.

---

## 🔄 Real-Time MQTT Updates

State updates happen instantly when devices change via:

- EOT Mobile App
- Google Assistant
- Alexa
- Touch Switches

Powered by **AWS IoT Core** secure MQTT connection.

---

## 🤖 Automations Example

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

---

## 📋 Changelog

### Version 2.0.0
- 🆕 Full MQTT real-time state synchronisation via AWS IoT Core
- 🆕 Cover/curtain position control support
- 🆕 Scene activation support
- 🆕 Fan speed control (0–100%)
- 🆕 Google Assistant & Alexa compatibility
- ⚡ Improved device discovery and credential flow
- 🐛 Various stability and reliability fixes

---

## 📄 License

This project is licensed under the MIT License.