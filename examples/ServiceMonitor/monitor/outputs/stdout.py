from .base import BaseOutput


class StdOut(BaseOutput):
    def __call__(self, event):
        s = self.render(event)
        print("触发事件: {}".format(s))
