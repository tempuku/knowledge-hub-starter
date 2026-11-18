"""Fail-closed, trusted process maintenance switch for M-04 (#38).

This is one *local* writer interlock, not a distributed lease. Operators must
pause every trusted CLI/MCP/legacy writer launch and independently freeze the
upstream production branch before declaring a cutover maintenance window.
"""
from __future__ import annotations

import os

ENV = "KH_WRITES_MAINTENANCE"


def writes_paused(environ=None) -> bool:
    """Only an absent flag or the explicit '0' permits writes.

    Fail closed for empty, malformed, and alternate truthy values: a misspelled
    value must never silently reopen writes during a cutover window.
    """
    values = os.environ if environ is None else environ
    return values.get(ENV) not in (None, "0")
