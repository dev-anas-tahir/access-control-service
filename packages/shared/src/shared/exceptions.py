class ShopBaseException(Exception):
    pass


class AuthenticationError(ShopBaseException):
    pass


class AuthorizationError(ShopBaseException):
    pass


class NotFoundError(ShopBaseException):
    pass


class ValidationError(ShopBaseException):
    pass


class ConflictError(ShopBaseException):
    pass
