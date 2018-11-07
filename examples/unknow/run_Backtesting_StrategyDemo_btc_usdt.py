# encoding: UTF-8

import sys, os, platform
global vnpy_root
p = str(platform.system())
if p == 'Windows':
    # windows下

    vnpy_root = os.path.abspath(os.path.join(os.getcwd()))
    # linux 下
else:
    vnpy_root = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))

sys.path.append(vnpy_root)
from datetime import datetime
import numpy as np
import pandas as pd
import talib as ta  # 科学计算库
#import statsmodels.api as sm  # 统计库
import matplotlib
import matplotlib.pyplot as plt
import math  # 数学计算相关

matplotlib.rcParams['figure.figsize'] = (20.0, 10.0)

from vnpy.trader.app.ctaStrategy.strategy.strategyDemo_DualEmaDtosc import StrategyDemo

data_path = os.path.abspath(os.path.join(os.getcwd(), 'data'))
if not os.path.exists(data_path):
    os.mkdir(data_path)

logs_path = os.path.abspath(os.path.join(os.getcwd(), 'logs'))
if not os.path.exists(logs_path):
    os.mkdir(logs_path)

strategy_settings = {}
test_settings = {}
test_settings['MinInterval'] = 5   # K线的分钟周期
test_settings['bar_interval'] = 1   # 回测数据的分钟周期
test_settings['TMinInterval'] = 1   # 回测数据的分钟周期


test_settings['name'] = 'SDemo_M{}_{}'.format(test_settings['MinInterval'], datetime.now().strftime('%m%d_%H%M'))

test_settings['strategy'] = StrategyDemo
test_settings['start_date'] = '20180101'
test_settings['initDays'] = 60
test_settings['end_date'] = '20180228'
test_settings['size'] = 1
test_settings['margin_rate'] = 1
test_settings['percentLimit'] = 100
test_settings['initCapital'] = 1000000
test_settings['rate']  = float(0.002)

test_settings['backtesting'] = True
test_settings['inputSS'] = 5
test_settings['is_7x24'] = True

test_settings['vtSymbol'] = 'btc_usd'
test_settings['shortSymbol'] = test_settings['vtSymbol']
test_settings['symbol'] = test_settings['vtSymbol']

test_settings['mode'] = 'bar'
test_settings['debug'] = True

test_settings['minDiff'] = 0.01
test_settings['min_trade_volume'] = 0.01
test_settings['min_notional'] = 0.01


if p == 'Windows':
    test_settings['bar_file'] = os.path.abspath(os.path.join(data_path,'okex_btc_usdt_20180101_20180808_1min.csv'))
else:
    test_settings['bar_file'] = '/home/tensorflow/bar_data/btc_usd_min5.csv'
test_settings['log_file'] = os.path.abspath(os.path.join(logs_path,'{}'.format(test_settings['name'])))

test_settings['report_file'] = os.path.abspath(os.path.join(logs_path,'{}.csv'.format(test_settings['name'])))

import json
from examples.CtaBacktesting.util_branch_testing import *
from vnpy.trader.vtEvent import EventEngine2
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine
from vnpy.trader.app.ctaStrategy.ctaBase import CtaBarData
import traceback

single_strategy_test(test_settings)