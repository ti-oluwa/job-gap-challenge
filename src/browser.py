import typing
import re
import enum
from contextlib import asynccontextmanager

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    Page,
    Response,
    Route,
)
from src.utils import format_url
from src.logging import logger
from src.exceptions import NavigationError, PageNotFound


class BrowserType(enum.Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    MS_EDGE = "msedge"


DEFAULT_BROWSER_OPTIONS = {
    "headless": True,
    "slow_mo": 0,
    "timeout": 0,
    "devtools": False,
    "chromium_sandbox": False,
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--start-maximized",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-infobars",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--no-first-run",
        "--ignore-certificate-errors",
    ],
}

DEFAULT_BROWSER_CONTEXT_OPTIONS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
    "reduced_motion": "reduce",
    "accept_downloads": False,
    "locale": "en-US",
    "color_scheme": "light",
    "geolocation": None,
    "extra_http_headers": {
        "Upgrade-Insecure-Requests": "1",  # Force browser to upgrade HTTP requests to HTTPS
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    },
}


@asynccontextmanager
async def launch_browser(
    pw: Playwright,
    browser_type: BrowserType = BrowserType.CHROMIUM,
    **launch_options: typing.Any,
) -> typing.AsyncGenerator[BrowserContext, None]:
    """
    Async context manager that launches a browser, yields a browser context and closes the browser.

    :param pw: An asynchronous playwright instance.
    :param browser_type: The browser type to launch.
    :param launch_options: Additional options for launching the browser.
    :return: An async generator yielding a browser context.
    """
    context_options = launch_options.pop("context_options", {})
    context_options = {**DEFAULT_BROWSER_CONTEXT_OPTIONS, **context_options}
    launch_options = {**DEFAULT_BROWSER_OPTIONS, **launch_options}
    browser: Browser = await getattr(pw, BrowserType(browser_type).value).launch(
        **launch_options
    )
    try:
        context = await browser.new_context(**context_options)
        context.set_default_timeout(launch_options.get("timeout", 0))
        yield context
    finally:
        await browser.close()


async def navigate_to(
    url: str,
    page: Page,
    *,
    raise_notfound: bool = True,
    allow_redirects: bool = True,
    **goto_kwargs: typing.Any,
) -> typing.Optional[Response]:
    """
    Navigate to the given URL on the given page.

    :param url: The URL to navigate to.
    :param page: The page to navigate on.
    :param raise_notfound: If True, raises a `PageNotFound` exception if the page returns a 404 status code.
    :param allow_redirects: If True, allows redirects. Else, raises a `PageNotFound` exception if a redirect occurs.
    :param goto_kwargs: Additional keyword arguments to pass to `page.goto`.
    :return: The response object.
    """
    url = format_url(url)
    response = await page.goto(url, **goto_kwargs)
    if not response:
        raise NavigationError(
            f"Failed to navigate to {url}",
            url=url,
            nav_kwargs=goto_kwargs,
        )

    if raise_notfound and response.status == 404:
        raise PageNotFound(
            f"Page not found: {url}",
            url=url,
            nav_kwargs=goto_kwargs,
        )

    response_url = format_url(response.url)
    if url != response_url:
        logger.warning(f"Redirected to {response.url} from {url}")
        if not allow_redirects:
            raise NavigationError(
                f"Redirected to {response.url} from {url}",
                url=response_url,
                nav_kwargs=goto_kwargs,
                status_code=response.status,
            )
    return response


ad_keywords = {
    "ads",
    "googleadservices",
    "doubleclick",
    "googlesyndication",
    "googletagservices",
}
ads_resource_re = re.compile(rf"(?:{'|'.join(ad_keywords)})", flags=re.IGNORECASE)


@asynccontextmanager
async def new_page(
    browser_context: BrowserContext,
    blocked_resources: typing.Optional[typing.List[str]] = None,
) -> typing.AsyncGenerator[Page, None]:
    """
    Create a new page in the given browser context with optional resource blocking.

    :param browser_context: The browser context to create the page in.
    :param blocked_resources: A list of resource types to block (e.g., ["image", "stylesheet"]).
        If None, only ad-related resources will be blocked.
    :return: An async generator yielding the new page.
    """
    page = await browser_context.new_page()
    if blocked_resources:

        async def _route_interceptor(route: Route):
            if route.request.resource_type in blocked_resources:
                await route.abort()
            elif ads_resource_re.search(route.request.url):
                await route.abort()
            else:
                await route.continue_()
    else:

        async def _route_interceptor(route: Route):
            if ads_resource_re.search(route.request.url):
                await route.abort()
            else:
                await route.continue_()

    await page.route("**/*", _route_interceptor)

    try:
        yield page
    finally:
        try:
            await page.close()
        except Exception:
            # Page might have been closed already
            pass
