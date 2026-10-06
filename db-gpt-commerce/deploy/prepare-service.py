#!/usr/bin/env python3
"""Prepare an isolated local-only DB-GPT service; run with the DeerFlow Python as root.
Does not alter DeerFlow config or publish a network port.
"""
from pathlib import Path
import os, subprocess
from dotenv import dotenv_values
import yaml

app=Path('/opt/dbgpt-commerce')
state=Path('/var/lib/dbgpt-commerce')
config=Path('/etc/dbgpt-commerce')
if subprocess.run(['id','dbgpt'],capture_output=True).returncode:
    subprocess.run(['useradd','--system','--home-dir',str(state),'--shell','/usr/sbin/nologin','dbgpt'],check=True)
state.mkdir(exist_ok=True)
config.mkdir(mode=0o700,exist_ok=True)
for name in ('official-data','data','artifacts','logs','cache'):
    target=state/name
    target.mkdir(exist_ok=True)
    link=app/name
    if not link.exists(): link.symlink_to(target, target_is_directory=True)
    elif not link.is_symlink(): raise RuntimeError(f'Refusing to replace existing {link}')
subprocess.run(['chown','-R','dbgpt:dbgpt',str(state)],check=True)
models=yaml.safe_load(Path('/opt/deerflow/config.yaml').read_text())['models']
model=next(m for m in models if m['name']=='deepseek-flash')
secret=dotenv_values('/etc/deerflow/model.env')['DEEPSEEK_API_KEY']
values={
 'OPENAI_API_KEY':secret,
 'OPENAI_BASE_URL':model['api_base'],
 'OPENAI_MODEL':model['model'],
 'DBGPT_HOME':str(state/'official-data'),
 'HOME':str(state),
 'PYTHONUNBUFFERED':'1',
 'PYTHONUTF8':'1',
 'TOKENIZERS_PARALLELISM':'false',
 'OMP_NUM_THREADS':'1',
 'OPENBLAS_NUM_THREADS':'1',
 'MPLCONFIGDIR':str(state/'cache/matplotlib'),
 'TIKTOKEN_CACHE_DIR':str(state/'cache/tiktoken'),
 'COMMERCE_LAZY_CODE_SERVER':'1',
}
# Values are simple service env fields; never output or include them in a bundle.
if any('\n' in v or '\r' in v or '"' in v for v in values.values()):
    raise ValueError('Unsupported environment value')
env=config/'model.env'
fd=os.open(env,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as f: f.write(''.join(f'{k}="{v}"\n' for k,v in values.items()))
os.chmod(env,0o600)
unit='''[Unit]
Description=DB-GPT commerce analysis (official UI)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
User=dbgpt
Group=dbgpt
WorkingDirectory=/opt/dbgpt-commerce
EnvironmentFile=/etc/dbgpt-commerce/model.env
ExecStart=/opt/dbgpt-commerce/.official-venv/bin/python /opt/dbgpt-commerce/run_official.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=45
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
RestrictSUIDSGID=true
CapabilityBoundingSet=
MemoryMax=700M
MemorySwapMax=512M
CPUQuota=100%
CPUWeight=50
TasksMax=128

[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/dbgpt-commerce.service').write_text(unit)
subprocess.run(['systemctl','daemon-reload'],check=True)
print('Prepared local-only service and private model configuration.')
