#!/usr/bin/env python3
"""Portable entrypoint; may be called from any workspace directory."""
from hook_router.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
