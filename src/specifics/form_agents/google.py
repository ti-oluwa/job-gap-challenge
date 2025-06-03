import typing

from playwright.async_api import ElementHandle

from src.exceptions import AgentError
from src.utils import fuzzy_search_keys
from src.generics.form_agents.google import GoogleFormAgent, FormQuestionSchema
from src.specifics.schemas import has_years_of_experience, years_of_experience_to_range


class GoogleJobFormAgent(GoogleFormAgent):
    """
    A specialized Google Form agent for processing job applications for the Google Job Form
    given in the interview task.
    """

    name: str = "Google Job Form Agent"
    description: typing.Optional[str] = (
        "An agent for filling and submitting Google Forms specifically for job applications."
    )

    async def answer_question(
        self,
        question: ElementHandle,
        form_data: typing.Dict[str, typing.Any],
        schema: FormQuestionSchema,
    ) -> None:
        """
        Answer a question in the Google Form based on the question schema.

        :param question: The question element handle.
        :param form_data: A dictionary of form field names and values.
        :param schema: The schema of the question.
        """
        if not schema.label:
            if schema.options_selectors and len(schema.options_selectors) == 1:
                # Accept terms handling
                selector = next(iter(schema.options_selectors.values()))
                if option := await question.query_selector(selector):
                    await option.click()
                    return
            raise AgentError(
                "Could not resolve question answer. Schema is missing 'label'."
            )

        results = fuzzy_search_keys(
            form_data, schema.label.lower(), cutoff=0.4, count=1
        )
        value = next(iter(results.values()), None)
        if not value:
            raise AgentError(
                f"Required field '{schema.label}' is missing in form data."
            )

        if schema.type == "text":
            # Firstname, Lastname, Email, handling
            if not schema.input_selector:
                raise AgentError(
                    f"No input selector found for question '{schema.label}'."
                )
            if input_element := await question.query_selector(schema.input_selector):
                await input_element.fill(str(value))
            else:
                raise AgentError(
                    f"Input element not found for question '{schema.label}'."
                )

        elif schema.type == "radio":
            # Years of experience handling
            if not schema.options_selectors:
                raise AgentError(
                    f"No options found for radio question '{schema.label}'."
                )

            for option_label, selector in schema.options_selectors.items():
                required_yoe = years_of_experience_to_range(option_label)
                if has_years_of_experience(required_yoe, value):
                    if option := await question.query_selector(selector):
                        await option.click()
                        return
            else:
                first_option_selector = next(
                    iter(schema.options_selectors.values()), None
                )
                if first_option_selector:
                    if option := await question.query_selector(first_option_selector):
                        await option.click()
                        return
            raise AgentError(
                f"Could not find a matching option for '{schema.label}' with value '{value}'."
            )
        else:
            raise AgentError(f"Unsupported question type '{schema.type}'.")
