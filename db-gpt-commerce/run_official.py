"""Launch the complete upstream DB-GPT application using local configuration."""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("DBGPT_HOME", str(ROOT / "official-data"))
os.environ.setdefault("DBGPT_LANG", "zh")
load_dotenv(ROOT / ".env")
secret_path = ROOT / "official-data" / ".encryption-key"
secret_path.parent.mkdir(parents=True, exist_ok=True)
if not secret_path.exists():
    from cryptography.fernet import Fernet

    secret_path.write_text(Fernet.generate_key().decode(), encoding="utf-8")
os.environ["DBGPT_ENCRYPT_KEY"] = secret_path.read_text(encoding="utf-8").strip()
os.environ["ENCRYPT_KEY"] = os.environ["DBGPT_ENCRYPT_KEY"]
# Source checkout contains templates omitted by the upstream wheel build hook.
source_pilot = ROOT / "vendor/DB-GPT/pilot"
target_pilot = ROOT / "official-data/workspace/pilot"
for source in source_pilot.rglob("*"):
    target = target_pilot / source.relative_to(source_pilot)
    if source.is_file() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

if __name__ == "__main__":
    import dbgpt_app.dbgpt_server as server
    from commerce.official_integration import install

    install(server)
    server.run_webserver(str(ROOT / "official.toml"))
