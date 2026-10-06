"""A low-memory startup must defer, not break, actual code execution."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class CloudRuntimeTests(unittest.TestCase):
    def test_lazy_pool_still_initializes_on_first_execution(self):
        from commerce.cloud_runtime import configure_code_server
        from dbgpt.util.code.server import CodeServer, ServerState

        driver = MagicMock()
        driver.lyric.load_default_workers = AsyncMock()
        driver.exec = AsyncMock(return_value="executed")
        original_before = CodeServer.before_start
        original_after = CodeServer.async_after_start
        try:
            with patch.dict(os.environ, {"COMMERCE_LAZY_CODE_SERVER": "1"}), patch(
                "dbgpt.util.code.server.DefaultLyricDriver", return_value=driver
            ):
                self.assertTrue(configure_code_server())
                server = CodeServer()
                server.before_start()
                asyncio.run(server.async_after_start())
                self.assertEqual(server._state, ServerState.INIT)
                driver.start.assert_not_called()
                driver.lyric.load_default_workers.assert_not_called()

                async def exercise():
                    self.assertEqual(await server.exec("1+1", "python"), "executed")
                    self.assertEqual(await server.exec("2+2", "python"), "executed")
                asyncio.run(exercise())
                driver.start.assert_called_once()
                driver.lyric.load_default_workers.assert_awaited_once()
                server.before_stop()
                driver.stop.assert_called_once()
        finally:
            CodeServer.before_start = original_before
            CodeServer.async_after_start = original_after

    def test_normal_startup_is_unchanged_without_opt_in(self):
        from commerce.cloud_runtime import configure_code_server
        from dbgpt.util.code.server import CodeServer
        original = CodeServer.before_start
        with patch.dict(os.environ, {"COMMERCE_LAZY_CODE_SERVER": "0"}):
            self.assertFalse(configure_code_server())
        self.assertIs(CodeServer.before_start, original)
