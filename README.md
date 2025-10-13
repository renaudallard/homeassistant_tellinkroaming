# 🛰️ Tellink Prepaid Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![version](https://img.shields.io/badge/version-1.1.4-blue.svg)](https://github.com/renaudallard/tellinkroaming_ha)
[![license](https://img.shields.io/github/license/renaudallard/tellinkroaming_ha)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/renaudallard/tellinkroaming_ha.svg)](https://github.com/renaudallard/tellinkroaming_ha/issues)
[![GitHub stars](https://img.shields.io/github/stars/renaudallard/tellinkroaming_ha.svg)](https://github.com/renaudallard/tellinkroaming_ha/stargazers)

A **custom Home Assistant integration** for monitoring your **Tellink prepaid balance, SIM status, username, and validity date** directly from your dashboard.  
Supports **multiple accounts**, **secure credential storage**, and **low-credit notifications**.

---

## ✨ Features

- 📊 Sensors for:
  - **Balance (€)**
  - **Username**
  - **SIM status (Active/Inactive)**
  - **Expiry date (with date device class)**
- 🧾 Multiple accounts support
- 🕒 Configurable **update interval** and **retry time**
- ⚠️ Configurable **low credit alert limit**
- 🧰 Simple web-based configuration UI

---

## 🧩 Installation

### Option 1 — HACS (Recommended)

1. Go to **HACS → Integrations → Custom Repositories**
2. Add repository:  
with category **Integration**
3. Click **Download** and restart Home Assistant
4. Add the integration via  
**Settings → Devices & Services → Add Integration → Tellink Prepaid**

### Option 2 — Manual

1. Download the latest release ZIP:  
[📦 tellinkroaming_ha releases](https://github.com/renaudallard/tellinkroaming_ha/releases)
2. Extract it into:
3. Restart Home Assistant
4. Add the integration from the UI

---

## ⚙️ Configuration

### Step 1: Login
When adding the integration:
- Enter your **Tellink username** (usually your phone number)
- Enter your **password**
- Click “Submit” — credentials are **stored securely** (not in plaintext)

### Step 2: Options
You can later configure:
- **Update interval** (default 3600 s)
- **Retry interval** (default 3600 s)
- **Low credit limit** (default 2 €)

Go to:  
**Settings → Devices & Services → Tellink → Configure**

---

## 🧾 Example Sensors

| Sensor Name              | Description                          | Device Class | Example Value  |
|---------------------------|--------------------------------------|---------------|----------------|
| `sensor.tellink_balance`  | Current credit amount (€)            | Monetary      | `6.75`         |
| `sensor.tellink_status`   | SIM status (Active/Inactive)         | None          | `Active`       |
| `sensor.tellink_username` | Tellink username (CLI)               | None          | `9189007815`   |
| `sensor.tellink_expiry`   | Expiry date of validity              | Date          | `2037-12-31`   |

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
