"""Color-coded, human-readable formatting of Route53 record changes."""

import sys
from collections import Counter
from typing import Dict, List, Set

COLOR_RESET = "\033[0m"
COLOR_MAP = {
    "CREATE": "\033[32m",  # Green
    "DELETE": "\033[31m",  # Red
    "UPSERT": "\033[36m",  # Cyan
}


class RecordFormatter:
    """Formats Route53 record changes for human-readable display."""

    def __init__(self, use_color=None):
        self.use_color = sys.stdout.isatty() if use_color is None else use_color

    def _colorize(self, text: str, operation: str) -> str:
        color = COLOR_MAP.get(operation)
        if not self.use_color or not color:
            return text
        return f"{color}{text}{COLOR_RESET}"

    def get_batch_summary(self, changes: List[Dict]) -> str:
        """Build a one-line summary like '3 changes: 2 CREATE, 1 DELETE'."""
        total = len(changes)
        if total == 0:
            return "0 changes"
        if total == 1:
            return "1 change"
        counts = Counter(c["operation"] for c in changes)
        detail = ", ".join(f"{counts[op]} {op}" for op in sorted(counts))
        return f"{total} changes: {detail}"

    def format_batch(self, changes: List[Dict]) -> str:
        """Format a batch of changes for display."""
        return "\n".join(self.format_change(c) for c in changes)

    def format_change(self, change: Dict) -> str:
        """Format a single change as a header line plus value or diff lines."""
        operation = change["operation"]
        record = change["record"]
        old_record = change.get("old_record")

        header_parts = [record.Name, record.Type]
        if record.AliasTarget is not None:
            header_parts.append("[ALIAS]")
        elif record.TTL is not None:
            header_parts.append(f"(TTL: {record.TTL})")

        policy_info = self._format_routing_policy_brief(record)
        if policy_info:
            header_parts.append(policy_info)

        operation_label = self._colorize(f"{operation:6}", operation)
        lines = [f"  {operation_label} {' '.join(header_parts)}"]

        if operation == "UPSERT" and old_record:
            lines.extend(self._format_upsert_diff(old_record, record))
        else:
            lines.extend(self._format_values(record))

        return "\n".join(lines)

    def _format_routing_policy_brief(self, record) -> str:
        """Format routing policy fields as a parenthesized summary."""
        parts = []
        if record.SetIdentifier:
            parts.append(f"SetIdentifier: {record.SetIdentifier}")
        if record.Weight is not None:
            parts.append(f"Weight: {record.Weight}")
        if record.Region:
            parts.append(f"Region: {record.Region}")
        if record.Failover:
            parts.append(f"Failover: {record.Failover}")
        if record.GeoLocation:
            parts.append(f"GeoLocation: {self._format_geolocation(record.GeoLocation)}")
        if record.HealthCheckId:
            parts.append(f"HealthCheck: {record.HealthCheckId}")
        return f"({', '.join(parts)})" if parts else ""

    def _format_geolocation(self, geo) -> str:
        """Format a GeoLocation as continent/country/subdivision."""
        parts = [
            code
            for code in (
                getattr(geo, "ContinentCode", None),
                getattr(geo, "CountryCode", None),
                getattr(geo, "SubdivisionCode", None),
            )
            if code
        ]
        return "/".join(parts) if parts else str(geo)

    def _format_values(self, record) -> List[str]:
        """Format a record's alias target or resource record values."""
        if record.AliasTarget:
            alias = record.AliasTarget
            line = f"         -> {alias.DNSName}"
            if alias.HostedZoneId:
                line += f" (ZoneId: {alias.HostedZoneId})"
            return [line]
        if record.ResourceRecords:
            return [f"         -> {rr.Value}" for rr in record.ResourceRecords]
        return []

    def _format_upsert_diff(self, old_record, new_record) -> List[str]:
        """Format the field-by-field diff between old and new records."""
        lines = []
        old_dict = old_record.model_dump(exclude_none=True)
        new_dict = new_record.model_dump(exclude_none=True)

        compare_fields = [
            "TTL",
            "SetIdentifier",
            "Weight",
            "Region",
            "Failover",
            "MultiValueAnswer",
            "HealthCheckId",
            "TrafficPolicyInstanceId",
        ]
        for field in compare_fields:
            old_val = old_dict.get(field)
            new_val = new_dict.get(field)
            if old_val != new_val:
                old_str = old_val if old_val is not None else "(none)"
                new_str = new_val if new_val is not None else "(none)"
                lines.append(f"         {field}: {old_str} -> {new_str}")

        if old_dict.get("GeoLocation") != new_dict.get("GeoLocation"):
            old_geo = (
                self._format_geolocation(old_record.GeoLocation)
                if old_record.GeoLocation
                else "(none)"
            )
            new_geo = (
                self._format_geolocation(new_record.GeoLocation)
                if new_record.GeoLocation
                else "(none)"
            )
            lines.append(f"         GeoLocation: {old_geo} -> {new_geo}")

        old_alias = old_record.AliasTarget
        new_alias = new_record.AliasTarget
        if old_alias and new_alias:
            if (old_alias.DNSName, old_alias.HostedZoneId) != (
                new_alias.DNSName,
                new_alias.HostedZoneId,
            ):
                lines.append(
                    f"         - {old_alias.DNSName} (ZoneId: {old_alias.HostedZoneId})"
                )
                lines.append(
                    f"         + {new_alias.DNSName} (ZoneId: {new_alias.HostedZoneId})"
                )
        elif old_alias:
            lines.append(
                f"         - {old_alias.DNSName} (ZoneId: {old_alias.HostedZoneId})"
            )
        elif new_alias:
            lines.append(
                f"         + {new_alias.DNSName} (ZoneId: {new_alias.HostedZoneId})"
            )

        if not old_alias and not new_alias:
            old_values = self._extract_record_values(old_record)
            new_values = self._extract_record_values(new_record)
            for value in sorted(old_values - new_values):
                lines.append(f"         - {value}")
            for value in sorted(new_values - old_values):
                lines.append(f"         + {value}")

        return lines

    def _extract_record_values(self, record) -> Set[str]:
        """Return a record's resource record values as a set."""
        if not record.ResourceRecords:
            return set()
        return {rr.Value for rr in record.ResourceRecords}
