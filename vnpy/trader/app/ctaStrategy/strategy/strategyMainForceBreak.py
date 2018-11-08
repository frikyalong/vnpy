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
    varList = {
        'isBigChange': False,
        'isContinuousRise': True,
        'm5HighValue': 0,
        'm5HighOpenInterest': 0,
        'm5HighVolume': 0,
        'm5HighChange': 0,
        'm5LowValue': 0,
        'm5LowOpenInterest': 0,
        'm5LowVolume': 0,
        'm5LowChange': 0,
        'm5PreVolume': 0,
        'm5CurVolume': 0,
        'm5PreOpenInterest': 0,
        'm5CurOpenInterest': 0,
        'm5PreChangeArray': np.zeros(5),
        'm3HighValue': 0,
        'm3HighOpenInterest': 0,
        'm3HighVolume': 0,
        'm3HighChange': 0,
        'm3ChangeArray': np.zeros(5),
        'm3LowValue': 0,
        'm3LowOpenInterest': 0,
        'm3LowVolume': 0,
        'm3LowChange': 0,
        'm3PreVolume': 0,
        'm3CurVolume': 0,
        'm3PreOpenInterest': 0,
        'm3CurOpenInterest': 0,
        'm3PreChangeArray': np.zeros(5),
        'fiveMinK': 5,
        'fiveMinKCount': 0,
        'threeMinK': 9,
        'threeMinKCount': 0,
    }

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
        m5LineSettingBase = {}
        m5LineSettingBase['name'] = 'M5'
        m5LineSettingBase['period'] = 'minute'
        m5LineSettingBase['barTimeInterval'] = 5
        m5LineSettingBase['mode'] = CtaLineBar.TICK_MODE
        m5LineSettingBase['minDiff'] = 1
        m5LineSettingBase['is_7x24'] = False
        bar_class = getCtaBarClass('minute')

        m5RBLineSetting = copy.copy(m5LineSettingBase)
        m5RBLineSetting['shortSymbol'] = 'RB'
        m5RBLineSetting['name'] = 'M5RB'
        m3RBLineSetting = copy.copy(m5RBLineSetting)
        m3RBLineSetting['name'] = 'M3RB'
        m3RBLineSetting['barTimeInterval'] = 3

        m5RULineSetting = copy.copy(m5LineSettingBase)
        m5RULineSetting['shortSymbol'] = 'RU'
        m5RULineSetting['name'] = 'M5RU'
        m3RULineSetting = copy.copy(m5RULineSetting)
        m3RULineSetting['name'] = 'M3RU'
        m3RULineSetting['barTimeInterval'] = 3

        m5MLineSetting = copy.copy(m5LineSettingBase)
        m5MLineSetting['shortSymbol'] = 'M'
        m5MLineSetting['name'] = 'M5M'
        m3MLineSetting = copy.copy(m5MLineSetting)
        m3MLineSetting['name'] = 'M3M'
        m3MLineSetting['barTimeInterval'] = 3

        m5ILineSetting = copy.copy(m5LineSettingBase)
        m5ILineSetting['shortSymbol'] = 'I'
        m5ILineSetting['name'] = 'M5I'
        m3ILineSetting = copy.copy(m5ILineSetting)
        m3ILineSetting['name'] = 'M3I'
        m3ILineSetting['barTimeInterval'] = 3

        m5CULineSetting = copy.copy(m5LineSettingBase)
        m5CULineSetting['shortSymbol'] = 'CU'
        m5CULineSetting['name'] = 'M5CU'
        m3CULineSetting = copy.copy(m5CULineSetting)
        m3CULineSetting['name'] = 'M3CU'
        m3CULineSetting['barTimeInterval'] = 3

        m5NILineSetting = copy.copy(m5LineSettingBase)
        m5NILineSetting['shortSymbol'] = 'NI'
        m5NILineSetting['name'] = 'M5NI'
        m3NILineSetting = copy.copy(m5NILineSetting)
        m3NILineSetting['name'] = 'M3NI'
        m3NILineSetting['barTimeInterval'] = 3

        m5HCLineSetting = copy.copy(m5LineSettingBase)
        m5HCLineSetting['shortSymbol'] = 'HC'
        m5HCLineSetting['name'] = 'M5HC'
        m3HCLineSetting = copy.copy(m5HCLineSetting)
        m3HCLineSetting['name'] = 'M3HC'
        m3HCLineSetting['barTimeInterval'] = 3

        m5YLineSetting = copy.copy(m5LineSettingBase)
        m5YLineSetting['shortSymbol'] = 'Y'
        m5YLineSetting['name'] = 'M5Y'
        m3YLineSetting = copy.copy(m5YLineSetting)
        m3YLineSetting['name'] = 'M3Y'
        m3YLineSetting['barTimeInterval'] = 3

        m5JMLineSetting = copy.copy(m5LineSettingBase)
        m5JMLineSetting['shortSymbol'] = 'JM'
        m5JMLineSetting['name'] = 'M5JM'
        m3JMLineSetting = copy.copy(m5JMLineSetting)
        m3JMLineSetting['name'] = 'M3JM'
        m3JMLineSetting['barTimeInterval'] = 3

        m5CFLineSetting = copy.copy(m5LineSettingBase)
        m5CFLineSetting['shortSymbol'] = 'CF'
        m5CFLineSetting['name'] = 'M5CF'
        m3CFLineSetting = copy.copy(m5CFLineSetting)
        m3CFLineSetting['name'] = 'M3CF'
        m3CFLineSetting['barTimeInterval'] = 3

        m5ZNLineSetting = copy.copy(m5LineSettingBase)
        m5ZNLineSetting['shortSymbol'] = 'ZN'
        m5ZNLineSetting['name'] = 'M5ZN'
        m3ZNLineSetting = copy.copy(m5ZNLineSetting)
        m3ZNLineSetting['name'] = 'M3ZN'
        m3ZNLineSetting['barTimeInterval'] = 3

        m5SRLineSetting = copy.copy(m5LineSettingBase)
        m5SRLineSetting['shortSymbol'] = 'SR'
        m5SRLineSetting['name'] = 'M5SR'
        m3SRLineSetting = copy.copy(m5SRLineSetting)
        m3SRLineSetting['name'] = 'M3SR'
        m3SRLineSetting['barTimeInterval'] = 3

        MARKET = {
            'RB': {'name': 'RB', 'm5Setting': m5RBLineSetting, 'm3Setting': m5RBLineSetting, 'varList': copy.copy(self.varList)},
            'RU': {'name': 'RU', 'm5Setting': m5RULineSetting, 'm3Setting': m5RULineSetting, 'varList': copy.copy(self.varList)},
            'M': {'name': 'M', 'm5Setting': m5MLineSetting, 'm3Setting': m5MLineSetting, 'varList': copy.copy(self.varList)},
            'I': {'name': 'I', 'm5Setting': m5ILineSetting, 'm3Setting': m5ILineSetting, 'varList': copy.copy(self.varList)},
            'CU': {'name': 'CU', 'm5Setting': m5CULineSetting, 'm3Setting': m5CULineSetting, 'varList': copy.copy(self.varList)},
            'NI': {'name': 'NI', 'm5Setting': m5NILineSetting, 'm3Setting': m5NILineSetting, 'varList': copy.copy(self.varList)},
            'HC': {'name': 'HC', 'm5Setting': m5HCLineSetting, 'm3Setting': m5HCLineSetting, 'varList': copy.copy(self.varList)},
            'Y': {'name': 'Y', 'm5Setting': m5YLineSetting, 'm3Setting': m5YLineSetting, 'varList': copy.copy(self.varList)},
            'JM': {'name': 'JM', 'm5Setting': m5CFLineSetting, 'm3Setting': m5CFLineSetting, 'varList': copy.copy(self.varList)},
            'CF': {'name': 'CF', 'm5Setting': m5RBLineSetting, 'm3Setting': m5RBLineSetting, 'varList': copy.copy(self.varList)},
            'ZN': {'name': 'ZN', 'm5Setting': m5ZNLineSetting, 'm3Setting': m5ZNLineSetting, 'varList': copy.copy(self.varList)},
            'SR': {'name': 'SR', 'm5Setting': m5SRLineSetting, 'm3Setting': m5SRLineSetting, 'varList': copy.copy(self.varList)},
        }

        self.lineM5RB = bar_class(self, self.onBarM5, MARKET['RB']['m5Setting'])
        self.lineM5RU = bar_class(self, self.onBarM5, MARKET['RU']['m5Setting'])
        self.lineM5M = bar_class(self, self.onBarM5, MARKET['M']['m5Setting'])
        self.lineM5I = bar_class(self, self.onBarM5, MARKET['I']['m5Setting'])
        self.lineM5CU = bar_class(self, self.onBarM5, MARKET['CU']['m5Setting'])
        self.lineM5NI = bar_class(self, self.onBarM5, MARKET['NI']['m5Setting'])
        self.lineM5HC = bar_class(self, self.onBarM5, MARKET['HC']['m5Setting'])
        self.lineM5Y = bar_class(self, self.onBarM5, MARKET['Y']['m5Setting'])
        self.lineM5JM = bar_class(self, self.onBarM5, MARKET['JM']['m5Setting'])
        self.lineM5CF = bar_class(self, self.onBarM5, MARKET['CF']['m5Setting'])
        self.lineM5ZN = bar_class(self, self.onBarM5, MARKET['ZN']['m5Setting'])
        self.lineM5SR = bar_class(self, self.onBarM5, MARKET['SR']['m5Setting'])

        self.lineM3RB = bar_class(self, self.onBarM3, MARKET['RB']['m3Setting'])
        self.lineM3RU = bar_class(self, self.onBarM3, MARKET['RU']['m3Setting'])
        self.lineM3M = bar_class(self, self.onBarM3, MARKET['M']['m3Setting'])
        self.lineM3I = bar_class(self, self.onBarM3, MARKET['I']['m3Setting'])
        self.lineM3CU = bar_class(self, self.onBarM3, MARKET['CU']['m3Setting'])
        self.lineM3NI = bar_class(self, self.onBarM3, MARKET['NI']['m3Setting'])
        self.lineM3HC = bar_class(self, self.onBarM3, MARKET['HC']['m3Setting'])
        self.lineM3Y = bar_class(self, self.onBarM3, MARKET['Y']['m3Setting'])
        self.lineM3JM = bar_class(self, self.onBarM3, MARKET['JM']['m3Setting'])
        self.lineM3CF = bar_class(self, self.onBarM3, MARKET['CF']['m3Setting'])
        self.lineM3ZN = bar_class(self, self.onBarM3, MARKET['ZN']['m3Setting'])
        self.lineM3SR = bar_class(self, self.onBarM3, MARKET['SR']['m3Setting'])

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
                self.lineM5RB.onTick(copy.copy(tick))
                self.lineM3RB.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'ru1901':
                self.lineM5RU.onTick(copy.copy(tick))
                self.lineM3RU.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'm1901':
                self.lineM5M.onTick(copy.copy(tick))
                self.lineM3M.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'i1901':
                self.lineM5I.onTick(copy.copy(tick))
                self.lineM3I.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'cu1901':
                self.lineM5CU.onTick(copy.copy(tick))
                self.lineM3CU.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'ni1901':
                self.lineM5NI.onTick(copy.copy(tick))
                self.lineM3NI.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'hc1901':
                self.lineM5HC.onTick(copy.copy(tick))
                self.lineM3HC.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'y1901':
                self.lineM5Y.onTick(copy.copy(tick))
                self.lineM3Y.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'jm1901':
                self.lineM5JM.onTick(copy.copy(tick))
                self.lineM3JM.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'cf1901':
                self.lineM5CF.onTick(copy.copy(tick))
                self.lineM3CF.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'zn1901':
                self.lineM5ZN.onTick(copy.copy(tick))
                self.lineM3ZN.onTick(copy.copy(tick))
            elif tick.vtSymbol == 'sr1901':
                self.lineM5SR.onTick(copy.copy(tick))
                self.lineM3SR.onTick(copy.copy(tick))



    # ----------------------------------------------------------------------
    def onBar(self, bar):
        # 发出状态更新事件
        self.putEvent()

    def onBarM5(self, m5Bar):
        print('*' * 20 + 'onTick start' + '*' * 20)
        print('\n'.join(['%s:%s' % item for item in m5Bar.__dict__.items()]))
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
            self.m5PreChangeArray[0:4] = self.m5PreChangeArray[1:5]
            self.m5PreChangeArray[-1] = abs(m5Bar.high - m5Bar.low)

            self.writeCtaCritical(u'{0}: 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.format(
                m5Bar.symbol, m5Bar.close, self.m5HighValue, self.m5HighVolume, self.m5HighOpenInterest, m5Bar.volume, m5Bar.openInterest))
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
