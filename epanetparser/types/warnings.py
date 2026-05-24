class PywrParserWarning(Warning):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.message})"


class PywrTypeValidationWarning(PywrParserWarning):

    desc_text = "[WARNING]"

    def __init__(self, component, warning, exc, valuetext):
        self.component = component
        self.warning = warning
        self.exc = exc
        self.valuetext = valuetext

    def __str__(self):
        return f"{self.desc_text} {self.component} '{self.warning}' -> {self.exc}:\n          {self.valuetext}"

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.component}, {self.warning}, {self.exc})"

    def as_dict(self):
        return {
            "component": self.component,
            "rule": self.warning,
            "exception": str(self.exc),
            "value": self.valuetext
        }


class PywrNameWarning(PywrParserWarning):
    def __init__(self, message, component):
        super().__init__(message)
