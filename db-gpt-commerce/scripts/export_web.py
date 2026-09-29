"""Export only newly generated synthetic data, never a user's runtime database."""
import json
import sqlite3
import sys
import tempfile
import shutil
import gc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from commerce.data import seed_database, reference_rows, periods, digest, SCHEMA
from commerce.analysis import decompose

destination = ROOT / 'web' / 'assets'
destination.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    path = seed_database(Path(temporary) / 'synthetic.sqlite')
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        raw = {table: [dict(r) for r in con.execute(f'SELECT * FROM {table}')]
               for table in ('orders', 'refunds', 'channels')}
    fixtures = []
    for month in ('2026-08-16', '2026-09-16'):
        for region in ('华东', '华北'):
            params = dict(periods(month), region=region)
            rows = reference_rows(path, params)
            fixtures.append(dict(params=params, rows=rows, analysis=decompose(rows)))
    shutil.copyfile(path, destination / 'synthetic.sqlite')
    manifest = dict(synthetic=True, seed=20260916, database_sha256=digest(path),
                    coverage_start='2026-06-01', coverage_end_exclusive='2026-09-01',
                    timezone='Asia/Shanghai', schema=SCHEMA)
    for name, value in [('raw.json', raw), ('manifest.json', manifest), ('expected.json', fixtures)]:
        (destination / name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    con.close()
    gc.collect()  # sqlite connection context managers commit but do not close connections.
print('Exported fresh synthetic SQLite, raw rows, metadata and four Python comparison fixtures.')
