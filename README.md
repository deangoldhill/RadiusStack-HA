# RadiusStack-HA

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for [RadiusStack](https://github.com/deangoldhill/RadiusStack) — a self-hosted FreeRADIUS management stack. Install via HACS as a custom repository.

## Sensors

| Sensor | Description |
|---|---|
| Total Users | Number of RADIUS users |
| MAC Auth Devices | Registered MAC bypass devices |
| NAS Clients | Configured NAS clients |
| Usage Plans | Number of usage plans |
| Active Sessions | Current active sessions (overview) |
| Total Sessions (All Time) | All-time session count |
| Authentications Today | Access-Accepts today |
| Auth Rejects Today | Access-Rejects today |
| Data Used Today | GB transferred today |
| Data Used This Week | GB transferred this week |
| Live Active Sessions | Real-time active session count |
| Accepts (Last Hour) | Auth accepts in last 60 minutes |
| Rejects (Last Hour) | Auth rejects in last 60 minutes |
| Accepts (Last 24 Hours) | Auth accepts in last 24 hours |
| Rejects (Last 24 Hours) | Auth rejects in last 24 hours |
| Active Session Count | Count from live sessions endpoint |
| Failed Auth Total | Total failed authentication events |
| Unique Failed Usernames | Distinct usernames with failures |

## Installation

1. In HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/deangoldhill/RadiusStack-HA` as category **Integration**
3. Install **RadiusStack-HA** and restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → RadiusStack-HA**
5. Enter your host, port (default `3000`), API key and poll interval

## Generating an API Key

In the RadiusStack web UI: **Administrators → select admin → Generate API Key**

## Requirements

- Home Assistant 2024.1.0+
- RadiusStack API reachable from the HA host
