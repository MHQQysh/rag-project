"""Regression checks for the official tool bridge and report-file handoff."""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DBGPT_HOME", str(ROOT / "official-data"))


class OfficialBridgeTests(unittest.TestCase):
    def test_registered_tool_dispatch(self):
        from dbgpt._private.config import Config
        from dbgpt.agent.resource.manage import get_resource_manager, initialize_resource
        from dbgpt.agent.resource.tool.base import tool
        from dbgpt.component import SystemApp
        from dbgpt_app.openapi.api_v1.tools.execute_tool import make_execute_tool

        @tool(description="Check a registered domain tool can be dispatched by name.")
        def bridge_probe(value: int) -> str:
            return str(value * 2)

        app = SystemApp()
        Config().SYSTEM_APP = app
        initialize_resource(app)
        get_resource_manager(app).register_resource(resource_instance=bridge_probe)
        result = asyncio.run(make_execute_tool({})(tool_name="bridge_probe", args={"value": 21}))
        self.assertEqual(json.loads(result)["chunks"][0]["content"], "42")

    def test_report_file_keeps_exact_numbers(self):
        from dbgpt_app.openapi.api_v1.tools.html_interpreter import make_html_interpreter

        with tempfile.TemporaryDirectory(prefix="commerce-report-") as folder:
            source = Path(folder) / "report.html"
            html = "<!doctype html><html><body>自营客单价 ¥300.00 → ¥280.00；贡献 -44,800 元。</body></html>"
            source.write_text(html, encoding="utf-8")
            result = asyncio.run(make_html_interpreter({}, folder)(file_path=str(source), title="核验报告"))
            rendered = next(c for c in json.loads(result)["chunks"] if c["output_type"] == "html")
            self.assertEqual(rendered["content"], html)


if __name__ == "__main__":
    unittest.main()
