import os

import psutil

from .. import logger as log
from .base import BaseInput


class PIDFileInput(BaseInput):
    def get_default_options(self):
        return {"timestamp_format": "%Y-%m-%d"}

    def __iter__(self):
        for pid_file in self.get_file_list():
            status = {"file": pid_file}
            if not os.path.exists(pid_file):
                msg = "找不到PID文件({pid_file})".format(pid_file=pid_file)
                status.update({"msg": msg, "pid_file_not_exists": True})
                yield status
                continue
            else:
                status["pid_file_not_exists"] = False

            try:
                buf = open(pid_file).read()
                pid = int(buf)
            except ValueError:
                msg = "PID文件内容不正确: {}".format(buf)
                status.update({"msg": msg, "pid_file_not_correct": True})
                yield status
                continue
            else:
                status["pid_file_not_correct"] = False

            try:
                proc = psutil.Process(pid)
            except psutil._exceptions.NoSuchProcess:
                msg = "找不到进程(PID={pid})".format(pid=pid)
                status.update({"msg": msg, "process_not_exists": True})
                yield status
                continue
            else:
                status["process_not_exists"] = False

            status["msg"] = "进程存在(PID={pid})".format(pid=pid)
            status["process_exists"] = True
            yield status
