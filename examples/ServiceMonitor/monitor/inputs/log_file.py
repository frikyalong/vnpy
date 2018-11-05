import os
import glob
import datetime
import json

from .. import logger as log
from .base import BaseInput


class LogFileInput(BaseInput):
    def __init__(self, options):
        super().__init__(options)

        self.last_file_pointer = {}

    def get_default_options(self):
        return {
            "multiline": False,
            "last_lines": 0,
            "key": "raw_content",
            "timestamp_format": "%Y-%m-%d"
        }

    def is_file_changed(self, path):
        new_size = os.path.getsize(path)
        old_size = self.get_last_read_position(path)

        if old_size == 0:
            return new_size > 0
        else:
            return new_size != old_size

    def get_last_read_position(self, path):
        return self.last_file_pointer.get(path, 0)

    def get_file_pointer(self, path):
        new_size = os.path.getsize(path)
        old_size = self.get_last_read_position(path)

        if new_size >= old_size:
            return old_size
        else:
            return max(new_size - 1024 * 256, 0)

    def set_file_pointer(self, path):
        self.last_file_pointer[path] = os.path.getsize(path)

    def get_new_lines(self, path):
        if self.options["last_lines"] > 0:
            # 如果是读取最后行模式
            last_lines = self.options["last_lines"]
        else:
            # 如果是读取最新改变内容模式
            if self.get_last_read_position(path) == 0:
                # 如果这个文件之前没有记录，则读取最后一行
                last_lines = 1
            else:
                last_lines = 0

        if last_lines > 0:
            last_pos = self.get_file_pointer(path)
            fp = open(path)
            fp.seek(last_pos)
            buf = fp.readlines()
            self.set_file_pointer(path)
            return buf[-last_lines:]
        else:
            if not self.is_file_changed(path):
                self.set_file_pointer(path)
                return []
            else:
                last_pos = self.get_file_pointer(path)
                fp = open(path)
                fp.seek(last_pos)
                buf = fp.readlines()
                self.set_file_pointer(path)
                return buf

    def __iter__(self):
        output_key = self.options["key"]
        file_list = self.get_file_list()

        for path in file_list:
            if os.path.exists(path):
                new_lines = self.get_new_lines(path)
                if len(new_lines) == 0:
                    continue

                if self.options["multiline"]:
                    new_lines = ["".join(new_lines)]

                for line in new_lines:
                    yield {
                        "file": path,
                        output_key: line,
                        "exists": True,
                    }
            else:
                if self.options.get("raise_if_not_exists", False):
                    yield {"file": path, "exists": False, output_key: ""}


class CTASettingJSONInput(LogFileInput):
    def get_file_list(self):
        timestamp = self.get_timestamp()
        json_path = self.options["path"]
        json_files = [
            os.path.abspath(fn) for fn in glob.glob(json_path, recursive=True)
        ]
        print(json_files)

        log_files = []
        for json_file in json_files:
            root_path, _ = os.path.split(json_file)
            log_path = os.path.join(root_path, "logs")

            settings = json.load(open(json_file, "r"))
            for item in settings:
                strategy_name = item["name"]
                log_file = os.path.join(
                    log_path, "{name}_{timestamp}.log".format(
                        name=strategy_name, timestamp=timestamp))
                print(log_file)
                log_files.append(log_file)

        return log_files
