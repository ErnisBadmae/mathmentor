#!/usr/bin/env python3
"""Compatibility shim for platform-devkit's documentation maintenance CLI.

Canonical implementation lives in `platform_devkit.cli.docs_maintenance`.
Keep this file so existing repo commands and docs that call
`python scripts/docs_maintenance.py ...` continue to work during Phase C.
"""

from __future__ import annotations

import sys

from platform_devkit.cli import docs_maintenance as _impl

main = _impl.main

if __name__ != "__main__":
    sys.modules[__name__] = _impl


if __name__ == "__main__":
    raise SystemExit(main())
