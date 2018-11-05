import re
from .. import logger as log
from .base import BaseFilter


class RegexParser(BaseFilter):
    def __call__(self, event):
        key = self.options["key"]

        if key in event:
            content = event[key]

            pattern = re.compile(self.options["pattern"])
            if pattern.search(content) is None:
                log.error(self.options["pattern"])
                log.error("正则表达式无法匹配: {}".format(content))

            for item in pattern.finditer(content):
                yield item.groupdict()
