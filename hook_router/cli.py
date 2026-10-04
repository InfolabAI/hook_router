import argparse
import json
import os
from pathlib import Path
import re
import sys

from hook_router.config import DEFAULT, load
from hook_router.engine import relay, run, session_path
from hook_router.install import install
from hook_router.processes import interrupt
from hook_router.storage import write


def extract_request(prompt, trigger):
    """Accept the text prefix or a leading Route plugin mention from the picker."""
    plugin = r'\[[^\]\n]+\]\(plugin://route@[^\s/)]+\)'
    match = re.fullmatch(r'\s*(?:' + re.escape(trigger) + '|@Route|' + plugin + r')(?:\s+(.*))?', prompt, re.DOTALL)
    return (match.group(1) or '') if match else None


def main():
    parser = argparse.ArgumentParser(description='Ordered model routing for Codex UserPromptSubmit hooks (Linux).')
    parser.add_argument('--config', type=Path, default=Path.home()/'.config/codex-hook-router/config.json')
    parser.add_argument('--hooks-file', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))/'hooks.json')
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--init-config', action='store_true')
    options.add_argument('--install', action='store_true')
    options.add_argument('--uninstall', action='store_true')
    options.add_argument('--check', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if os.environ.get('HOOK_ROUTER_CHILD') == '1':
        return 0
    if not sys.platform.startswith('linux'):
        parser.error('Linux (including WSL2) is required for PID identity and process supervision')
    if args.init_config:
        if args.config.exists():
            parser.error('Config already exists; edit it directly')
        write(args.config, DEFAULT)
        print('Created config: ' + str(args.config))
        return 0
    # Ordinary prompts must remain untouched, even if configuration is broken.
    event = None
    if not (args.install or args.uninstall or args.check):
        event = json.load(sys.stdin)
    try:
        config = load(args.config)
        if args.install or args.uninstall:
            install(args.hooks_file.expanduser(), Path(__file__).resolve().parents[1]/'router.py',
                    args.config.expanduser().resolve(), config['total_timeout'], remove=args.uninstall)
            print('Removed this configuration hooks.' if args.uninstall else 'Installed. Open /hooks in Codex and trust both definitions before use.')
            return 0
        if args.check:
            print(json.dumps({'valid': True, 'trigger': config['trigger'], 'profiles': config['profiles'],
                              'sandbox': config['sandbox'], 'network_access': config['network_access']}))
            return 0
        kind = event.get('hook_event_name')
        parent, turn = event.get('session_id'), event.get('turn_id')
        if kind == 'Interrupt':
            if isinstance(parent, str) and isinstance(turn, str):
                interrupt(session_path(config, parent), turn)
            return 0
        if kind != 'UserPromptSubmit':
            return 0
        request = extract_request(event.get('prompt', ''), config['trigger'])
        if request is None:
            return 0
        cwd = Path(event.get('cwd', os.getcwd())).resolve()
        if not parent or not turn:
            answer = 'Missing session_id or turn_id. No work executed; update your Codex hook runtime.'
        elif not request.strip():
            answer = 'Usage: ' + config['trigger'] + ' <request>, --resume, or --cancel-plan'
        else:
            answer = run(config, parent, turn, request, cwd)
        print(json.dumps(relay(config, answer), ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Block on infrastructure/config failure: letting the parent execute the
        # original request might repeat a partially completed external action.
        if event and event.get('hook_event_name') == 'Interrupt':
            return 0
        if event:
            print(json.dumps({'decision': 'block', 'reason': 'Hook Router could not safely process the request (' + type(exc).__name__ + '). Inspect local state/config; do not blindly repeat effects.'}))
            return 0
        parser.error(type(exc).__name__ + ': ' + str(exc))
