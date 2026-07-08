"""Doctor check results and report formatting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["pass", "warn", "fail"]


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Single doctor check outcome."""

    name: str
    severity: Severity
    message: str
    harness: str | None = None


@dataclass(slots=True)
class DoctorReport:
    """Aggregated doctor results for one run."""

    checks: list[CheckResult]

    @property
    def exit_code(self) -> int:
        return 1 if any(check.severity == "fail" for check in self.checks) else 0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "checks": [asdict(check) for check in self.checks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def format(self, *, verbose: bool = False) -> str:
        lines: list[str] = []
        for check in self.checks:
            if not verbose and check.severity == "pass":
                continue
            prefix = check.severity.upper()
            scope = f" [{check.harness}]" if check.harness else ""
            lines.append(f"{prefix} {check.name}{scope}: {check.message}")
        if not lines:
            lines.append("PASS doctor: all checks passed")
        return "\n".join(lines)
