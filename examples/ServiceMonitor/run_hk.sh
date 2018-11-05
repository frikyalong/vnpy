#!/bin/bash

PATH="/home/trade/anaconda3/envs/py35/bin:/home/trade/anaconda3/bin:/usr/local/anaconda3/bin:/usr/local/mongodb/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"

cd /home/trade/vnpy//ServiceMonitor
python main.py conf.hk/check_heartbeat.yaml >>log.txt 2>&1
python main.py conf.hk/check_alive.yaml >>log.txt 2>&1
python main.py conf.hk/check_err_log.yaml /tmp/status.pkl >>log.txt 2>&1

examples