class SlovarKeyError(KeyError):
    pass


class SlovarValueError(ValueError):
    pass


def set_exceptions(key_error, value_error):
    global SlovarKeyError, SlovarValueError
    SlovarKeyError = key_error
    SlovarValueError = value_error
