import typing
import asyncio
from pathlib import Path
from dataclasses import dataclass
from playwright.async_api import BrowserContext

from src.typing import PydanticModel, PydanticModelco
from src.browser import new_page, navigate_to
from src.exceptions import ApplicationError
from src.logging import logger
from src.utils import timeit
from src.generics.form_agents import AsyncFormAgent, AdvancedFormAgent


@dataclass(slots=True, frozen=True)
class ApplicationInfo(typing.Generic[PydanticModel]):
    url: str
    """A URL to the application page."""
    profile: PydanticModel
    """A Pydantic model representing the applicant's profile."""
    agent: AsyncFormAgent
    """An agent that handles the application form processing"""
    take_screenshot: bool = False
    """Whether to take a screenshot of the confirmation page."""
    screenshot_file_path: typing.Optional[Path] = None
    """Optional path to file where the screenshot will be saved."""


@dataclass(slots=True)
class ApplicationDetail(typing.Generic[PydanticModel]):
    """
    Details of an application made by/on-behalf-of an applicant.
    """

    url: str
    """A URL to the application page."""
    info: ApplicationInfo[PydanticModel]
    """Information about the application, including the profile and agent."""
    status: typing.Literal["pending", "submitted", "confirmed"] = "pending"
    """The status of the application."""
    confirmation_screenshot: typing.Optional[Path] = None
    """Optional path to the screenshot (file) of the confirmation page after submission."""


async def process_application(
    browser_context: BrowserContext,
    application_info: ApplicationInfo[PydanticModelco],
) -> ApplicationDetail[PydanticModelco]:
    """
    Process a single application for a given applicant profile.

    :param browser_context: The browser context to interact with.
    :param application_info: Information about the application to process.
    :return: An ApplicationDetail object containing the application details.
    """
    application_url = application_info.url
    applicant_profile = application_info.profile
    form_agent = application_info.agent
    take_screenshot = application_info.take_screenshot
    screenshot_file_path = application_info.screenshot_file_path
    application_detail = ApplicationDetail(
        url=application_url,
        info=application_info,
        status="pending",
        confirmation_screenshot=None,
    )

    with timeit(f"Application for {applicant_profile!r}"):
        async with new_page(
            browser_context, blocked_resources=["image", "media"]
        ) as page:
            try:
                await navigate_to(application_url, page, raise_notfound=True)
                form = await form_agent.get_form(page)
                form_data = applicant_profile.model_dump(mode="json")
                await form_agent.fill_form(form, form_data)
                await form_agent.submit_form(form)
                application_detail.status = "submitted"

                if await form_agent.confirm_submission(page):
                    application_detail.status = "confirmed"
                    if take_screenshot and isinstance(form_agent, AdvancedFormAgent):
                        screenshot_file_path = (
                            screenshot_file_path
                            or Path.cwd() / f"{applicant_profile}_confirmation.jpeg"
                        )
                        file_type = screenshot_file_path.suffix.removeprefix(
                            "."
                        ).lower()
                        await form_agent.take_screenshot(
                            page,
                            path=screenshot_file_path,
                            file_type=file_type,
                            quality=None if file_type == "png" else 100,
                        )
                        application_detail.confirmation_screenshot = (
                            screenshot_file_path
                        )

            except ApplicationError as exc:
                logger.error(
                    f"Error processing application for {applicant_profile!r}.\n"
                )
                logger.exception(exc)
                # application.status = "pending"

    return application_detail


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
        process_application(browser_context, application_info)
        for application_info in applications
    ]
    return await asyncio.gather(*tasks)
