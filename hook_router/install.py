"""Merge or remove only this checkout's two hook entries; preserve others."""
from datetime import datetime, timezone
import shlex
import sys
from pathlib import Path

from hook_router.storage import read, write


def definitions(script, config_path, timeout):
    cmd = ' '.join(shlex.quote(str(v)) for v in (sys.executable, script, '--config', config_path))
    return {
        'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': cmd, 'timeout': timeout + 60}]}],
        'Interrupt': [{'hooks': [{'type': 'command', 'command': cmd, 'timeout': 3}]}],
    }


def install(path, script, config_path, timeout, remove=False):
    entries = definitions(script, config_path, timeout)
    command = entries['Interrupt'][0]['hooks'][0]['command']
    original = read(path) if path.exists() else {}
    hooks = original.setdefault('hooks', {})
    for event, groups in entries.items():
        kept = []
        for group in hooks.get(event, []):
            rest = [item for item in group.get('hooks', []) if item.get('command') != command]
            if rest:
                kept.append(dict(group, hooks=rest))
        if not remove:
            kept.extend(groups)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        write(path.with_name(path.name + '.' + stamp + '.bak'), path.read_text())
    write(path, original)
