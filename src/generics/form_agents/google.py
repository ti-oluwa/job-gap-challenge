import typing
import re
from aiofiles import open as aio_open
from pathlib import Path
from annotated_types import Ge, Le
from playwright.async_api import Page, ElementHandle

from src.exceptions import AgentError
from src.logging import logger


google_form_url_re = re.compile(
    r"^(https?://)?(docs|forms)\.google\.com/(forms|spreadsheets)/d/"
    r"([/a-zA-Z0-9_-]+)(/viewform|/edit)?(\?.*)?$",
    flags=re.IGNORECASE,
)


class FormQuestionSchema(typing.NamedTuple):
    """
    Schema for a Google Form question.
    """

    label: str
    type: typing.Literal[
        "text",
        "long_text",
        "radio",
        "checkbox",
        "multiple_choice",
        "date",
        "time",
    ] = "text"
    required: bool = False
    options_selectors: typing.Optional[typing.Dict[str, str]] = None
    input_selector: typing.Optional[str] = None


class GoogleFormAgent:
    name: str = "Google Form Agent"
    description: typing.Optional[str] = (
        "An agent for filling and submitting Google Forms."
    )

    async def check_url(self, url: str) -> bool:
        """
        Check if the URL is a valid Google Form URL.

        :param url: The URL to check.
        :return: True if the URL is a valid Google Form URL, False otherwise.
        """
        return bool(google_form_url_re.match(url))

    async def get_form(self, page: Page) -> ElementHandle:
        """
        Get the form element on the Google Form page.

        :param page: The page containing the form.
        :return: The form element handle.
        """
        form = await page.query_selector("form")
        if not form:
            raise AgentError("No form found on the page.")
        return form

    async def fill_form(
        self,
        form: ElementHandle,
        form_data: typing.Dict[str, typing.Any],
    ) -> None:
        """
        Fill the Google Form with the given data.

        :param form: The form element handle.
        :param form_data: A dictionary of form field names and values.
        """
        questions_container = await form.query_selector("div[role='list']")
        if not questions_container:
            raise AgentError("No questions found in the form.")

        questions = await questions_container.query_selector_all(
            "> div[role='listitem']"
        )
        if not questions:
            raise AgentError("No questions found in the form.")

        try:
            for question in questions:
                schema = await self.get_question_schema(question)
                await self.answer_question(question, form_data, schema)
        except Exception as exc:
            raise AgentError(exc, agent_name=self.name) from exc

    async def get_question_schema(
        self,
        question: ElementHandle,
    ) -> FormQuestionSchema:
        """
        Extract the question text and type from a Google Form question element.

        :param question: The question element handle.
        :return: A tuple containing the question text and type.
        """
        question_schema = await question.evaluate(
            """
            (question) => {
                const questionSchema = {
                    label: null,
                    type: "text",
                    required: false,
                    input_selector: null,
                    options_selectors: null
                };
                const labelElement = question.querySelector("div[jsaction]:first-child span:first-child");
                const requiredElement = question.querySelector("span[aria-label='Required question']");
                const inputElement = question.querySelector("input");
                const radioGroup = question.querySelector("div[role='radiogroup']")
                const listGroup = question.querySelector("div[role='list']");

                questionSchema["label"]= labelElement ? labelElement.textContent.trim() : null;
                questionSchema["required"] = requiredElement !== null;
                if (inputElement) {
                    const randomSuffix = Math.random().toString(36).substring(2, 15);
                    const selector = inputElement.getAttribute("form_input") || "google_form_input_" + randomSuffix;
                    inputElement.setAttribute("form_input", "google_form_input_" + randomSuffix);
                    questionSchema["input_selector"] = `input[form_input="${selector}"]`; 
                };
                if (radioGroup) {
                    questionSchema["type"] = "radio";
                    const options = Array.from(radioGroup.querySelectorAll("span[role='presentation'] label.docssharedWizToggleLabeledContainer"));
                    questionSchema["options_selectors"] = {};
                    options.forEach((option, index) => {
                        const label = option.textContent.trim() || `Option ${index + 1}`;
                        const randomSuffix = Math.random().toString(36).substring(2, 15);
                        const selector = `google_form_radio_${randomSuffix}_${index}`;
                        option.setAttribute("form_radio_label", selector);
                        questionSchema["options_selectors"][label] = `${option.tagName.toLowerCase()}[form_radio_label="${selector}"]`;
                    });
                };
                if (listGroup) {
                    questionSchema["type"] = listGroup.querySelector("div[role='checkbox']") ? "checkbox" : "multiple_choice";
                    const options = Array.from(listGroup.querySelectorAll("div[role='listitem'] label.docssharedWizToggleLabeledContainer"));
                    questionSchema["options_selectors"] = {};
                    options.forEach((option, index) => {
                        const label = option.textContent.trim() || `Option ${index + 1}`;
                        const randomSuffix = Math.random().toString(36).substring(2, 15);
                        const selector = `google_form_choice_${randomSuffix}_${index}`;
                        option.setAttribute("form_choice_label", selector);
                        questionSchema["options_selectors"][label] = `${option.tagName.toLowerCase()}[form_choice_label="${selector}"]`;
                    });
                };
                return questionSchema;
            }
            """
        )
        return FormQuestionSchema(**question_schema)

    async def answer_question(
        self,
        question: ElementHandle,
        form_data: typing.Dict[str, typing.Any],
        schema: "FormQuestionSchema",
    ) -> None:
        """
        Answer a question in the Google Form based on the question schema.
        :param question: The question element handle.
        :param form_data: A dictionary of form field names and values.
        :param schema: The schema of the question.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")

    async def submit_form(self, form: ElementHandle) -> None:
        """
        Submit the Google Form.

        :param form: The form element handle.
        """
        submit_button = await form.query_selector("div[role='button']")
        if not submit_button:
            raise AgentError("No submit button found in the Google Form.")
        await submit_button.click()

    async def confirm_submission(self, page: Page) -> bool:
        """
        Confirm the form submission if required.

        :param page: The page containing the form.
        :return: True if submission is confirmed, False otherwise.
        """
        await page.wait_for_load_state("networkidle")
        return "Your response has been recorded" in await page.content()

    async def take_screenshot(
        self,
        page: Page,
        path: typing.Union[str, Path],
        quality: typing.Optional[typing.Annotated[int, Ge(0), Le(100)]] = None,
        file_type: typing.Union[typing.Literal["jpeg", "png"], str] = "jpeg",
    ) -> None:
        """
        Take a screenshot of the submission confirmation page.

        :param page: The page containing the form submission confirmation.
        :param path: The path to save the screenshot.
        :param quality: Optional quality of the screenshot (0-100 for jpeg, should be ignored for png).
        :param file_type: The file type of the screenshot ('jpeg' or 'png').
        :raises AgentError: If the directory does not exist.
        """
        if file_type not in ["jpeg", "png"]:
            raise ValueError(
                f"Invalid screenshot type {file_type}. Supported types are 'jpeg' and 'png'."
            )

        file_type = typing.cast(typing.Literal["jpeg", "png"], file_type.lower())
        path = Path(path)
        if not path.parent.exists() or not path.parent.is_dir():
            raise ValueError(f"Directory {path.parent} does not exist.")
        if path.suffix not in [".jpeg", ".jpg", ".png"]:
            raise ValueError(
                f"Invalid file type {path.suffix}. Supported types are .jpeg, .jpg, and .png."
            )

        logger.info(f"Taking screenshot of page {page.url!r}.\n")
        screenshot = await page.screenshot(quality=quality, type=file_type)
        async with aio_open(path, "wb") as f:
            await f.write(screenshot)
        logger.debug(f"Screenshot saved to {path!r}.")
