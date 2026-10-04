"""The Python coordinator validates model output before advancing a plan."""
WORKER_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['status', 'report_markdown', 'evidence'],
    'properties': {
        'status': {'type': 'string', 'enum': ['completed', 'blocked', 'failed']},
        'report_markdown': {'type': 'string'},
        'evidence': {'type': 'array', 'items': {'type': 'string'}},
    },
}


def route_schema(profiles):
    return {'type': 'object', 'additionalProperties': False, 'required': ['steps'], 'properties': {
        'steps': {'type': 'array', 'minItems': 1, 'maxItems': 32, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['model', 'effort', 'commands'],
            'properties': {
                'model': {'type': 'string', 'enum': sorted({p['model'] for p in profiles})},
                'effort': {'type': 'string', 'enum': sorted({p['effort'] for p in profiles})},
                'commands': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
            }}}}}


def validate_plan(value, request, profiles):
    if not isinstance(value, dict) or set(value) != {'steps'}:
        raise ValueError('Expected only steps')
    steps = value['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise ValueError('Expected 1 to 32 steps')
    pairs = {(p['model'], p['effort']) for p in profiles}
    merged, chunks = [], []
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'model', 'effort', 'commands'}:
            raise ValueError('Invalid step fields')
        if not all(isinstance(step[k], str) for k in ('model', 'effort')) or (step['model'], step['effort']) not in pairs:
            raise ValueError('Unsupported model/effort pair')
        commands = step['commands']
        if not isinstance(commands, list) or not commands or not all(isinstance(c, str) and c.strip() for c in commands):
            raise ValueError('Expected nonempty commands')
        chunks.extend(commands)
        if merged and all(merged[-1][k] == step[k] for k in ('model', 'effort')):
            merged[-1]['commands'].extend(commands)
        else:
            merged.append(dict(step, commands=list(commands)))
    if ''.join(chunks) != request:
        raise ValueError('Commands must concatenate to the exact original request, in order')
    return {'steps': merged}


def validate_worker(value):
    if not isinstance(value, dict) or set(value) != set(WORKER_SCHEMA['required']):
        raise ValueError('Invalid result fields')
    if value['status'] not in ('completed', 'blocked', 'failed'):
        raise ValueError('Invalid status')
    if not isinstance(value['report_markdown'], str) or not value['report_markdown'].strip():
        raise ValueError('Empty report')
    if not isinstance(value['evidence'], list) or not all(isinstance(v, str) and v.strip() for v in value['evidence']):
        raise ValueError('Invalid evidence')
    if value['status'] == 'completed' and not value['evidence']:
        raise ValueError('Completed work requires evidence')
    return value
