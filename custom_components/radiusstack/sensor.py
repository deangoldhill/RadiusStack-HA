"""Sensor platform for RadiusStack-HA."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_ACTIVE_SESSIONS,
    DATA_CONTAINERS,
    DATA_FAILED_AUTH,
    DATA_OVERVIEW,
    DOMAIN,
)
from .coordinator import RadiusStackCoordinator


def _dig(data: dict, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
        if data is None:
            return default
    return data


def _bytes_to_gb(b) -> float | None:
    try:
        return round(float(b) / 1_073_741_824, 3)
    except (TypeError, ValueError):
        return None


def _auth_trend_sum(d, field: str, hours: int) -> int | None:
    """
    Sum accepts or rejects from authTrend7d for the last N hours.
    authTrend7d is daily buckets — for 24h we use today's bucket,
    for 1h we use today's bucket divided by 24 as a best approximation
    since the API only provides daily granularity.
    """
    trend = _dig(d, DATA_OVERVIEW, "authTrend7d")
    if not trend or not isinstance(trend, list):
        return None
    # Last entry is today
    today = trend[-1] if trend else {}
    try:
        daily_val = int(today.get(field, 0) or 0)
    except (TypeError, ValueError):
        return None
    if hours >= 24:
        return daily_val
    # Approximate last hour as today_total / 24
    return round(daily_val / 24)


@dataclass(frozen=True, kw_only=True)
class RadiusStackSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any]


SENSOR_DESCRIPTIONS: list[RadiusStackSensorDescription] = [

    # ── Overview counts ──────────────────────────────────────────────────
    RadiusStackSensorDescription(
        key="total_users",
        name="Total Users",
        icon="mdi:account-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "users"),
    ),
    RadiusStackSensorDescription(
        key="total_mac_devices",
        name="MAC Auth Devices",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "macs"),
    ),
    RadiusStackSensorDescription(
        key="total_nas_clients",
        name="NAS Clients",
        icon="mdi:router-network",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "nas"),
    ),
    RadiusStackSensorDescription(
        key="total_plans",
        name="Usage Plans",
        icon="mdi:card-account-details",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "plans"),
    ),
    RadiusStackSensorDescription(
        key="active_sessions",
        name="Active Sessions",
        icon="mdi:wifi-check",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "activeSessions"),
    ),
    RadiusStackSensorDescription(
        key="total_sessions",
        name="Total Sessions (All Time)",
        icon="mdi:history",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "totalSessions"),
    ),
    RadiusStackSensorDescription(
        key="auth_today",
        name="Authentications Today",
        icon="mdi:shield-check",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "authToday"),
    ),
    RadiusStackSensorDescription(
        key="rejects_today",
        name="Auth Rejects Today",
        icon="mdi:shield-off",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, DATA_OVERVIEW, "counts", "rejectToday"),
    ),

    # ── Data throughput ──────────────────────────────────────────────────
    RadiusStackSensorDescription(
        key="data_today_gb",
        name="Data Used Today",
        icon="mdi:database-arrow-up",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _bytes_to_gb(_dig(d, DATA_OVERVIEW, "data", "today")),
    ),
    RadiusStackSensorDescription(
        key="data_week_gb",
        name="Data Used This Week",
        icon="mdi:database-clock",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _bytes_to_gb(_dig(d, DATA_OVERVIEW, "data", "week")),
    ),

    # ── Auth trend (derived from authTrend7d daily buckets) ──────────────
    RadiusStackSensorDescription(
        key="accepts_last_24h",
        name="Accepts (Last 24 Hours)",
        icon="mdi:check-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _auth_trend_sum(d, "accepts", 24),
    ),
    RadiusStackSensorDescription(
        key="rejects_last_24h",
        name="Rejects (Last 24 Hours)",
        icon="mdi:close-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _auth_trend_sum(d, "rejects", 24),
    ),
    RadiusStackSensorDescription(
        key="accepts_last_1h",
        name="Accepts (Last Hour, est.)",
        icon="mdi:check-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _auth_trend_sum(d, "accepts", 1),
    ),
    RadiusStackSensorDescription(
        key="rejects_last_1h",
        name="Rejects (Last Hour, est.)",
        icon="mdi:close-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _auth_trend_sum(d, "rejects", 1),
    ),

    # ── Active session count ─────────────────────────────────────────────
    RadiusStackSensorDescription(
        key="active_session_count",
        name="Active Session Count",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(d.get(DATA_ACTIVE_SESSIONS, [])),
    ),

    # ── Failed auth ──────────────────────────────────────────────────────
    # failed-auth returns { details: [...], summary: [...] }
    RadiusStackSensorDescription(
        key="failed_auth_total",
        name="Failed Auth Total",
        icon="mdi:account-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(
            _dig(d, DATA_FAILED_AUTH, "details") or []
        ),
    ),
    RadiusStackSensorDescription(
        key="unique_failed_usernames",
        name="Unique Failed Usernames",
        icon="mdi:account-question",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(
            _dig(d, DATA_FAILED_AUTH, "summary") or []
        ),
    ),

    # ── Container health ─────────────────────────────────────────────────
    RadiusStackSensorDescription(
        key="containers_healthy",
        name="Healthy Containers",
        icon="mdi:server-network",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: sum(
            1 for c in (d.get(DATA_CONTAINERS) or [])
            if c.get("state") == "running"
        ),
    ),
    RadiusStackSensorDescription(
        key="containers_unhealthy",
        name="Unhealthy Containers",
        icon="mdi:server-network-off",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: sum(
            1 for c in (d.get(DATA_CONTAINERS) or [])
            if c.get("state") != "running"
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RadiusStackCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    entities: list = [
        RadiusStackSensor(coordinator, description, host, port)
        for description in SENSOR_DESCRIPTIONS
    ]

    # Dynamically create one binary sensor + one container state sensor
    # per discovered container (populated after first coordinator refresh)
    containers = coordinator.data.get(DATA_CONTAINERS, []) if coordinator.data else []
    for container in containers:
        name = container.get("name", "")
        if name:
            entities.append(
                RadiusStackContainerSensor(coordinator, host, port, name)
            )

    async_add_entities(entities)


class RadiusStackSensor(CoordinatorEntity[RadiusStackCoordinator], SensorEntity):
    """A single RadiusStack-HA sensor."""

    entity_description: RadiusStackSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RadiusStackCoordinator,
        description: RadiusStackSensorDescription,
        host: str,
        port: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"radiusstack_{host}_{port}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=f"RadiusStack-HA ({host}:{port})",
            manufacturer="RadiusStack",
            model="FreeRADIUS Stack",
            configuration_url=f"http://{host}:{port}",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class RadiusStackContainerSensor(CoordinatorEntity[RadiusStackCoordinator], SensorEntity):
    """Per-container state sensor (running / stopped / etc.)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"

    def __init__(
        self,
        coordinator: RadiusStackCoordinator,
        host: str,
        port: int,
        container_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._container_name = container_name
        display = container_name.replace("radius_", "").replace("_", " ").title()
        self._attr_name = f"Container {display}"
        self._attr_unique_id = f"radiusstack_{host}_{port}_container_{container_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=f"RadiusStack-HA ({host}:{port})",
            manufacturer="RadiusStack",
            model="FreeRADIUS Stack",
            configuration_url=f"http://{host}:{port}",
        )

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        containers = self.coordinator.data.get(DATA_CONTAINERS, [])
        for c in containers:
            if c.get("name") == self._container_name:
                return c.get("state", "unknown")
        return "unknown"

    @property
    def icon(self) -> str:
        return "mdi:server" if self.native_value == "running" else "mdi:server-off"
