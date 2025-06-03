from tracemalloc import start
import typing
import asyncio
import time
from dataclasses import dataclass
from playwright.async_api import BrowserContext

from src.typing import PydanticModel, PydanticModelco
from src.browser import new_page, navigate_to
from src.exceptions import ApplicationError
from src.logging import logger
from src.generics.form_agents import AsyncFormAgent


@dataclass(slots=True)
class ApplicationDetail(typing.Generic[PydanticModel]):
    """
    Details of an application made by an applicant.
    """

    url: str
    profile: PydanticModel
    status: typing.Literal["pending", "submitted", "confirmed"] = "pending"


async def process_application(
    browser_context: BrowserContext,
    application_url: str,
    form_agent: AsyncFormAgent,
    applicant_profile: PydanticModelco,
) -> ApplicationDetail[PydanticModelco]:
    """
    Process a single application for a given applicant profile.

    :param browser_context: The browser context to interact with.
    :param application_url: The URL of the application to navigate to.
    :param form_agent: The form agent to use for processing the application.
    :param applicant_profile: The applicant profile containing the data to fill in the application.
    """
    application = ApplicationDetail(
        url=application_url,
        profile=applicant_profile,
        status="pending",
    )

    async with new_page(browser_context) as page:
        start_time = time.monotonic()
        try:
            await navigate_to(application_url, page, raise_notfound=True)
            form = await form_agent.get_form(page)
            form_data = applicant_profile.model_dump(mode="json")
            await form_agent.fill_form(form, form_data)
            await form_agent.submit_form(form)
            application.status = "submitted"
            if await form_agent.confirm_submission(page):
                application.status = "confirmed"
        except ApplicationError as exc:
            logger.error(f"Error processing application for {applicant_profile!r}.\n")
            logger.exception(exc)
            application.status = "pending"
        end_time = time.monotonic()
        logger.info(
            f"Processed {applicant_profile!r} in {end_time - start_time:.2f} seconds.\n"
        )
    return application


@dataclass(slots=True, frozen=True)
class ApplicationInfo(typing.Generic[PydanticModel]):
    url: str
    profile: PydanticModel
    agent: AsyncFormAgent


async def process_applications(
    browser_context: BrowserContext,
    applications: typing.List[ApplicationInfo[PydanticModelco]],
) -> typing.List[ApplicationDetail[PydanticModelco]]:
    """
    Create multiple applications for a list of applicant profiles.

    :param browser_context: The browser context to interact with.
    :param applications: A list of application information to create applications for.
    :return: A list of ApplicationDetail objects.
    """
    tasks = [
        process_application(
            browser_context,
            application_info.url,
            application_info.agent,
            application_info.profile,
        )
        for application_info in applications
    ]
    return await asyncio.gather(*tasks)
