from ..common import BaseModule


class BaseFilter(BaseModule):
    def __call__(self, event):
        raise NotImplementedError
