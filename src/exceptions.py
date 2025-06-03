import typing


class ApplicationError(Exception):
    """Base class for all application-related exceptions."""

    pass


class NavigationError(ApplicationError):
    """Exception raised when navigation fails."""

    def __init__(
        self,
        message: typing.Optional[typing.Union[str, Exception]] = None,
        url: typing.Optional[str] = None,
        nav_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
        status_code: typing.Optional[int] = None,
        *args: typing.Any,
    ) -> None:
        message = message or "Navigation error occurred"
        super().__init__(message, *args)
        self.url = url
        self.nav_kwargs = nav_kwargs
        self.status_code = status_code


class PageNotFound(NavigationError):
    """Exception raised when a page is not found (HTTP 404)."""

    def __init__(
        self,
        message: typing.Optional[typing.Union[str, Exception]] = None,
        url: typing.Optional[str] = None,
        nav_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
        *args: typing.Any,
    ) -> None:
        message = message or "Page not found"
        super().__init__(
            message, url=url, nav_kwargs=nav_kwargs, status_code=404, *args
        )


class AgentError(ApplicationError):
    """Exception raised when an agent encounters an error."""

    def __init__(
        self,
        message: typing.Optional[typing.Union[str, Exception]] = None,
        agent_name: typing.Optional[str] = None,
        error_code: typing.Optional[int] = None,
        *args: typing.Any,
    ) -> None:
        message = message or "Agent error occurred"
        super().__init__(message, *args)
        self.agent_name = agent_name
        self.error_code = error_code

