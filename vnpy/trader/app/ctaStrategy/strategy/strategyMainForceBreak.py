# encoding: UTF-8
import talib
import numpy as np

from vnpy.trader.app.ctaStrategy.strategy.dingTalkSend import dingRobot
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate


########################################################################
class MainForceBreakStrategy(CtaTemplate):
    className = 'MainForceBreakStrategy'
    author = u'Gary Wang'

    # 策略变量
    isBigChange = False
    isContinuousRise = True

    m5HighValue = 0
    m5HighOpenInterest = 0
    m5HighVolume = 0
    m5HighChange = 0

    m5LowValue = 0
    m5LowOpenInterest = 0
    m5LowVolume = 0
    m5LowChange = 0

    m5PreVolume = 0
    m5CurVolume = 0
    m5PreOpenInterest = 0
    m5CurOpenInterest = 0
    m5PreChangeArray = np.zeros(5)

    m3HighValue = 0
    m3HighOpenInterest = 0
    m3HighVolume = 0
    m3HighChange = 0

    m3ChangeArray = np.zeros(5)

    m3LowValue = 0
    m3LowOpenInterest = 0
    m3LowVolume = 0
    m3LowChange = 0

    m3PreVolume = 0
    m3CurVolume = 0
    m3PreOpenInterest = 0
    m3CurOpenInterest = 0
    m3PreChangeArray = np.zeros(5)

    fiveMinK = 5
    fiveMinKCount = 0
    threeMinK = 9
    threeMinKCount = 0

    bar = None  # K线对象
    barMinute = EMPTY_STRING  # K线当前的分钟


    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'atrLength',
                 'atrMaLength',
                 'rsiLength',
                 'rsiEntry',
                 'trailingPercent']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue',
               'atrMa',
               'rsiValue',
               'rsiBuy',
               'rsiSell']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MainForceBreakStrategy, self).__init__(ctaEngine, setting)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）
        # ddRobot = dingRobot()
        # ddRobot.postStart('可以下单啦， 666')

        # 创建5minsK线
        m5LineSetting = {}
        m5LineSetting['name'] = 'M5'
        m5LineSetting['period'] = 'minute'
        m5LineSetting['barTimeInterval'] = 5
        m5LineSetting['mode'] = CtaLineBar.TICK_MODE
        m5LineSetting['minDiff'] = 1
        # m5LineSetting['shortSymbol'] = 'aa[:-4].upper()' rb
        m5LineSetting['shortSymbol'] = 'RB'
        m5LineSetting['is_7x24'] = False
        bar_class = getCtaBarClass('minute')
        self.lineM5 = bar_class(self, self.onBarM5, m5LineSetting)

        # 创建3minsK线
        m3LineSetting = {}
        m3LineSetting['name'] = 'M3'
        m3LineSetting['period'] = 'minute'
        m3LineSetting['barTimeInterval'] = 3
        m3LineSetting['mode'] = CtaLineBar.TICK_MODE
        m3LineSetting['minDiff'] = 1
        m3LineSetting['shortSymbol'] = 'RB'
        m3LineSetting['is_7x24'] = False
        bar_class = getCtaBarClass('minute')
        self.lineM3 = bar_class(self, self.onBarM3, m3LineSetting)

    # ----------------------------------------------------------------------
    def onInit(self):
        self.writeCtaLog(u'%s策略初始化' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        # print('*' * 20 + 'onTick start' + '*' * 20)
        # print('\n'.join(['%s:%s' % item for item in tick.__dict__.items()]))
        # 计算K线
        if hasattr(tick, 'vtSymbol'):
            # print('*' * 20 + 'onTick start' + '*' * 20)
            # print('\n'.join(['%s:%s' % item for item in tick.__dict__.items()]))
            if tick.vtSymbol == 'rb1901':
                self.lineM5.onTick(copy.copy(tick))
                self.lineM3.onTick(copy.copy(tick))

        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice
            bar.openInterest = tick.openInterest

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        # 发出状态更新事件
        self.putEvent()

    def onBarM5(self, m5Bar):
        self.writeCtaLog(u'onBarM5')
        self.writeCtaLog(self.lineM5.displayLastBar())

        # if m5Bar.datetime.hour < 21:
        #     return
        if self.fiveMinKCount <= self.fiveMinK:
            self.writeCtaLog(u'top 5 bars')
            self.fiveMinKCount += 1
            if self.m5HighValue == 0:
                self.m5HighValue = m5Bar.high

            if self.m5LowValue == 0:
                self.m5LowValue = m5Bar.high

            self.m5HighValue = max(self.m5HighValue, m5Bar.high)
            if self.m5HighValue == m5Bar.high:
                self.m5HighOpenInterest = m5Bar.openInterest
                self.m5HighVolume = m5Bar.volume
                self.m5HighChange = abs(m5Bar.high - m5Bar.low)

            self.m5LowValue = min(self.m5HighValue, m5Bar.high)
            if self.m5LowValue == m5Bar.low:
                self.m5LowOpenInterest = m5Bar.openInterest
                self.m5LowVolume = m5Bar.volume
                self.m5LowChange = abs(m5Bar.high - m5Bar.low)
            if abs(m5Bar.high - m5Bar.low) > m5Bar.close * 0.016:
                self.isBigChange = True
            if m5Bar.close < m5Bar.open:
                self.isContinuousRise = False

        if len(self.lineM5.lineBar) > 5:
            self.writeCtaLog(u'out of 5 bars')
            self.m5PreVolume = self.m5CurVolume
            self.m5CurVolume = m5Bar.volume
            self.m5PreOpenInterest = self.m5CurOpenInterest
            self.m5CurOpenInterest = m5Bar.openInterest
            self.m5PreChangeArray[0:4] = self.m5PreChangeArray[1:4]
            self.m5PreChangeArray[-1] = abs(m5Bar.high - m5Bar.low)

            if self.isContinuousRise:
                self.writeCtaLog(u'+--- isContinuousRise')
                return

            if self.isBigChange:
                self.writeCtaLog(u'+--- isBigChange')
                return

            if m5Bar.close < self.m5HighValue:
                self.writeCtaLog(u'+--- 5Bar.close < self.m5HighValue')
                return

            if m5Bar.openInterest > self.m5HighOpenInterest or m5Bar.openInterest > self.m5PreOpenInterest:
                self.writeCtaLog(u'+--- m5Bar.openInterest > self.m5HighOpenInterest or m5Bar.openInterest > self.m5PreOpenIntereste')
                if m5Bar.volume > self.m5HighValue * 0.7 or m5Bar.volume > self.m5PreVolume:
                    self.writeCtaLog(u'+--- m5Bar.volume > self.m5HighValue * 0.7 or m5Bar.volume > self.m5PreVolume')
                    change = abs(m5Bar.high - m5Bar.low)
                    for item in self.m5PreChangeArray:
                        if change < item:
                            return
                    ddRobot = dingRobot()
                    self.writeCtaLog(u'+--- send message')
                    ddRobot.postStart(u'{0}可以开多仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                      format(m5Bar.symbol, m5Bar.close, self.m5HighValue, self.m5HighVolume, self.m5HighOpenInterest, m5Bar.volume, m5Bar.openInterest))

    def onBarM3(self, m3Bar):
        pass

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()
