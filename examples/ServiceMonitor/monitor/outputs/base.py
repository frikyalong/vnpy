from ..common import BaseModule
import json


class BaseOutput(BaseModule):
    def render(self, event):
        if "format" in self.options:
            fmt = self.options["format"]
            return fmt.format(**event)
        else:
            return json.dumps(event)

    def __call__(self, event):
        raise NotImplementedError
