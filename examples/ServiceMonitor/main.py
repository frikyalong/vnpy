import os
import sys
import datetime
import traceback
import pickle as pkl
import datetime
import yaml

from monitor.beat import MonitorBeat

def check_if_working_time():
    working_time_list = [
        # 开始小时，开始分钟，结束小时，结束分钟
        (8, 56, 15, 0),
        (20, 49, 23, 59),
        (0, 0, 2, 30),
    ]
    now = datetime.datetime.now().replace(second=0)

    trade_date = now - datetime.timedelta(hours=7)
    if 1 <= trade_date.isoweekday() <= 5:
        for start_hour, start_minute, end_hour, end_minute in working_time_list:
            start = now.replace(hour=start_hour, minute=start_minute)
            end = now.replace(hour=end_hour, minute=end_minute)
            if start <= now <= end:
                return True

    return False


def main(config_file, status_file=None):
    print(u'using :{}'.format(config_file))
    config = yaml.load(open(config_file))

    # 是否设置限定检查时间范围
    if config.get("working_time_only", True):
        if not check_if_working_time():
            return

    beat = None
    if status_file is not None:
        if os.path.exists(status_file):
            try:
                beat = pkl.load(open(status_file, "rb"))
            except:
                traceback.print_exc()

    if beat is None:
        beat = MonitorBeat(config)
    else:
        beat.config = config

    try:
        beat.beat()
    except:
        traceback.print_exc()

    if status_file is not None:
        pkl.dump(beat, open(status_file, "wb"))


if __name__ == "__main__":
    main(*sys.argv[1:])
