202510231200
# 🛰️ Tellink Prepaid Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![version](https://img.shields.io/badge/version-1.2.1-blue.svg)](https://github.com/renaudallard/homeassistant_tellinkroaming)
[![license](https://img.shields.io/github/license/renaudallard/homeassistant_tellinkroaming)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/renaudallard/homeassistant_tellinkroaming.svg)](https://github.com/renaudallard/homeassistant_tellinkroaming/issues)
[![GitHub stars](https://img.shields.io/github/stars/renaudallard/homeassistant_tellinkroaming.svg)](https://github.com/renaudallard/homeassistant_tellinkroaming/stargazers)

A **custom Home Assistant integration** for monitoring your **Tellink prepaid balance, SIM status, username, and validity date** directly from your dashboard.  
Supports **multiple accounts**, **sensors via a DataUpdateCoordinator**, and **low-credit notifications**.

---

## ✨ Features

- 📊 Sensors for:
  - **Balance (€)** with dynamic **icon color** *(red < €2, orange < €4, green otherwise)*
  - **Username**
  - **SIM status (Active/Inactive)**
  - **Expiry date** (native `date` device class)
- 🧾 Multiple accounts support
- 🕒 Configurable **update interval** and **retry time**
- ⚠️ Low credit alert examples
- 🧰 Web-based configuration UI

---

## 🧩 Installation

### Option 1 — HACS (Recommended)

1. Go to **HACS → Integrations → Custom Repositories**
2. Add repository (category **Integration**):  
   `https://github.com/renaudallard/homeassistant_tellinkroaming`
3. Click **Download** and restart Home Assistant
4. Add the integration via  
   **Settings → Devices & Services → Add Integration → Tellink Prepaid**

### Option 2 — Manual

1. Download the latest release ZIP:  
   `https://github.com/renaudallard/homeassistant_tellinkroaming/releases`
2. Extract it into your HA config folder at:  
   `<config>/custom_components/tellink/`
3. Restart Home Assistant
4. Add the integration from the UI

---

## ⚙️ Configuration

### Step 1: Login
When adding the integration:
- Enter your **Tellink username** (usually your phone number)
- Enter your **password**
- Click **Submit** — password is marked **sensitive** in the UI

### Step 2: Options
You can later configure:
- **Update interval** (default 3600 s)
- **Retry interval** (default 3600 s)

Go to:  
**Settings → Devices & Services → Tellink → Configure**

---

## 🧾 Example Sensors

| Sensor Name              | Description                          | Device Class | Example Value |
|-------------------------|--------------------------------------|--------------|---------------|
| `sensor.tellink_balance`  | Current credit amount (€)            | Monetary     | `6.75`        |
| `sensor.tellink_status`   | SIM status (Active/Inactive)         | None         | `Active`      |
| `sensor.tellink_username` | Tellink username (CLI)               | None         | `9189007815`  |
| `sensor.tellink_expiry`   | Expiry date of validity              | Date         | `2037-12-31`  |

---

## ⚠️ Low Credit Alerts

You can use an automation such as:

```yaml
alias: Tellink low credit alert
trigger:
  - platform: numeric_state
    entity_id: sensor.tellink_balance
    below: 2
action:
  - service: notify.mobile_app_yourdevice
    data:
      message: "Your Tellink balance is below 2 €!"
mode: single
