import asyncio
from collections.abc import Sequence
from email.policy import default
import re
import typing
import click
import orjson
import yaml
from pathlib import Path
from more_itertools import batched
from itertools import chain
from playwright.async_api import async_playwright, BrowserContext

from src.utils import cleanup_tasks_on_exit
from src.browser import launch_browser, BrowserType
from src.exceptions import AgentError
from src.logging import logger
from src.generics.applications import (
    ApplicationDetail,
    process_applications,
    ApplicationInfo,
)
from src.generics.form_agents import AsyncFormAgent, AdvancedFormAgent
from src.specifics.form_agents.google import GoogleJobFormAgent
from src.specifics.schemas import ApplicantProfile


FORM_AGENTS: typing.Dict[str, AsyncFormAgent] = {
    "google": GoogleJobFormAgent(),
}


async def process_application_data(
    application_url: str,
    form_agent: AsyncFormAgent,
    application_data: typing.Iterable[typing.Dict[str, typing.Any]],
    batch_size: int = 10,
    browser_type: BrowserType = BrowserType.CHROMIUM,
    browser_options: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
    retry_limit: int = 2,
    retry_backoff: float = 3.0,
) -> typing.Tuple[typing.List[ApplicationDetail], typing.List[ApplicationDetail]]:
    """
    Process job application data using a specified form agent.

    :param application_url: The URL of the job application form.
    :param form_agent: The form agent to use for processing applications.
    :param application_data: Iterable of dictionaries containing applicants' data.
    :param batch_size: Number of applications to process in a single batch.
    :param browser_type: The type of browser to use for processing applications.
    :param browser_options: Optional dictionary of options for the `playwright` browser type.
    :param retry_limit: Maximum number of retries for processing each application.
    :return: A list of ApplicationDetail objects containing the results of the processing.
    """
    if not await form_agent.check_url(application_url):
        raise AgentError(
            f"Invalid or incompatible URL for {form_agent.name!r}.",
            agent_name=form_agent.name,
        )

    async with (
        cleanup_tasks_on_exit(),
        async_playwright() as pw,
        launch_browser(
            pw,
            browser_type=browser_type,
            **(browser_options or {}),
        ) as browser_context,
    ):
        results: typing.List[ApplicationDetail[ApplicantProfile]] = []
        for batch in batched(application_data, n=batch_size):
            applications = [
                ApplicationInfo(
                    url=application_url,
                    profile=ApplicantProfile.model_validate(applicant_data),
                    agent=form_agent,
                )
                for applicant_data in batch
            ]
            results.extend(await process_applications(browser_context, applications))

        confirmed_applications, unconfirmed_applications = sort_applications(results)
        back_off = retry_backoff
        retries = 0
        while retries < retry_limit and unconfirmed_applications:
            retries += 1
            back_off *= retries
            logger.info(
                f"Retrying {len(unconfirmed_applications)} applications in {back_off} seconds...\n"
            )
            await asyncio.sleep(back_off)

            confirmed, unconfirmed_applications = await retry_unconfirmed_applications(
                unconfirmed_applications,
                form_agent=form_agent,
                browser_context=browser_context,
                batch_size=batch_size,
            )
            confirmed_applications.extend(confirmed)

    return confirmed_applications, unconfirmed_applications


def sort_applications(
    application_details: typing.Iterable[ApplicationDetail[ApplicantProfile]],
) -> typing.Tuple[
    typing.List[ApplicationDetail[ApplicantProfile]],
    typing.List[ApplicationDetail[ApplicantProfile]],
]:
    """
    Sort applications into confirmed and unconfirmed lists.

    :param application_details: Iterable of ApplicationDetail objects to sort.
    :return: A tuple containing two lists: confirmed applications and unconfirmed applications.
    """
    confirmed, unconfirmed = [], []
    for application_detail in application_details:
        if application_detail.status == "confirmed":
            confirmed.append(application_detail)
        else:
            unconfirmed.append(application_detail)
    return confirmed, unconfirmed


