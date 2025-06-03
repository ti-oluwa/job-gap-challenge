import typing
from pathlib import Path
from annotated_types import Ge, Le

from playwright.async_api import Page, ElementHandle


__all__ = ["AsyncFormAgent", "AdvancedFormAgent"]

@typing.runtime_checkable
class AsyncFormAgent(typing.Protocol):
    """
    Protocol for an agent that can fill and submit forms.

    Should raise `AgentError` if an error occurs during form handling/processing.
    """

    name: str
    description: typing.Optional[str]

    async def check_url(self, url: str) -> bool:
        """
        Check if the URL is compatible with this form agent.

        :param url: The URL to check.
        :return: True if the URL is compatible, False otherwise.
        """
        raise NotImplementedError

    async def get_form(self, page: Page) -> ElementHandle:
        """
        Get the form element on the page.

        :param page: The page containing the form.
        :return: The form element handle.
        """
        raise NotImplementedError

    async def fill_form(
        self, form: ElementHandle, form_data: typing.Dict[str, typing.Any]
    ) -> None:
        """
        Fill the form with the given data.

        :param form: The form element handle.
        :param form_data: A dictionary of form field names and values.
        """
        raise NotImplementedError

    async def submit_form(self, form: ElementHandle) -> None:
        """
        Submit the form on the page.

        :param form: The form element handle.
        :return: The response after submitting the form.
        """
        raise NotImplementedError

    async def confirm_submission(self, page: Page) -> bool:
        """
        Confirm the form submission if required.

        :param page: The page containing the form.
        :return: True if submission is confirmed, False otherwise.
        """
        raise NotImplementedError


@typing.runtime_checkable
class AdvancedFormAgent(AsyncFormAgent, typing.Protocol):
    """
    An advanced form agent that can handle more complex form interactions.
    This is an extension of the basic AsyncFormAgent protocol.
    """

    async def screenshot_submission(
        self,
        page: Page,
        path: typing.Union[str, Path],
        quality: typing.Annotated[int, Ge(0), Le(100)] = 100,
        type_: typing.Literal["jpeg", "png"] = "jpeg",
    ) -> None:
        """
        Take a screenshot of the submission confirmation page.

        :param page: The page containing the form submission confirmation.
        :param path: The path to save the screenshot.
        :param quality: The quality of the screenshot (0-100).
        :param type_: The type of the screenshot ('jpeg' or 'png').
        :raises AgentError: If the directory does not exist.
        """
        raise NotImplementedError
