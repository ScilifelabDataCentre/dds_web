class AuthenticationError(Exception):
    """Errors due to user authentication."""

    def __str__(self):
        return f"{self.args[0]}"


class DatabaseInconsistencyError(Exception):
    """Errors due to database inconcistencies."""

    def __str__(self):
        return f"{self.args[0]}"
