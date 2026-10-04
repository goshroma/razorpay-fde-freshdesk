class FreshdeskError(Exception):
    pass


class AuthenticationError(FreshdeskError):
    pass


class NotFoundError(FreshdeskError):
    pass


class InvalidRequestError(FreshdeskError):
    pass


class RateLimitError(FreshdeskError):
    pass
    