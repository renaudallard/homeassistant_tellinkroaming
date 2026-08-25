<p align="center">
  <img src="logo.png" alt="Tellink Roaming" />
</p>

<h1 align="center">Tellink Prepaid Integration for Home Assistant</h1>

<p align="center">
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-blue.svg" alt="HACS" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming"><img src="https://img.shields.io/badge/version-1.4.1-blue.svg" alt="version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/renaudallard/homeassistant_tellinkroaming" alt="license" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming/issues"><img src="https://img.shields.io/github/issues/renaudallard/homeassistant_tellinkroaming.svg" alt="issues" /></a>
  <a href="https://github.com/renaudallard/homeassistant_tellinkroaming/stargazers"><img src="https://img.shields.io/github/stars/renaudallard/homeassistant_tellinkroaming.svg" alt="stars" /></a>
</p>

<p align="center">
  A custom Home Assistant integration for monitoring your <strong>Tellink prepaid balance, SIM status, username, and validity date</strong> directly from your dashboard.
</p>

---

## Features

- **Balance** sensor (€) with low-balance status icons
- **Username**, **SIM status**, and **Expiry date** sensors
- Multiple accounts support
- Passwords kept only in private HA storage, never in the config entry data
- Reauthentication prompt when the portal stops accepting a password
- Configurable update and retry intervals, applied without a restart
- Low credit alert automation example
- Web-based configuration UI

---

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=renaudallard&repository=homeassistant_tellinkroaming&category=integration)

Or manually:

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

| Option            | Default | Range            |
|-------------------|---------|------------------|
| Update interval   | 3600 s  | 60 to 86400 s    |
| Retry interval    | 3600 s  | 60 to 86400 s    |

Changing either value reloads the integration straight away; no restart needed.

### Reauthentication

If the portal stops accepting your credentials, Home Assistant raises its own
**reauthentication** notice for that account, on the integration page and in
**Settings > Repairs**. Opening it asks for the new password, validates it
against the portal, stores it and reloads the integration. Each account is
handled separately, so with several accounts you can tell which one needs
attention.

---

## Sensors

The four sensors are grouped under one device per account, named
**Tellink (your username)**. Each sensor names only itself, so they show up as
**Tellink (9189007815) Balance**, **... Status**, and so on.

| Sensor      | Description               | Device Class | Example       |
|-------------|---------------------------|--------------|---------------|
| Balance     | Current credit amount (€) | None         | `6.75`        |
| Status      | SIM status                | None         | `Active`      |
| Username    | Tellink username          | None         | `9189007815`  |
| Expiry      | Validity expiry date      | Date         | `2037-12-31`  |

### Entity ids

Entity ids are assigned once, when a sensor is first seen, and never change
afterwards. Which ones you have depends on when you installed:

- Upgraded from 1.4.0 or earlier: `sensor.tellink_balance_9189007815` and so
  on, with your username on the end. These are kept as they are.
- Installed fresh from 1.4.1 onward: derived from the device and sensor names,
  so `sensor.tellink_9189007815_balance` and so on.

Check **Settings > Devices & Services > Tellink** for the ids on your own
system before writing automations against them.

### Balance status icons

The balance sensor changes icon with the remaining credit and exposes the same
level as a `balance_state` attribute, so automations can react without parsing
the icon. The attribute is empty while the balance is unknown.

| Balance | Icon | `balance_state` |
|---------|------|-----------------|
| `< 2 EUR` | `mdi:sim-alert` | `critical` |
| `2 - 4 EUR` | `mdi:sim-off` | `warning` |
| `>= 4 EUR` | `mdi:sim` | `normal` |

---

## Low Credit Alert Example

```yaml
alias: Tellink low credit alert
trigger:
  - platform: numeric_state
    entity_id: sensor.tellink_balance_9189007815  # check yours first
    below: 2
action:
  - service: notify.mobile_app_yourdevice
    data:
      message: "Your Tellink balance is below 2 EUR!"
mode: single
```

---

## License

BSD 2-Clause. See [LICENSE](LICENSE).

---

## Notes

- Compatible with **Home Assistant 2025.10+**
- Domain: **`tellink`**
- Uses **DataUpdateCoordinator**; sensors do not call the API directly
- Expiry returns a proper `date` (HA 2025+ requirement)
- Balance is recorded as a measurement, so long term statistics are kept
- Brand images (icon and logo) included for HA 2026.3+ UI display
