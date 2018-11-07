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

from vnpy.trader.app.ctaStrategy.strategy.strategyDemo_RBreaker import StrategyDemo_RBreaker

data_path = os.path.abspath(os.path.join(os.getcwd(), 'data'))
if not os.path.exists(data_path):
    os.mkdir(data_path)

logs_path = os.path.abspath(os.path.join(os.getcwd(), 'logs'))
if not os.path.exists(logs_path):
    os.mkdir(logs_path)

strategy_settings = {}
test_settings = {}

from vnpy.trader.app.ctaStrategy.ctaLineBar import PERIOD_HOUR,PERIOD_DAY
#test_settings['kline_name'] = 'D1'
#test_settings['kline_period'] = PERIOD_DAY
#test_settings['kline_len'] = 1   # 大周期K线配置


test_settings['kline_name'] = 'H12'
test_settings['kline_period'] = PERIOD_HOUR
test_settings['kline_len'] = 12   # 大周期K线配置

test_settings['name'] = 'S_RBreak_{}_{}'.format(test_settings['kline_name'], datetime.now().strftime('%m%d_%H%M'))

test_settings['strategy'] = StrategyDemo_RBreaker
test_settings['start_date'] = '20171101'
test_settings['initDays'] = 60
test_settings['end_date'] = '20180831'
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

test_settings['long_mult'] = 0.8
test_settings['short_mult'] = 0.8
test_settings['fixed_stoplose'] = 0.1


test_settings['bar_interval'] = 1   # 回测数据的分钟周期
test_settings['TMinInterval'] = 1   # 回测数据的分钟周期


if p == 'Windows':
    test_settings['bar_file'] = os.path.abspath(os.path.join(data_path,'okex_btc_usdt_20180101_20180808_1min.csv'))
else:
    test_settings['bar_file'] = '/home/trade/bar_data/btc_usd_min5.csv'
test_settings['log_file'] = os.path.abspath(os.path.join(logs_path,'{}'.format(test_settings['name'])))

test_settings['report_file'] = os.path.abspath(os.path.join(logs_path,'{}.csv'.format(test_settings['name'])))

# 回测正向策略和反向策略。
# 正向策略，取消加仓；反向策略，取消止损
import json
from examples.CtaBacktesting.util_branch_testing import *
from vnpy.trader.vtEvent import EventEngine2
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine
from vnpy.trader.app.ctaStrategy.ctaBase import CtaBarData
import traceback

single_strategy_test(test_settings)