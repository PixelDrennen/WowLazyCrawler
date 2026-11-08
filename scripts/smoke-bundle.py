"""Verify the packaged backend from an unrelated directory without system Python dependencies."""
import argparse
import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('bundle',type=Path)
args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='lazycrawler-moved-') as temp:
    root=Path(temp)
    shutil.copytree(args.bundle.resolve(),root/'renamed application')
    data=root/'user-data'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    log=(root/'smoke.log').open('w+')
    process=subprocess.Popen([str(root/'renamed application'/'lazycrawler-server'),'--port',str(port),'--data',str(data)],cwd=root,stdout=log,stderr=log)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=2) as client:
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read())
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('Bundled backend did not start')
            assert client.get('/').status_code==200
            assert 'assets/' in client.get('/').text
            assert client.get('/api/settings').status_code==401
            client.post('/api/login',json={'token':(data/'admin-token').read_text().strip()}).raise_for_status()
            config=client.get('/api/settings').json()
            admin=client.get('/api/admin').json()
            assert admin['origin']=='live' and admin['characters']==[]
            assert len(admin['coverage'])>50
            plan=client.get('/api/addon/plan').json()
            assert plan['origin']=='live' and plan['opportunities']==[]
            addon=root/'renamed application'/'_internal'/'addon'/'LazyCrawler'/'Core.lua'
            assert addon.is_file()
            assert config['region']=='us'
            response=client.get('/api/export')
            assert response.json()['schema_version']==1
            assert 'attachment' in response.headers['content-disposition']
            other=subprocess.run([str(root/'renamed application'/'lazycrawler-server'),'--port',str(port+1),'--data',str(data)],capture_output=True,text=True,timeout=10)
            assert other.returncode!=0 and 'already running' in other.stderr
        print('PASS: moved bundle starts, serves assets, authenticates, separates demo/live data, includes the addon and prevents duplicate workers')
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()
