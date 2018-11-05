from .base import BaseFilter


class IfEqual(BaseFilter):
    def __call__(self, event):
        key = self.options["key"]
        value = self.options["value"]

        if key in event:
            if event[key] == value:
                yield event


class IfNotEqual(BaseFilter):
    def __call__(self, event):
        key = self.options["key"]
        value = self.options["value"]

        if key in event:
            if event[key] != value:
                yield event


class IfTrue(BaseFilter):
    def __call__(self, event):
        key = self.options["key"]

        if key in event:
            if event[key]:
                yield event


class IfNotTrue(BaseFilter):
    def __call__(self, event):
        key = self.options["key"]

        if key in event:
            if not event[key]:
                yield event
