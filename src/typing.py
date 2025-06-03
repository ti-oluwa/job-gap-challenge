import typing
from typing_extensions import ParamSpec
from pydantic import BaseModel


T = typing.TypeVar("T")
R = typing.TypeVar("R")
P = ParamSpec("P")

PydanticModel = typing.TypeVar("PydanticModel", bound=BaseModel)
PydanticModelco = typing.TypeVar("PydanticModelco", bound=BaseModel, covariant=True)
