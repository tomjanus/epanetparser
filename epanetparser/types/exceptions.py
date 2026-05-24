from .warnings import PywrParserWarning


class PywrParserException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.message})"


class PywrTypeValidationError(PywrParserException):
    desc_text = "[FAILURE]"

    def __init__(self, component, rule, exc, valuetext):
        self.component = component
        self.rule = rule
        self.exc = exc
        self.valuetext = valuetext

    def __str__(self):
        return f"{self.desc_text} {self.component} '{self.rule}' -> {self.exc}:\n          {self.valuetext}"

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.component}, {self.rule}, {self.exc})"

    def as_dict(self):
        return {
            "component": self.component,
            "rule": self.rule,
            "exception": str(self.exc),
            "value": self.valuetext
        }



class PywrTypeValidationErrorBundle(PywrParserException):
    def __init__(self, message, bundle):
        self.message = message
        self.bundle = bundle

    @property
    def errors(self):
        return [exc for exc in self.bundle if isinstance(exc, PywrParserException)]

    @property
    def warnings(self):
        return [exc for exc in self.bundle if isinstance(exc, PywrParserWarning)]


class PywrNetworkValidationError(PywrParserException):
    def __init__(self, message):
        super().__init__(message)
        self.component = "network"

    def as_dict(self):
        return {
            "component": self.component,
            "message": self.message
        }
