import os
import glob
import datetime

from ..common import BaseModule


class BaseInput(BaseModule):
    def __iter__(self):
        raise NotImplementedError

    def get_file_list(self):
        path = self.options["path"]

        values = {"timestamp": self.get_timestamp()}
        path = path.format(**values)

        all_files = glob.glob(path, recursive=True)
        return [os.path.abspath(fn) for fn in all_files]

    def get_timestamp(self):
        fmt = self.options["timestamp_format"]
        dt = datetime.datetime.now()
        return dt.strftime(fmt)