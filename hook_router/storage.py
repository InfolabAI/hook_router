"""Private atomic state and Linux process identities."""
import json
import os
from pathlib import Path
import tempfile


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def identity(pid):
    """Start ticks prevent signaling a reused PID. None includes zombies."""
    try:
        path = Path('/proc') / str(pid) / 'stat'
        if path.stat().st_uid != os.getuid():
            return None
        fields = path.read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None
