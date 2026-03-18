<p align="center">
  <img src="logo.png" alt="Tellink Roaming" />
</p>

<h1 align="center">Tellink Prepaid Integration for Home Assistant</h1>

<p align="center">
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-blue.svg" alt="HACS" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming"><img src="https://img.shields.io/badge/version-1.2.4-blue.svg" alt="version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/renaudallard/homeassistant_tellinkroaming" alt="license" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming/issues"><img src="https://img.shields.io/github/issues/renaudallard/homeassistant_tellinkroaming.svg" alt="issues" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming/stargazers"><img src="https://img.shields.io/github/stars/renaudallard/homeassistant_tellinkroaming.svg" alt="stars" /></a>
</p>

<p align="center">
  A custom Home Assistant integration for monitoring your <strong>Tellink prepaid balance, SIM status, username, and validity date</strong> directly from your dashboard.
</p>

---

## Features

- **Balance** sensor (€) with dynamic icon color (red < €2, orange < €4, green otherwise)
- **Username**, **SIM status**, and **Expiry date** sensors
- Multiple accounts support
- Secure credentials stored in private HA storage (auto-migrated from older entries)
- Repairs issue with a **Fix** button for reauthentication
- Configurable update and retry intervals
- Low credit alert automation example
- Web-based configuration UI

---

## Installation

### HACS (Recommended)

1. Go to **HACS > Integrations > Custom Repositories**
2. Add repository (category **Integration**):
   `https://github.com/renaudallard/homeassistant_tellinkroaming`
3. Click **Download** and restart Home Assistant
4. Add the integration via **Settings > Devices & Services > Add Integration > Tellink Prepaid**

### Manual

1. Download the latest release from the [releases page](https://github.com/renaudallard/homeassistant_tellinkroaming/releases)
2. Extract into `<config>/custom_components/tellink/`
3. Restart Home Assistant
4. Add the integration from the UI

---

## Configuration

### Login

When adding the integration:
- Enter your **Tellink username** (usually your phone number)
- Enter your **password**
- Click **Submit**

### Options

You can configure update and retry intervals under:
**Settings > Devices & Services > Tellink > Configure**

| Option            | Default |
|-------------------|---------|
| Update interval   | 3600 s  |
| Retry interval    | 3600 s  |

### Reauthentication

If credentials become invalid, a **Tellink needs reauthentication** issue appears in **Settings > Repairs**.
Click **Fix**, enter the new password, and the integration will validate, store, and reload automatically.

---

## Sensors

| Sensor                     | Description               | Device Class | Example       |
|----------------------------|---------------------------|--------------|---------------|
| `sensor.tellink_balance`   | Current credit amount (€) | Monetary     | `6.75`        |
| `sensor.tellink_status`    | SIM status                | None         | `Active`      |
| `sensor.tellink_username`  | Tellink username           | None         | `9189007815`  |
| `sensor.tellink_expiry`    | Validity expiry date      | Date         | `2037-12-31`  |

---

## Low Credit Alert Example

```yaml
alias: Tellink low credit alert
trigger:
  - platform: numeric_state
    entity_id: sensor.tellink_balance
    below: 2
action:
  - service: notify.mobile_app_yourdevice
    data:
      message: "Your Tellink balance is below 2 EUR!"
mode: single
```

---

## Notes

- Compatible with **Home Assistant 2025.10+**
- Domain: **`tellink`**
- Uses **DataUpdateCoordinator**; sensors do not call the API directly
- Expiry returns a proper `date` (HA 2025+ requirement)
- Brand images (icon and logo) included for HA 2026.3+ UI display
