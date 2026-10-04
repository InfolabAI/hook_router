"""Keep Codex in this process group; terminate it if the caller disappears."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from hook_router.storage import identity


def main():
    parent, token, cancel, *command = sys.argv[1:]
    if identity(int(parent)) != token or Path(cancel).exists():
        return 130
    child = subprocess.Popen(command)  # same group, same pipes
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while child.poll() is None:
        if stopped or Path(cancel).exists() or identity(int(parent)) != token:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            os.killpg(os.getpgrp(), signal.SIGTERM)
            time.sleep(0.2)
            os.killpg(os.getpgrp(), signal.SIGKILL)
        time.sleep(0.05)
    return child.returncode


if __name__ == '__main__':
    raise SystemExit(main())
