import asyncio
import sys


def selector_event_loop() -> asyncio.AbstractEventLoop:
    """Loop compatible with psycopg async (ProactorEventLoop is not)."""
    return asyncio.SelectorEventLoop()


def use_selector_event_loop() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
