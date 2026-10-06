"""Create a source-only Linux bundle from the pinned, patched official checkout."""
import argparse
import io
import subprocess
import tarfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
COMMIT = "ca9f014cb3ead157ca2ee6ce645658f5fb55138c"
parser = argparse.ArgumentParser()
parser.add_argument("--vendor", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
vendor = args.vendor.resolve()
revision = subprocess.check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"], text=True).strip()
if revision != COMMIT:
    raise SystemExit("Official checkout does not match the pinned revision")
subprocess.run(["git", "-C", str(vendor), "apply", "--reverse", "--check",
                str(PROJECT / "official-patches/registered-business-tools.patch")], check=True)

def source_only(info):
    parts = set(Path(info.name).parts)
    if parts & {".git", ".env", "__pycache__", ".venv", "node_modules"} or info.name.endswith(".pyc"):
        return None
    return info

with tarfile.open(args.output, "w:gz") as archive:
    for name in ("commerce", "official_tests", "tests", "official-patches", "deploy",
                 "run_official.py", "official.toml", "official-requirements.lock",
                 "official-requirements-linux.lock", "pytest.ini"):
        archive.add(PROJECT / name, arcname=name, filter=source_only)
    for name in ("packages", "pilot", "skills", "docker/examples", "README.md", "pyproject.toml", "LICENSE"):
        if (vendor / name).exists():
            archive.add(vendor / name, arcname="vendor/DB-GPT/" + name, filter=source_only)
    payload = (COMMIT + "\n").encode()
    info = tarfile.TarInfo("vendor/DB-GPT/UPSTREAM_COMMIT")
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))
print(f"Created source bundle: {args.output} ({args.output.stat().st_size} bytes)")
