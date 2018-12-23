# encoding: UTF-8

import sys
import json
sys.path.append('..')
from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_INT, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN,OFFSET_CLOSE,OFFSET_CLOSETODAY,OFFSET_CLOSEYESTERDAY, STATUS_CANCELLED
from vnpy.trader.app.ctaStrategy.ctaPolicy import *
from vnpy.trader.app.ctaStrategy.ctaPosition import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.data.shcifco.vnshcifco import *
from vnpy.trader.utils import *


class StrategyMonitor(CtaTemplate):
    className = 'StrategyMonitor'
    author = u'Gary'
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    ma = 40                    # 平均波动周期 MA Length

    def __init__(self, ctaEngine, setting=None):
        """Constructor"""
        super(Strategy_TripleMa, self).__init__(ctaEngine, setting)

        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('minDiff')

        # 增加监控变量项目
        self.varList.append('pos')              # 仓位
        self.varList.append('entrust')          # 是否正在委托

        self.curDateTime = None                 # 当前Tick时间
        self.curTick = None                     # 最新的tick
        self.lastOrderTime = None               # 上一次委托时间
        self.cancelSeconds = 60                 # 撤单时间(秒)

        # 定义日内的交易窗口
        self.openWindow = False                 # 开市窗口
        self.tradeWindow = False                # 交易窗口
        self.closeWindow = False                # 收市平仓窗口

        self.inited = False                     # 是否完成了策略初始化
        self.backtesting = False                # 是否回测
        self.lineM5 = None                      # 5分钟K线

        if setting:
            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M5 K线
            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'            # k线名称
            lineM5Setting['barTimeInterval'] = 60*5  # K线的Bar时长
            lineM5Setting['inputMa1Len'] = 10        # 第1条均线
            lineM5Setting['inputMa2Len'] = 20        # 第2条均线
            lineM5Setting['inputMa3Len'] = 120       # 第3条均线
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            self.lineM5 = CtaLineBar(self, self.onBarM5, lineM5Setting)

            try:
                mode = setting['mode']
                if mode != EMPTY_STRING:
                    self.lineM5.setMode(setting['mode'])
            except KeyError:
                self.lineM5.setMode(self.lineM5.TICK_MODE)

        self.onInit()