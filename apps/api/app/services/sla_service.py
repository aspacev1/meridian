"""SLA status computation, per ARCHITECTURE.md's SLA Monitor logic."""

from datetime import time

SLA_RANK = {"healthy": 0, "warning": 1, "breach": 2, "no_scan": 2}


def compute_sla_status(
    delivery_time: time | None,
    target_time: time,
    run_status: str,
    dq_pass_rate_pct: float,
    dq_threshold_pct: int,
) -> str:
    if run_status == "failed":
        return "breach"
    if delivery_time is None:
        return "breach"
    if delivery_time > target_time:
        return "warning"
    if dq_pass_rate_pct < dq_threshold_pct:
        return "warning"
    return "healthy"


def dq_pass_rate_pct(dq_rules_passed: int, dq_rules_total: int) -> float:
    if dq_rules_total <= 0:
        return 100.0
    return (dq_rules_passed / dq_rules_total) * 100


def worst_status(statuses: list[str]) -> str:
    """breach > warning > healthy, used to roll layer statuses up to a
    pipeline-run-level status."""
    return max(statuses, key=lambda s: SLA_RANK.get(s, 0), default="no_scan")
