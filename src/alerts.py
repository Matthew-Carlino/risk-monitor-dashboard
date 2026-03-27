"""Alert system for risk monitoring."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Single alert record."""

    timestamp: datetime
    metric: str
    current_value: float
    threshold: float
    severity: Severity
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"{self.severity.value} [{self.metric}]: {self.message}"


class AlertEngine:
    """Manage and trigger alerts based on configurable thresholds."""

    def __init__(self):
        """Initialize alert engine."""
        self.alerts: List[Alert] = []
        self.thresholds: Dict[str, float] = {
            "var_99": 0.05,  # 5% daily VaR
            "max_drawdown": 0.10,  # 10% max drawdown
            "herfindahl_index": 0.20,  # Concentration limit
            "correlation_threshold": 0.75,  # Correlation spike
            "gross_leverage": 2.0,  # Max leverage
        }
        self.active_alerts: Dict[str, Alert] = {}

    def set_threshold(self, metric: str, value: float) -> None:
        """Set alert threshold for a metric.

        Args:
            metric: Metric name.
            value: Threshold value.
        """
        self.thresholds[metric] = value
        logger.info(f"Set threshold {metric} = {value}")

    def check_var_breach(self, var_value: float, var_limit: float) -> Optional[Alert]:
        """Check if VaR exceeds limit.

        Args:
            var_value: Current VaR.
            var_limit: Threshold.

        Returns:
            Alert if breached, None otherwise.
        """
        if var_value > var_limit:
            severity = Severity.CRITICAL if var_value > var_limit * 1.5 else Severity.WARNING
            alert = Alert(
                timestamp=datetime.now(),
                metric="VaR_99",
                current_value=var_value,
                threshold=var_limit,
                severity=severity,
                message=f"VaR breach: {var_value:.4f} > {var_limit:.4f}",
            )
            return alert
        return None

    def check_drawdown_breach(self, dd: float, dd_limit: float) -> Optional[Alert]:
        """Check if drawdown exceeds limit.

        Args:
            dd: Current maximum drawdown.
            dd_limit: Threshold.

        Returns:
            Alert if breached, None otherwise.
        """
        if dd > dd_limit:
            severity = Severity.CRITICAL if dd > dd_limit * 1.5 else Severity.WARNING
            alert = Alert(
                timestamp=datetime.now(),
                metric="Max_Drawdown",
                current_value=dd,
                threshold=dd_limit,
                severity=severity,
                message=f"Drawdown breach: {dd:.2%} > {dd_limit:.2%}",
            )
            return alert
        return None

    def check_concentration(self, hhi: float, hhi_limit: float) -> Optional[Alert]:
        """Check if portfolio concentration exceeds limit.

        Args:
            hhi: Herfindahl-Hirschman Index.
            hhi_limit: Threshold.

        Returns:
            Alert if breached, None otherwise.
        """
        if hhi > hhi_limit:
            severity = Severity.WARNING if hhi < 0.3 else Severity.CRITICAL
            alert = Alert(
                timestamp=datetime.now(),
                metric="HHI",
                current_value=hhi,
                threshold=hhi_limit,
                severity=severity,
                message=f"Concentration warning: HHI {hhi:.4f} > {hhi_limit:.4f}",
            )
            return alert
        return None

    def check_correlation_spike(self, corr: float, corr_limit: float) -> Optional[Alert]:
        """Check if correlation spikes above threshold.

        Args:
            corr: Current average correlation.
            corr_limit: Threshold.

        Returns:
            Alert if breached, None otherwise.
        """
        if corr > corr_limit:
            alert = Alert(
                timestamp=datetime.now(),
                metric="Correlation_Spike",
                current_value=corr,
                threshold=corr_limit,
                severity=Severity.WARNING,
                message=f"Correlation spike: {corr:.3f} > {corr_limit:.3f} (diversification breaking down)",
            )
            return alert
        return None

    def check_leverage_limit(self, leverage: float, limit: float) -> Optional[Alert]:
        """Check if leverage exceeds limit.

        Args:
            leverage: Current gross leverage.
            limit: Threshold.

        Returns:
            Alert if breached, None otherwise.
        """
        if leverage > limit:
            severity = Severity.CRITICAL
            alert = Alert(
                timestamp=datetime.now(),
                metric="Gross_Leverage",
                current_value=leverage,
                threshold=limit,
                severity=severity,
                message=f"Leverage breach: {leverage:.2f}x > {limit:.2f}x",
            )
            return alert
        return None

    def add_alert(self, alert: Alert) -> None:
        """Record a new alert.

        Args:
            alert: Alert to record.
        """
        self.alerts.append(alert)
        self.active_alerts[alert.metric] = alert
        logger.warning(f"Alert triggered: {alert}")

    def resolve_alert(self, metric: str) -> None:
        """Mark alert as resolved.

        Args:
            metric: Metric name.
        """
        if metric in self.active_alerts:
            self.active_alerts[metric].resolved = True
            self.active_alerts[metric].resolved_at = datetime.now()
            del self.active_alerts[metric]

    def get_active_alerts(self) -> List[Alert]:
        """Get all active unresolved alerts.

        Returns:
            List of active Alert objects.
        """
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """Get recent alert history.

        Args:
            limit: Max alerts to return. Default 50.

        Returns:
            List of recent alerts (newest first).
        """
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def severity_count(self) -> Dict[str, int]:
        """Count active alerts by severity.

        Returns:
            Dict of {severity: count}.
        """
        counts = {s.value: 0 for s in Severity}
        for alert in self.get_active_alerts():
            counts[alert.severity.value] += 1
        return counts
