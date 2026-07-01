"""Sandbox MCP server for synthetic tester agents.

Unlike ``app.adapters.mcp.server`` this exposes no production DB, no Telegram,
and no write tools. It is intended for local Qwen/OpenCode as a bounded synthetic
tester over deterministic in-memory flows.

Run from ``backend/``:

    python -m app.adapters.mcp.sandbox_server
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from scripts import simulate_student_flow  # noqa: E402

mcp = FastMCP("ege-mentor-sandbox")


@mcp.tool()
def run_student_simulation() -> dict[str, Any]:
    """Run deterministic in-memory learner-flow simulation.

    Covers interval overlay, unparseable interval fallback, and source_ref-gated
    probability visual. Does not connect to production Postgres or Telegram.
    """
    return json.loads(simulate_student_flow.run_json())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
