import datetime

from .base import BaseFilter


class Timeout(BaseFilter):
    def get_default_options(self):
        return {
            "key": "timestamp",
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
        }

    def __call__(self, event):
        key = self.options["key"]
        fmt = self.options["timestamp_format"]

        if key in event:
            last_dt = datetime.datetime.strptime(event[key], fmt)
            curr_dt = datetime.datetime.now()

            delta = curr_dt - last_dt
            print(delta)
            if delta.total_seconds() > self.options["timeout"]:
                yield {
                    "msg": "超时",
                    "last_timestamp": last_dt.strftime(fmt),
                    "current_timestamp": curr_dt.strftime(fmt),
                }
