import typing
import re
from typing_extensions import Annotated
from annotated_types import Ge, Le
import pydantic


yoe_pattern = re.compile(r"^\s*(?P<min>\d+)(?P<separator>[^\d\s])(?P<max>\d+)?.*$")


YearOfExperience: typing.TypeAlias = Annotated[int, Ge(0), Le(50)]
YearsOfExperience: typing.TypeAlias = typing.Tuple[
    typing.Optional[YearOfExperience], typing.Optional[YearOfExperience]
]


def years_of_experience_to_range(yoe: str) -> YearsOfExperience:
    """
    Convert a string representation of years of experience to a tuple of integers.

    The input string should be in the format "min-max" or "min separator max",
    where 'separator' can be any non-digit character (e.g., "1-5", "2 to 4", "3, 5", "5+").

    :param yoe: String representation of years of experience.
    :return: Tuple of integers representing the range of years.
    """
    match = yoe_pattern.match(yoe)
    if not match:
        return (None, None)

    min_years = int(match.group("min"))
    max_years = int(match.group("max")) if match.group("max") is not None else None
    if max_years is not None and min_years > max_years:
        raise ValueError(
            f"Invalid years of experience range: {yoe}. "
            "Minimum years cannot be greater than maximum years."
        )
    return (min_years, max_years)


def has_years_of_experience(
    required: YearsOfExperience, applicant: YearsOfExperience
) -> bool:
    """
    Check if the applicant's years of experience overlap with the required
    years of experience.

    :param required: Required years of experience range.
    :param applicant: Applicant years of experience range.
    :return: True if the ranges overlap, False otherwise.
    """
    req_min, req_max = required
    app_min, app_max = applicant

    if app_min is None or req_min is None:
        return False
    
    if req_max is None:
        return app_min >= req_min
    if app_max is None:
        return req_min <= app_min
    if app_max < req_min:
        return False
    if app_min > req_max:
        return False
    if app_min <= req_min and app_max >= req_max:
        return True
    if app_min >= req_min and app_max <= req_max:
        return True
    return app_min >= req_min


class ApplicantProfile(pydantic.BaseModel):
    """Job applicant profile model."""

    full_name: Annotated[
        str,
        pydantic.StringConstraints(
            strip_whitespace=True,
            strict=True,
            min_length=1,
            max_length=100,
        ),
    ] = pydantic.Field(
        description="Full name of the applicant",
        validation_alias=pydantic.AliasChoices("fullName", "name", "full_name"),
        alias_priority=1,
    )
    first_name: Annotated[
        str,
        pydantic.StringConstraints(
            strip_whitespace=True,
            strict=True,
        ),
    ] = pydantic.Field(
        default="",
        description="First name of the applicant",
        validation_alias=pydantic.AliasChoices("firstName", "givenName", "first_name"),
        alias_priority=2,
    )
    last_name: Annotated[
        str,
        pydantic.StringConstraints(
            strip_whitespace=True,
            strict=True,
        ),
    ] = pydantic.Field(
        default="",
        description="Last name of the applicant",
        validation_alias=pydantic.AliasChoices("lastName", "familyName", "last_name"),
        alias_priority=3,
    )
    email: pydantic.EmailStr = pydantic.Field(
        description="Email address of the applicant",
        validation_alias=pydantic.AliasChoices(
            "email", "contact_email", "email_address"
        ),
    )
    country: Annotated[
        str, pydantic.StringConstraints(strip_whitespace=True, to_upper=True)
    ] = pydantic.Field(
        description="Country of residence",
        validation_alias=pydantic.AliasChoices("country", "location", "residence"),
    )
    years_of_experience: YearsOfExperience = pydantic.Field(
        (0, 1),
        description="Years of professional experience",
        validation_alias="experience",
    )
    interests: typing.List[str] = pydantic.Field(
        default_factory=list,
        description="List of professional interests",
    )
    comments: typing.Optional[str] = pydantic.Field(
        default=None,
        description="Additional comments or notes from the applicant",
    )

    model_config = pydantic.ConfigDict(
        extra="allow",
    )

    @pydantic.model_validator(mode="after")
    def validate_profile(self) -> "ApplicantProfile":
        """
        Validate the applicant profile after initial parsing.

        Ensures that at least one of first_name or last_name is provided.
        """
        self.first_name, self.last_name = (
            self.full_name.split(maxsplit=1)
            if " " in self.full_name
            else (self.full_name, "")
        )
        return self

    @pydantic.field_validator("years_of_experience", mode="before")
    @classmethod
    def validate_years_of_experience(
        cls, value: typing.Union[str, YearsOfExperience]
    ) -> YearsOfExperience:
        """
        Validate and convert years of experience input to a tuple of integers.

        :param value: Input value for years of experience.
        :return: Tuple of integers representing the range of years.
        """
        if isinstance(value, str):
            return years_of_experience_to_range(value)
        return value
