"""Opt-in cloud tuning for DB-GPT's eagerly started code-worker pool.

Commerce SQL and HTML reports do not use Lyric. Keep its normal on-demand
initialization in CodeServer.exec/get_code_server, but skip startup prewarming.
"""
import os


def configure_code_server() -> bool:
    if os.environ.get("COMMERCE_LAZY_CODE_SERVER") != "1":
        return False
    from dbgpt.util.code.server import CodeServer

    def before_start(self):
        # Leave state INIT. _ensure_initialized starts the driver on first use.
        pass

    async def async_after_start(self):
        pass

    CodeServer.before_start = before_start
    CodeServer.async_after_start = async_after_start
    return True
