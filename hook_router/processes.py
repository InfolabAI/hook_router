"""Codex invocation, bounded cancellation, and per-turn process registration."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import json

from hook_router.storage import identity, read, write


class Cancelled(Exception):
    pass


def terminate(pid, token):
    if token and identity(pid) == token:
        try:
            os.killpg(pid, signal.SIGTERM)
            time.sleep(0.2)
            # The guardian stays alive until group cleanup; check identity again.
            if identity(pid) == token:
                os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def interrupt(session, turn_id):
    active_path = session / 'active.json'
    if not active_path.exists():
        return
    active = read(active_path)
    if active['turn_id'] != turn_id or not identity(active['owner_pid']) == active['owner_token']:
        return
    write(Path(active['cancel']), 'cancelled')
    worker = active.get('worker')
    if worker:
        terminate(worker['pid'], worker['token'])
    try:
        if identity(active['owner_pid']) == active['owner_token']:
            os.kill(active['owner_pid'], signal.SIGTERM)
    except ProcessLookupError:
        pass


def command(config, work, cwd, profile, schema, thread=None, router=False):
    cmd = ['codex', 'exec', '--ignore-user-config', '--skip-git-repo-check',
           '--cd', str(cwd), '--sandbox', 'read-only' if router else config['sandbox']]
    if not router:
        for root in config['writable_roots']:
            cmd += ['--add-dir', str(Path(root).expanduser().resolve())]
    if thread:
        cmd += ['resume', thread]
    # All -c flags belong AFTER resume. Splitting them loses overrides in 0.160.0.
    cmd += ['-c', 'approval_policy="never"', '-c', 'features.hooks=false',
            '-c', 'features.apps=false', '-c', 'features.multi_agent=false']
    if not router and config['sandbox'] == 'workspace-write':
        cmd += ['-c', 'sandbox_workspace_write.network_access=' + str(config['network_access']).lower()]
    if router:
        cmd += ['--ephemeral']
    write(work / 'schema.json', schema)
    cmd += ['--model', profile['model'], '-c', 'model_reasoning_effort=' + json.dumps(profile['effort']),
            '--json', '--output-schema', str(work / 'schema.json'),
            '--output-last-message', str(work / 'answer.json'), '-']
    return cmd


def invoke(config, session, active, work, cwd, profile, schema, prompt, timeout, thread=None, router=False):
    work.mkdir(mode=0o700)
    write(work / 'prompt.txt', prompt)
    cmd = command(config, work, cwd, profile, schema, thread, router)
    env = dict(os.environ, HOOK_ROUTER_CHILD='1')
    for key in list(env):
        if any(word in key.upper() for word in ('TOKEN', 'API_KEY', 'SECRET', 'PASSWORD')):
            env.pop(key)
    # The guardian is launched as a module in the same portable checkout.
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
    guardian = [sys.executable, '-m', 'hook_router.guardian', str(os.getpid()),
                identity(os.getpid()), active['cancel'], *cmd]
    proc = None
    started = time.monotonic()
    meta = dict(model=profile['model'], effort=profile['effort'], ok=False)
    stdout = ''
    try:
        if Path(active['cancel']).exists():
            raise Cancelled()
        proc = subprocess.Popen(guardian, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
        active['worker'] = {'pid': proc.pid, 'token': identity(proc.pid)}
        write(session / 'active.json', active)
        stdout, _ = proc.communicate(prompt, timeout=timeout)
        if Path(active['cancel']).exists():
            raise Cancelled()
        if proc.returncode != 0:
            raise RuntimeError('Codex invocation failed; check login/model availability')
        result = read(work / 'answer.json')
        meta['ok'] = True
    except (Cancelled, KeyboardInterrupt, subprocess.TimeoutExpired) as exc:
        if proc:
            terminate(proc.pid, active.get('worker', {}).get('token'))
            stdout, _ = proc.communicate()
        meta['error'] = 'timeout' if isinstance(exc, subprocess.TimeoutExpired) else 'interrupted'
        result = None
    except (OSError, ValueError, RuntimeError):
        meta['error'] = 'process_or_output_error'
        result = None
    finally:
        if proc and proc.poll() is None:
            terminate(proc.pid, active.get('worker', {}).get('token'))
            proc.wait()
        active.pop('worker', None)
        write(session / 'active.json', active)
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'thread.started':
            meta['thread_id'] = event.get('thread_id')
        if event.get('type') == 'turn.completed':
            meta['usage'] = event.get('usage')
    meta['seconds'] = round(time.monotonic() - started, 3)
    write(work / 'metadata.json', meta)
    for file in work.iterdir():
        if file.is_file():
            file.chmod(0o600)
    return result, meta