async def retry_unconfirmed_applications(
    application_details: typing.Iterable[ApplicationDetail[ApplicantProfile]],
    form_agent: AsyncFormAgent,
    browser_context: BrowserContext,
    batch_size: int = 10,
) -> typing.Tuple[
    typing.List[ApplicationDetail[ApplicantProfile]],
    typing.List[ApplicationDetail[ApplicantProfile]],
]:
    """
    Retry processing job applications with the specified parameters.

    :param application_details: Iterable of ApplicationDetail objects to retry.
    :param form_agent: The form agent to use for processing applications.
    :param browser_context: The browser context to interact with.
    :param batch_size: Number of applications to process in a single batch.
    :return: A tuple containing two lists: confirmed applications and unconfirmed applications.
    """
    results = []
    for batch in batched(application_details, n=batch_size):
        applications = [
            ApplicationInfo(
                url=application_detail.url,
                profile=application_detail.profile,
                agent=form_agent,
            )
            for application_detail in batch
        ]
        results.extend(await process_applications(browser_context, applications))
    return sort_applications(results)


@click.command(
    help="Process job application data using a specified form agent.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.argument("application_url", type=str)
@click.argument(
    "data_file",
    type=click.File("rb", lazy=True),
)
@click.option(
    "agent_name",
    "--agent",
    type=click.Choice(FORM_AGENTS.keys()),
    required=False,
    default=None,
)
@click.option(
    "--batch-size",
    type=int,
    default=10,
    help="Number of job applications to process in a single batch.",
)
@click.option(
    "--browser-type",
    type=click.Choice([bt.value for bt in BrowserType]),
    default=BrowserType.CHROMIUM.value,
    help="The `playwright` browser type to use for processing applications.",
)
@click.option(
    "options_file",
    "--browser-options",
    type=click.File("rb", lazy=True),
    help="Path to YAML configuration file containing `playwright` browser options",
)
@click.option(
    "retry_limit",
    "--retry",
    type=int,
    default=0,
    help="Number of times to retry processing unconfirmed applications.",
)
@click.option(
    "--screenshots",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, writable=True),
    help="If provided, application confirmation/submission screenshots would be taken. "
    "Path to directory where screenshots should be stored.",
    required=False,
    default=None,
)
def main(
    application_url: str,
    data_file: typing.BinaryIO,
    agent_name: typing.Optional[str] = None,
    batch_size: int = 10,
    browser_type: BrowserType = BrowserType.CHROMIUM,
    options_file: typing.Optional[typing.BinaryIO] = None,
    retry_limit: int = 0,
    screenshots: typing.Optional[Path] = None,
) -> None:
    """
    Process job applications using a specified form agent.

    :param application_url: The URL of the job application form.
    :param agent_name: The name of the form agent to use.
    :param data_file: Path to a JSON file containing applicants' data.
    :param batch_size: Number of applications to process in a single batch.
    :param browser_type: The type of browser to use for processing applications.
    :param options_file: Optional YAML configuration file for browser options.
    :param retry_limit: Maximum number of retries for processing each application.
    :param screenshots: Path to directory where screenshots should be stored.
    """
    if not agent_name:
        form_agent = next(iter(FORM_AGENTS.values()), None)
        if not form_agent:
            raise ValueError("No registered form agents available.")
    else:
        form_agent = FORM_AGENTS[agent_name]

    if screenshots and not isinstance(form_agent, AdvancedFormAgent):
        raise ValueError(
            f"Agent '{agent_name}' does not support screenshots. "
            "Please use an agent that supports advanced features."
        )

    application_data = orjson.loads(data_file.read())
    if not isinstance(application_data, Sequence):
        raise ValueError("Application data must be a sequence of objects.")

    browser_options: typing.Optional[typing.Dict[str, typing.Any]] = (
        yaml.safe_load(options_file) if options_file else None
    )
    results = asyncio.run(
        process_application_data(
            application_url,
            form_agent=form_agent,
            application_data=application_data,
            batch_size=batch_size,
            browser_type=BrowserType(browser_type),
            browser_options=browser_options,
            retry_limit=retry_limit,
        )
    )
    display_application_results(results)


def display_application_results(
    results: typing.Tuple[
        typing.List[ApplicationDetail[ApplicantProfile]],
        typing.List[ApplicationDetail[ApplicantProfile]],
    ],
) -> None:
    confirmed, unconfirmed = results
    click.echo(
        click.style(
            f"{len(confirmed) + len(unconfirmed)} applications processed!",
            fg="white",
            bold=True,
        )
    )
    for application in chain(confirmed, unconfirmed):
        click.echo(
            click.style(
                f"Application for {application.profile.full_name} "
                f"({application.profile.email}) - Status: {application.status}\n",
                fg="blue"
                if application.status == "confirmed"
                else "yellow"
                if application.status == "submitted"
                else "red",
            )
        )
