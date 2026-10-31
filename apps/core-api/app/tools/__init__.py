"""Optional scenario tools. Importing the package registers every tool's snapshot
contributor and data counter."""

from app.tools import (  # noqa: F401  (registers on import)
    atmosphere,
    composure,
    rule_checks,
    rule_sheet,
    status_hud,
)
