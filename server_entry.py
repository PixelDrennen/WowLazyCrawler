"""Bundled backend entry point; also usable with system Python."""
import argparse
import fcntl
import json
import os
import sys
from pathlib import Path
import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--data',default=os.environ.get('LAZYCRAWLER_DATA',str(Path.home()/'.local/share/wowlazycrawler')))
    args = parser.parse_args()
    os.environ['LAZYCRAWLER_DATA'] = args.data
    data_path=Path(args.data).expanduser().resolve()
    data_path.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.environ['LAZYCRAWLER_DATA']=str(data_path)
    lock_file=open(data_path/'server.lock','a')
    try:
        fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('LazyCrawler is already running with this data folder. Open the existing instance or stop it first.')
    runtime=data_path/'runtime.json'
    runtime.write_text(json.dumps({'pid':os.getpid(),'port':args.port,'host':args.host}))
    os.chmod(runtime,0o600)
    # Build imports the package normally; PyInstaller discovers it through this import.
    from server.app import app
    try:
        uvicorn.run(app,host=args.host,port=args.port,log_level='info',access_log=False)
    finally:
        runtime.unlink(missing_ok=True)
