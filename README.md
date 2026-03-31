# RadiusStack-HA

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for [RadiusStack](https://github.com/deangoldhill/RadiusStack) — a self-hosted FreeRADIUS management stack. Install via HACS as a custom repository.

## Sensors

| Sensor | Source | Description |
|---|---|---|
| Total Users | Overview | Number of RADIUS users |
| MAC Auth Devices | Overview | Registered MAC bypass devices |
| NAS Clients | Overview | Configured NAS clients |
| Usage Plans | Overview | Number of usage plans |
| Active Sessions | Overview | Current active sessions |
| Total Sessions (All Time) | Overview | All-time session count |
| Authentications Today | Overview | Access-Accepts today |
| Auth Rejects Today | Overview | Access-Rejects today |
| Data Used Today | Overview | GB transferred today |
| Data Used This Week | Overview | GB transferred this week |
| Accepts (Last Hour) | Live Stats | Exact accepts in last 60 minutes |
| Rejects (Last Hour) | Live Stats | Exact rejects in last 60 minutes |
| Accepts (Last 24 Hours) | Live Stats | Exact accepts in last 24 hours |
| Rejects (Last 24 Hours) | Live Stats | Exact rejects in last 24 hours |
| Unique Users (Last 24 Hours) | Live Stats | Distinct users seen in last 24 hours |
| Avg Session Duration | Live Stats | Average session length in minutes |
| Active Session Count | Sessions | Count from live sessions endpoint |
| Failed Auth Total | Failed Auth | Total failed authentication records |
| Unique Failed Usernames | Failed Auth | Distinct usernames with failures |
| Healthy Containers | System | Containers in running state |
| Unhealthy Containers | System | Containers not in running state |
| Container [Name] | System | Per-container state (one per container) |

## Buttons

One **Restart [Container]** button is created per discovered `radius_*` container.

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
