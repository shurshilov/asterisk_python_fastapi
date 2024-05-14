class AuthError(Exception):
    """Auth error."""

    def __init__(self, detail: str) -> None:

        super().__init__()
        self.detail = detail


class BusinessError(Exception):
    """Business logic error."""

    def __init__(self, detail: str) -> None:

        super().__init__()
        self.detail = detail
