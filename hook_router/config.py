import json
from pathlib import Path

DEFAULT = {
    'trigger': '@route',
    'router': {'model': 'gpt-6.1-sol', 'effort': 'low'},
    'profiles': [
        {'name': 'routine', 'model': 'gpt-6.1-sol', 'effort': 'low',
         'description': 'Summaries, extraction, routine edits, and follow-ups based on completed analysis.'},
        {'name': 'analysis', 'model': 'gpt-6.1-sol', 'effort': 'medium',
         'description': 'New technical analysis, evidence review, and nontrivial debugging.'},
        {'name': 'complex', 'model': 'gpt-6-astra', 'effort': 'high',
         'description': 'Difficult design, conflicting evidence, or an explicit request for the strongest model.'},
    ],
    'sandbox': 'read-only', 'network_access': False, 'writable_roots': [],
    'instructions': 'Complete only the current step. Respect the user\'s scope. Do not send messages or change external systems without explicit authorization.',
    'state_dir': '~/.local/share/codex-hook-router',
    'total_timeout': 900, 'router_timeout': 120, 'worker_timeout': 780,
}


def load(path):
    config = json.loads(Path(path).expanduser().read_text(encoding='utf-8'))
    if set(config) - set(DEFAULT):
        raise ValueError('Unknown configuration keys')
    config = dict(DEFAULT, **config)
    profiles = config['profiles']
    if not isinstance(profiles, list) or not profiles:
        raise ValueError('At least one profile is required')
    for profile in [config['router'], *profiles]:
        if not isinstance(profile, dict) or not all(isinstance(profile.get(k), str) and profile[k] for k in ('model', 'effort')):
            raise ValueError('Every profile needs a model and effort')
    for profile in profiles:
        if not all(isinstance(profile.get(k), str) and profile[k] for k in ('name', 'description')):
            raise ValueError('Worker profiles need names and descriptions')
    if len({(p['model'], p['effort']) for p in profiles}) != len(profiles):
        raise ValueError('Worker model/effort pairs must be unique')
    if config['sandbox'] not in ('read-only', 'workspace-write'):
        raise ValueError('sandbox must be read-only or workspace-write')
    if not isinstance(config['network_access'], bool):
        raise ValueError('network_access must be boolean')
    if config['network_access'] and config['sandbox'] != 'workspace-write':
        raise ValueError('Network-enabled workers require workspace-write')
    if not isinstance(config['writable_roots'], list) or not all(isinstance(p, str) for p in config['writable_roots']):
        raise ValueError('writable_roots must be a list of paths')
    if not isinstance(config['trigger'], str) or not config['trigger'].startswith('@') or any(c.isspace() for c in config['trigger']):
        raise ValueError('trigger must be a single @command')
    for key in ('total_timeout', 'router_timeout', 'worker_timeout'):
        if type(config[key]) is not int or not 1 <= config[key] <= 86400:
            raise ValueError('Timeouts must be positive integers, at most 86400 seconds')
    if not isinstance(config['instructions'], str) or not isinstance(config['state_dir'], str):
        raise ValueError('instructions and state_dir must be strings')
    state = Path(config['state_dir']).expanduser()
    if not state.is_absolute():
        state = Path(path).expanduser().resolve().parent / state
    config['state_dir'] = str(state.resolve())
    return config
