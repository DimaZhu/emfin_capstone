"""Build/install V2 and run it outside the checkout.

Uses a fresh temporary venv with independently installed runtime dependencies.
No publishing or upstream access. Every imported V2 file must be in that venv.
"""
from pathlib import Path
import json,os,subprocess,sys,tempfile,time,urllib.request,venv

ROOT=Path(__file__).resolve().parents[1]


def run(args,cwd,env):
    result = subprocess.run([str(a) for a in args],cwd=cwd,env=env,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    return result


def main():
    with tempfile.TemporaryDirectory(prefix='emfin-v2-installed-') as temp:
        root=Path(temp);wheel_dir=root/'wheel';wheel_dir.mkdir()
        env=os.environ.copy();env.pop('PYTHONPATH',None)
        build=run([sys.executable,'-m','pip','wheel',ROOT,'--no-deps','--no-build-isolation','--wheel-dir',wheel_dir],root,env)
        wheel=next(wheel_dir.glob('emfin_v2-*.whl'))
        venv_dir=root/'venv';venv.create(venv_dir,with_pip=True)
        bindir=venv_dir/('Scripts' if os.name=='nt' else 'bin')
        python=bindir/('python.exe' if os.name=='nt' else 'python')
        run([python,'-m','pip','install','--upgrade','pip>=26.2','setuptools>=84.1','wheel>=0.48'],root,env)
        run([python,'-m','pip','install',wheel],root,env)
        work=root/'outside-clone';work.mkdir()
        probe=run([python,'-c',"import emfin_v2,json; from emfin_v2.default_run import DEFAULT_CONFIG; from emfin_v2.toolbox.raw_data import series_file; print(json.dumps(dict(version=emfin_v2.__version__,module=emfin_v2.__file__,config=str(DEFAULT_CONFIG),data=str(series_file('DGS3MO')))))"],work,env)
        info=json.loads(probe.stdout)
        assert Path(info['module']).is_relative_to(venv_dir),info
        assert Path(info['config']).is_relative_to(venv_dir),info
        assert Path(info['data']).is_relative_to(venv_dir),info
        assert info['version']=='2.1.0'
        for name in ['emfin_v2','emfin_capstone']:
            result=run([python,'-m',name,'--output',work/name],work,env)
            report=json.loads((work/name/'results.json').read_text())
            assert report['status']['kind'] in ['optimized','calibrated optimizer/cash mixture'],report
            assert (work/name/'report.html').is_file()
            print(name,result.stdout.strip())
        cmd=bindir/('emfin-run.exe' if os.name=='nt' else 'emfin-run')
        run([cmd,'--output',work/'console'],work,env)
        explorer=bindir/('emfin-explore.exe' if os.name=='nt' else 'emfin-explore')
        run([explorer,'--export',work/'explorer.html'],work,env)
        assert 'Net wealth after cumulative payouts' in (work/'explorer.html').read_text()
        import socket
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        with (work/'server.log').open('w') as log:
            server=subprocess.Popen([str(explorer),'--port',str(port)],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                for _ in range(200):
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}',timeout=2) as response:
                            assert 'Net wealth after cumulative payouts' in response.read().decode()
                        break
                    except OSError:
                        if server.poll() is not None:raise RuntimeError((work/'server.log').read_text())
                        time.sleep(.1)
                else:raise RuntimeError('installed explorer did not start')
            finally:
                server.terminate();server.wait(timeout=10)
        print('PASS: installed wheel, bundled config/data/HTML, both launch names, console entrypoints and HTTP outside clone')
        print(json.dumps(info,indent=2))

if __name__=='__main__':main()
