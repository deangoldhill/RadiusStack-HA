"""Rich read-only sensors for RadiusStack."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_ACTIVE_SESSIONS, DATA_DEPLETED, DATA_DOWNSTREAM, DATA_DOWNSTREAM_STATS, DATA_FAILED_AUTH, DATA_LIVE, DATA_NAS, DATA_NAS_STATS, DATA_OVERVIEW, DATA_SYSTEM_STATUS, DATA_USERS, DOMAIN
from .coordinator import RadiusStackCoordinator
from .metrics import count_disabled_users, depleted_summary, downstream_totals, nas_totals


def _dig(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if not isinstance(data, dict): return default
        data = data.get(key, default)
        if data is None: return default
    return data


def _bytes_to_gb(value: Any) -> float | None:
    try: return round(float(value) / 1_073_741_824, 3)
    except (TypeError, ValueError): return None


def _system_containers(data: dict[str, Any]) -> list[dict[str, Any]]:
    status = data.get(DATA_SYSTEM_STATUS, {})
    if isinstance(status, list): return status
    return status.get("containers", []) if isinstance(status, dict) else []


def _system_health(data: dict[str, Any]) -> int:
    containers = _system_containers(data)
    return sum(str(item.get("state", item.get("status", ""))).lower() in ("running", "healthy", "up") for item in containers)


@dataclass(frozen=True, kw_only=True)
class RadiusStackSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _overview_count(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: _dig(data, DATA_OVERVIEW, "counts", key)


SENSOR_DESCRIPTIONS: list[RadiusStackSensorDescription] = [
    RadiusStackSensorDescription(key="total_users", name="Total Users", icon="mdi:account-multiple", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("users")),
    RadiusStackSensorDescription(key="disabled_users", name="Disabled Users", icon="mdi:account-cancel", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: count_disabled_users(d.get(DATA_USERS, []))),
    RadiusStackSensorDescription(key="mac_auth_devices", name="MAC Auth Devices", icon="mdi:lan", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("macs")),
    RadiusStackSensorDescription(key="nas_clients", name="NAS Clients", icon="mdi:router-network", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("nas")),
    RadiusStackSensorDescription(key="radsec_nas", name="RadSec NAS Clients", icon="mdi:lock-check", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: sum(bool(item.get("radsec_enabled")) for item in d.get(DATA_NAS, []))),
    RadiusStackSensorDescription(key="routed_nas", name="Downstream Routed NAS", icon="mdi:transit-connection-variant", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: sum(item.get("downstream_destination_id") is not None for item in d.get(DATA_NAS, []))),
    RadiusStackSensorDescription(key="usage_plans", name="Usage Plans", icon="mdi:card-account-details", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("plans")),
    RadiusStackSensorDescription(key="active_sessions", name="Active Sessions", icon="mdi:wifi-check", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("activeSessions")),
    RadiusStackSensorDescription(key="total_sessions", name="Total Sessions", icon="mdi:history", state_class=SensorStateClass.TOTAL_INCREASING, value_fn=_overview_count("totalSessions")),
    RadiusStackSensorDescription(key="auth_today", name="Authentications Today", icon="mdi:shield-check", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("authToday")),
    RadiusStackSensorDescription(key="rejects_today", name="Auth Rejects Today", icon="mdi:shield-off", state_class=SensorStateClass.MEASUREMENT, value_fn=_overview_count("rejectToday")),
    RadiusStackSensorDescription(key="data_today", name="Data Used Today", icon="mdi:database-arrow-up", native_unit_of_measurement=UnitOfInformation.GIGABYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _bytes_to_gb(_dig(d, DATA_OVERVIEW, "data", "today"))),
    RadiusStackSensorDescription(key="data_week", name="Data Used This Week", icon="mdi:database-clock", native_unit_of_measurement=UnitOfInformation.GIGABYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _bytes_to_gb(_dig(d, DATA_OVERVIEW, "data", "week"))),
    RadiusStackSensorDescription(key="accepts_1h", name="Accepts Last Hour", icon="mdi:check-circle", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "accepts_1h")),
    RadiusStackSensorDescription(key="rejects_1h", name="Rejects Last Hour", icon="mdi:close-circle", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "rejects_1h")),
    RadiusStackSensorDescription(key="accepts_24h", name="Accepts Last 24 Hours", icon="mdi:check-circle-outline", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "accepts_24h")),
    RadiusStackSensorDescription(key="rejects_24h", name="Rejects Last 24 Hours", icon="mdi:close-circle-outline", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "rejects_24h")),
    RadiusStackSensorDescription(key="unique_users_24h", name="Unique Users Last 24 Hours", icon="mdi:account-multiple-check", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "unique_users_24h")),
    RadiusStackSensorDescription(key="average_session_minutes", name="Average Session Duration", icon="mdi:timer-outline", native_unit_of_measurement="min", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _dig(d, DATA_LIVE, "avg_session_min")),
    RadiusStackSensorDescription(key="active_session_records", name="Active Session Records", icon="mdi:counter", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: len(d.get(DATA_ACTIVE_SESSIONS, []))),
    RadiusStackSensorDescription(key="failed_auth", name="Failed Auth Records", icon="mdi:account-alert", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: len(_dig(d, DATA_FAILED_AUTH, "details") or [])),
    RadiusStackSensorDescription(key="failed_usernames", name="Unique Failed Usernames", icon="mdi:account-question", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: len(_dig(d, DATA_FAILED_AUTH, "summary") or [])),
    RadiusStackSensorDescription(key="depleted_allocations", name="Depleted Allocations", icon="mdi:account-alert-outline", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: depleted_summary(d.get(DATA_DEPLETED, {}))["total"], attributes_fn=lambda d: depleted_summary(d.get(DATA_DEPLETED, {}))),
    RadiusStackSensorDescription(key="depleted_users", name="Users Depleted by Plan", icon="mdi:account-off", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: depleted_summary(d.get(DATA_DEPLETED, {}))["users"]),
    RadiusStackSensorDescription(key="depleted_macs", name="MAC Devices Depleted by Plan", icon="mdi:lan-disconnect", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: depleted_summary(d.get(DATA_DEPLETED, {}))["mac_devices"]),
    RadiusStackSensorDescription(key="downstream_destinations", name="Downstream Destinations", icon="mdi:source-branch", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: len(d.get(DATA_DOWNSTREAM, []))),
    RadiusStackSensorDescription(key="downstream_requests", name="Downstream Requests Today", icon="mdi:swap-horizontal", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: downstream_totals(d.get(DATA_DOWNSTREAM_STATS, {}))["requests"], attributes_fn=lambda d: downstream_totals(d.get(DATA_DOWNSTREAM_STATS, {}))),
    RadiusStackSensorDescription(key="nas_auth", name="NAS Authentications Today", icon="mdi:router-wireless", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: nas_totals(d.get(DATA_NAS_STATS, {}))["auth"], attributes_fn=lambda d: nas_totals(d.get(DATA_NAS_STATS, {}))),
    RadiusStackSensorDescription(key="nas_active_sessions", name="NAS Active Sessions", icon="mdi:wifi", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: nas_totals(d.get(DATA_NAS_STATS, {}))["active"]),
    RadiusStackSensorDescription(key="healthy_containers", name="Healthy Containers", icon="mdi:server-network", state_class=SensorStateClass.MEASUREMENT, value_fn=_system_health),
    RadiusStackSensorDescription(key="unhealthy_containers", name="Unhealthy Containers", icon="mdi:server-network-off", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: len(_system_containers(d)) - _system_health(d)),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: RadiusStackCoordinator = hass.data[DOMAIN][entry.entry_id]
    host, port = entry.data[CONF_HOST], entry.data[CONF_PORT]
    entities: list[SensorEntity] = [RadiusStackSensor(coordinator, desc, host, port, entry.entry_id) for desc in SENSOR_DESCRIPTIONS]
    for nas in coordinator.data.get(DATA_NAS, []):
        if nas.get("id") is not None: entities.append(RadiusStackStatsSensor(coordinator, host, port, entry.entry_id, "nas", nas))
    for destination in coordinator.data.get(DATA_DOWNSTREAM, []):
        if destination.get("id") is not None: entities.append(RadiusStackStatsSensor(coordinator, host, port, entry.entry_id, "downstream", destination))
    async_add_entities(entities)


class _RadiusStackEntity(CoordinatorEntity[RadiusStackCoordinator]):
    _attr_has_entity_name = True
    def __init__(self, coordinator: RadiusStackCoordinator, host: str, port: int, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)}, name="RadiusStack", manufacturer="RadiusStack", model="FreeRADIUS management stack", configuration_url=f"http://{host}:{port}")


class RadiusStackSensor(_RadiusStackEntity, SensorEntity):
    entity_description: RadiusStackSensorDescription
    def __init__(self, coordinator: RadiusStackCoordinator, description: RadiusStackSensorDescription, host: str, port: int, entry_id: str) -> None:
        super().__init__(coordinator, host, port, entry_id); self.entity_description = description; self._attr_unique_id = f"radiusstack_{entry_id}_{description.key}"
    @property
    def native_value(self) -> Any: return self.entity_description.value_fn(self.coordinator.data) if self.coordinator.data else None
    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return self.entity_description.attributes_fn(self.coordinator.data) if self.coordinator.data and self.entity_description.attributes_fn else None


class RadiusStackStatsSensor(_RadiusStackEntity, SensorEntity):
    """One detailed sensor per discovered NAS or downstream destination."""
    def __init__(self, coordinator: RadiusStackCoordinator, host: str, port: int, entry_id: str, kind: str, item: dict[str, Any]) -> None:
        super().__init__(coordinator, host, port, entry_id); self._kind, self._id = kind, str(item["id"])
        self._attr_name = f"{'NAS' if kind == 'nas' else 'Downstream'} {item.get('shortname') or item.get('name') or item.get('nasname') or self._id} Requests Today"
        self._attr_unique_id = f"radiusstack_{entry_id}_{kind}_{self._id}_requests"
        self._attr_icon = "mdi:router-network" if kind == "nas" else "mdi:transit-connection-variant"
        self._attr_state_class = SensorStateClass.MEASUREMENT
    def _stats(self) -> dict[str, Any]:
        key = DATA_NAS_STATS if self._kind == "nas" else DATA_DOWNSTREAM_STATS
        return self.coordinator.data.get(key, {}).get(self._id, {}) if self.coordinator.data else {}
    @property
    def native_value(self) -> Any:
        totals = self._stats().get("totals", {})
        return sum(int(totals.get(key, 0) or 0) for key in (("auth", "accounting") if self._kind == "downstream" else ("auth",)))
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = self._stats(); return {key: value for key, value in stats.items() if key not in ("series",)}
