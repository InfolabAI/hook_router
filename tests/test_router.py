import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from hook_router.config import DEFAULT, load
from hook_router.contracts import validate_plan, validate_worker
from hook_router.engine import run, session_path, relay
from hook_router.install import install
from hook_router.processes import command, interrupt
from hook_router.storage import identity, read, write
from hook_router.cli import extract_request

ROOT = Path(__file__).resolve().parents[1]


def step(text, effort='low'):
    return dict(model='gpt-6.1-sol', effort=effort, commands=[text])


def result(status='completed', report='fixture result'):
    return dict(status=status, report_markdown=report, evidence=['fixture:1'])


class Tests(unittest.TestCase):
    def test_plugin_mention_and_prefix(self):
        for prefix in ('@route', '@Route', '[@Route](plugin://route@hook-router)', '[Route](plugin://route@local)'):
            self.assertEqual(extract_request(prefix + ' A\nB', '@route'), 'A\nB')
            self.assertEqual(extract_request(prefix + ' --resume', '@route'), '--resume')
            self.assertEqual(extract_request(prefix, '@route'), '')
        for prompt in ('ordinary request', '@route-other A', 'Discuss @route A',
                       '[Route](https://example.com) A', '[Route](plugin://route-other@local) A'):
            self.assertIsNone(extract_request(prompt, '@route'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = copy.deepcopy(DEFAULT)
        self.config['state_dir'] = str(self.root/'state')
        self.config_path = self.root/'config.json'
        write(self.config_path, self.config)

    def test_contract_order_merge_and_rejection(self):
        p = validate_plan({'steps':[step('A,'),step('B,'),step('C,'),step('D,','medium'),step('E')]},'A,B,C,D,E', self.config['profiles'])
        self.assertEqual([s['commands'] for s in p['steps']], [['A,','B,','C,'],['D,'],['E']])
        for bad in [{'steps':[step('ACB')]}, {'steps':[step('ABC','high')]}, {'steps':[step('')]}, {}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_plan(bad,'ABC',self.config['profiles'])
        with self.assertRaises(ValueError):
            validate_worker(dict(result(), evidence=[]))
        with self.assertRaises(ValueError):
            validate_worker(dict(result(), extra=True))

    def test_three_groups_same_thread_and_relay(self):
        calls=[]
        def fake(*args, **kwargs):
            calls.append((args,kwargs))
            if kwargs.get('router'):
                return {'steps':[step('ABC'),step('D','medium'),step('E')]},{'ok':True}
            return result(report='evidence '+str(len(calls))),{'ok':True,'thread_id':'same-thread'}
        with patch('hook_router.engine.invoke',side_effect=fake):
            text=run(self.config,'parent','turn','ABCDE',self.root)
        self.assertEqual([c[0][5]['effort'] for c in calls[1:]],['low','medium','low'])
        self.assertEqual(calls[2][1]['thread'],'same-thread')
        self.assertIn('evidence 2',calls[2][0][7])
        self.assertEqual(text.count('[Model:'),3)
        self.assertNotIn('pending_run',read(session_path(self.config,'parent')/'state.json'))
        output=relay(self.config,text)
        self.assertNotIn('decision',output)
        self.assertIn('Do not re-execute',output['hookSpecificOutput']['additionalContext'])

    def test_failure_and_resume_skips_completed(self):
        with patch('hook_router.engine.invoke',side_effect=[
            ({'steps':[step('A'),step('D','medium'),step('E')]},{'ok':True}),
            (result(),{'ok':True,'thread_id':'thread'}),
            (result('failed'),{'ok':True,'thread_id':'thread'})]):
            text=run(self.config,'parent','turn','ADE',self.root)
        self.assertIn('--resume',text)
        with patch('hook_router.engine.invoke',return_value=(result(),{'ok':True,'thread_id':'thread'})) as call:
            run(self.config,'parent','turn2','--resume',self.root)
        self.assertEqual(call.call_count,2)
        self.assertIn('"current_commands": ["D"]',call.call_args_list[0].args[7])
        self.assertIn('"recovering_partial_step": true',call.call_args_list[0].args[7])

    def test_invalid_router_and_missing_thread(self):
        with patch('hook_router.engine.invoke',return_value=({}, {'ok':True})) as call:
            text=run(self.config,'parent','turn','A',self.root)
        self.assertEqual(call.call_count,2)
        self.assertIn('No worker',text)
        with patch('hook_router.engine.invoke',side_effect=[({'steps':[step('A')]},{'ok':True}),(None,{'ok':False})]):
            run(self.config,'other','turn','A',self.root)
        with patch('hook_router.engine.invoke') as call:
            text=run(self.config,'other','turn2','--resume',self.root)
        call.assert_not_called()
        self.assertIn('session ID is missing',text)

    def test_config_and_resume_network_flags(self):
        c=load(self.config_path)
        self.assertEqual(c['sandbox'],'read-only')
        c.update(sandbox='workspace-write',network_access=True)
        work=self.root/'work';work.mkdir()
        cmd=command(c,work,self.root,c['router'],{},thread='abc')
        self.assertNotIn('-c',cmd[:cmd.index('resume')])
        self.assertIn('sandbox_workspace_write.network_access=true',cmd)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',cmd)
        write(self.config_path,dict(self.config,sandbox='danger-full-access'))
        with self.assertRaises(ValueError):load(self.config_path)

    def test_install_idempotent_preserves_unrelated(self):
        p=self.root/'hooks.json'
        other={'type':'command','command':'echo unrelated'}
        write(p,{'description':'keep','hooks':{'UserPromptSubmit':[{'hooks':[other]}]}})
        for _ in range(2):install(p,ROOT/'router.py',self.config_path,900)
        d=read(p);self.assertEqual(d['description'],'keep')
        self.assertEqual(len(d['hooks']['UserPromptSubmit']),2)
        self.assertEqual(len(d['hooks']['Interrupt']),1)
        install(p,ROOT/'router.py',self.config_path,900,remove=True)
        self.assertEqual(read(p)['hooks'],{'UserPromptSubmit':[{'hooks':[other]}]})

    def test_long_relay_private_file(self):
        value='[Model: example | Reasoning: low]\n'+('text\n'*1000)
        context=relay(self.config,value)['hookSpecificOutput']['additionalContext']
        self.assertNotIn('report_json:',context)
        path,=list((Path(self.config['state_dir'])/'reports').glob('*/report.md'))
        self.assertEqual(path.read_text(),value)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def fake_codex(self, waiting=False):
        binpath=self.root/'bin';binpath.mkdir()
        code='''import json,sys,os,time,subprocess
from pathlib import Path
prompt=sys.stdin.read()
out=Path(sys.argv[sys.argv.index('--output-last-message')+1])
if 'Request to split:' in prompt:
 request=json.loads(prompt.split('Request to split:\\n')[1].split('\\nYour previous')[0])
 result={'steps':[{'model':'gpt-6.1-sol','effort':'low','commands':[request]}]}
else:
 if os.environ.get('FAKE_WAIT')=='1':
  child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
  Path(os.environ['PID_FILE']).write_text(json.dumps([os.getpid(),child.pid]))
  time.sleep(60)
 result={'status':'completed','report_markdown':'Fixture executed','evidence':['fixture:1']}
out.write_text(json.dumps(result))
print(json.dumps({'type':'thread.started','thread_id':'fake-thread'}),flush=True)
'''
        file=binpath/'codex';file.write_text('#!'+sys.executable+'\n'+code);file.chmod(0o700)
        return dict(os.environ,PATH=str(binpath)+os.pathsep+os.environ['PATH'],FAKE_WAIT='1' if waiting else '0',PID_FILE=str(self.root/'pids'))

    def start_hook(self,env,prompt='@route fixture'):
        p=subprocess.Popen([sys.executable,str(ROOT/'router.py'),'--config',str(self.config_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        p.stdin.write(json.dumps({'hook_event_name':'UserPromptSubmit','prompt':prompt,'session_id':'parent','turn_id':'turn','cwd':str(self.root)}));p.stdin.close();p.stdin=None
        self.addCleanup(lambda: p.kill() if p.poll() is None else None)
        return p

    def test_full_cli_with_fake_codex(self):
        p=self.start_hook(self.fake_codex())
        out,err=p.communicate(timeout=10)
        self.assertEqual(p.returncode,0,err)
        self.assertIn('Fixture executed',json.loads(out)['hookSpecificOutput']['additionalContext'])

    def test_plugin_mention_full_cli(self):
        p=self.start_hook(self.fake_codex(),'[@Route](plugin://route@hook-router) fixture')
        out,err=p.communicate(timeout=10)
        self.assertEqual(p.returncode,0,err)
        self.assertIn('Fixture executed',json.loads(out)['hookSpecificOutput']['additionalContext'])

    def wait_pids(self):
        path=self.root/'pids'
        for _ in range(100):
            if path.exists():return read(path)
            time.sleep(.03)
        self.fail('fake worker did not start')

    def assert_dead(self,pids):
        for _ in range(100):
            if all(identity(pid) is None for pid in pids):return
            time.sleep(.03)
        self.fail('worker/descendant still alive')

    def test_interrupt_kills_worker_and_child(self):
        p=self.start_hook(self.fake_codex(True));pids=self.wait_pids()
        session=session_path(self.config,'parent')
        interrupt(session,'unrelated-turn')
        self.assertIsNone(p.poll())
        started=time.monotonic();interrupt(session,'turn')
        p.communicate(timeout=4)
        self.assert_dead(pids)
        self.assertLess(time.monotonic()-started,3)
        state=read(session/'state.json');plan=read(session/state['pending_run']/'plan.json')
        self.assertNotEqual(plan['steps'][0]['status'],'completed')

    def test_parent_sigkill_guardian_cleans_children(self):
        p=self.start_hook(self.fake_codex(True));pids=self.wait_pids()
        p.kill();p.communicate(timeout=4)
        self.assert_dead(pids)


if __name__=='__main__':unittest.main()
