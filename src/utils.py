import typing
import functools
import asyncio
import difflib

from contextlib import asynccontextmanager
from urllib.parse import urlparse

from src.logging import logger
from src.typing import R, P


def fuzzy_search_keys(
    mapping: typing.Mapping[str, typing.Any],
    query: str,
    cutoff: float = 0.6,
    count: int = 5,
) -> typing.Dict[str, typing.Any]:
    """
    Fuzzy search keys in a mapping.

    This function uses difflib to find close matches to the query string
    in the keys of the mapping. It returns a dictionary containing
    the keys that match the query, along with their corresponding values.

    :param mapping: A mapping (dictionary) to search in.
    :param query: The query string to search for.
    :param cutoff: The minimum similarity ratio for a match (default is 0.6).
    :param count: The maximum number of matches to return (default is 5).
    :return: A dictionary containing the matching keys and their values.
    """
    possibilities = [key.lower() for key in mapping.keys()]
    matches = difflib.get_close_matches(query, possibilities, cutoff=cutoff, n=count)
    if not matches:
        return {}
    return {k: mapping[k] for k in matches}


async def _all_tasks_except_current() -> typing.List[asyncio.Task]:
    """
    Returns all tasks except the current task.

    This can be used to cancel all tasks except the current task.
    """
    return [task for task in asyncio.all_tasks() if task != asyncio.current_task()]


async def _cancel_tasks(
    tasks: typing.Optional[typing.Sequence[asyncio.Task]] = None,
) -> None:
    """
    Helper function to cancel tasks and await them.

    This can be used to ensure all tasks are cancelled and awaited,
    on process exit.

    :param tasks: A list of tasks to cancel. If not provided, all tasks except the current task will be cancelled.
    :return: None
    """
    tasks = tasks or await _all_tasks_except_current()
    active_tasks = [t for t in tasks if not (t.done() or t.cancelled())]

    if not active_tasks:
        return

    # Gather all active tasks and cancel them
    gather = asyncio.gather(*active_tasks)
    gather.cancel()

    try:
        await asyncio.wait_for(gather, timeout=0.001)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass


@asynccontextmanager
async def cleanup_tasks_on_exit(
    tasks: typing.Optional[typing.List[asyncio.Task]] = None,
):
    """
    Cleanup all asyncio tasks on exit.

    :param tasks: A list of tasks to cancel. If not provided, all tasks except the current task will be cancelled.
    """
    try:
        yield
    finally:
        logger.info("Cleaning up active tasks...")
        await _cancel_tasks(tasks)


def to_async(func: typing.Callable[P, R]) -> typing.Callable[P, typing.Awaitable[R]]:
    """
    Adapt a synchronous function to an asynchronous function.
    """

    @functools.wraps(func)
    async def async_executor(*args: P.args, **kwargs: P.kwargs) -> R:
        loop = asyncio.get_running_loop()

        def _run() -> R:
            return func(*args, **kwargs)

        return await loop.run_in_executor(None, _run)

    return async_executor


def format_url(url_like: str) -> str:
    """
    Converts a URL-like string to a valid URL.

    :param url_like: A string that represents a URL
    :return: A properly formatted URL string
    """
    parsed_url = urlparse(url_like)

    scheme = f"{parsed_url.scheme}://" if parsed_url.scheme else "http://"
    netloc = parsed_url.netloc if parsed_url.netloc else ""
    path = parsed_url.path.replace("//", "/") if parsed_url.path else ""
    query = f"?{parsed_url.query}" if parsed_url.query else ""
    fragment = f"#{parsed_url.fragment}" if parsed_url.fragment else ""

    return f"{scheme}{netloc}{path}{query}{fragment}"
