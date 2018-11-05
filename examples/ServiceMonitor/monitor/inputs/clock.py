import os
import datetime

from .. import logger as log
from .base import BaseInput


class ClockInput(BaseInput):
    def get_default_options(self):
        return {
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
        }

    def __iter__(self):
        now = datetime.datetime.now()

        yield {
            "timestamp": now.strftime(self.options["timestamp_format"]),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.isoweekday(),
        }
