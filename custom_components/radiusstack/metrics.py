"""Small dependency-free transformations for RadiusStack telemetry."""
from __future__ import annotations

from typing import Any


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _decimal(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def count_disabled_users(users: list[dict[str, Any]]) -> int:
    """Count all documented/legacy disabled-user representations."""
    return sum(
        user.get("disabled") is True
        or user.get("enabled") is False
        or str(user.get("status", "")).lower() == "disabled"
        for user in users
        if isinstance(user, dict)
    )


def depleted_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the plan-depletion summary without exposing user identities."""
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    plans = summary.get("plans", []) if isinstance(summary, dict) else []
    return {
        "total": _number(summary.get("total")),
        "users": _number(summary.get("users")),
        "mac_devices": _number(summary.get("mac_devices")),
        "plan_names": [str(row["plan_name"]) for row in plans if isinstance(row, dict) and row.get("plan_name")],
    }


def downstream_totals(stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate downstream proxy telemetry across selected-tenant destinations."""
    auth = accounting = 0
    average_rps = 0.0
    peak_minute_rps = 0.0
    for stat in stats.values():
        totals = stat.get("totals", {}) if isinstance(stat, dict) else {}
        auth += _number(totals.get("auth"))
        accounting += _number(totals.get("accounting"))
        average_rps += _decimal(stat.get("average_rps"))
        peak_minute_rps = max(peak_minute_rps, _decimal(stat.get("peak_minute_rps")))
    return {"auth": auth, "accounting": accounting, "requests": auth + accounting, "average_rps": round(average_rps, 4), "peak_minute_rps": peak_minute_rps}


def nas_totals(stats: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Aggregate selected-tenant NAS day telemetry."""
    fields = ("auth", "accept", "reject", "active", "input_bytes", "output_bytes")
    result: dict[str, int] = dict.fromkeys(fields, 0)
    for stat in stats.values():
        totals = stat.get("totals", {}) if isinstance(stat, dict) else {}
        for field in fields:
            result[field] += _number(totals.get(field))
    return result
