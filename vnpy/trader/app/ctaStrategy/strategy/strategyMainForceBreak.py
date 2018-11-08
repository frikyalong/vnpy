# encoding: UTF-8
from vnpy.trader.app.ctaStrategy.strategy.dingTalkSend import dingRobot
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate


class MainForceBreakStrategy(CtaTemplate):
    className = 'MainForceBreakStrategy'
    author = u'Gary Wang'
    barMinute = EMPTY_STRING  # K线当前的分钟

    # 变量列表，保存了变量的名称
    varList = {
        'isBigChange': False,
        'isContinuousRise': True,
        'isContinuousFall': True,
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

        self.MARKET = {
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

        self.lineM5RB = bar_class(self, self.onBarM5, self.MARKET['RB']['m5Setting'])
        self.lineM5RU = bar_class(self, self.onBarM5, self.MARKET['RU']['m5Setting'])
        self.lineM5M = bar_class(self, self.onBarM5, self.MARKET['M']['m5Setting'])
        self.lineM5I = bar_class(self, self.onBarM5, self.MARKET['I']['m5Setting'])
        self.lineM5CU = bar_class(self, self.onBarM5, self.MARKET['CU']['m5Setting'])
        self.lineM5NI = bar_class(self, self.onBarM5, self.MARKET['NI']['m5Setting'])
        self.lineM5HC = bar_class(self, self.onBarM5, self.MARKET['HC']['m5Setting'])
        self.lineM5Y = bar_class(self, self.onBarM5, self.MARKET['Y']['m5Setting'])
        self.lineM5JM = bar_class(self, self.onBarM5, self.MARKET['JM']['m5Setting'])
        self.lineM5CF = bar_class(self, self.onBarM5, self.MARKET['CF']['m5Setting'])
        self.lineM5ZN = bar_class(self, self.onBarM5, self.MARKET['ZN']['m5Setting'])
        self.lineM5SR = bar_class(self, self.onBarM5, self.MARKET['SR']['m5Setting'])

        self.lineM3RB = bar_class(self, self.onBarM3, self.MARKET['RB']['m3Setting'])
        self.lineM3RU = bar_class(self, self.onBarM3, self.MARKET['RU']['m3Setting'])
        self.lineM3M = bar_class(self, self.onBarM3, self.MARKET['M']['m3Setting'])
        self.lineM3I = bar_class(self, self.onBarM3, self.MARKET['I']['m3Setting'])
        self.lineM3CU = bar_class(self, self.onBarM3, self.MARKET['CU']['m3Setting'])
        self.lineM3NI = bar_class(self, self.onBarM3, self.MARKET['NI']['m3Setting'])
        self.lineM3HC = bar_class(self, self.onBarM3, self.MARKET['HC']['m3Setting'])
        self.lineM3Y = bar_class(self, self.onBarM3, self.MARKET['Y']['m3Setting'])
        self.lineM3JM = bar_class(self, self.onBarM3, self.MARKET['JM']['m3Setting'])
        self.lineM3CF = bar_class(self, self.onBarM3, self.MARKET['CF']['m3Setting'])
        self.lineM3ZN = bar_class(self, self.onBarM3, self.MARKET['ZN']['m3Setting'])
        self.lineM3SR = bar_class(self, self.onBarM3, self.MARKET['SR']['m3Setting'])

    def onInit(self):
        self.writeCtaLog(u'%s策略初始化' % self.name)
        self.putEvent()

    def onStart(self):
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    def onStop(self):
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

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

    def onBar(self, bar):
        # 发出状态更新事件
        self.putEvent()

    def onBarM5(self, m5Bar):
        print('*' * 20 + 'onBarM5 start' + '*' * 20)
        print('\n'.join(['%s:%s' % item for item in m5Bar.__dict__.items()]))

        curSymbol = m5Bar.symbol[:-4].upper()
        curVarList = self.MARKET[curSymbol]['varList']

        if curVarList['fiveMinKCount'] <= curVarList['fiveMinK']:
            self.writeCtaLog(u'top 5 bars')
            curVarList['fiveMinKCount'] += 1
            if curVarList['m5HighValue'] == 0:
                curVarList['m5HighValue'] = m5Bar.high

            if curVarList['m5LowValue'] == 0:
                curVarList['m5LowValue'] = m5Bar.low

            curVarList['m5HighValue'] = max(curVarList['m5HighValue'], m5Bar.high)
            curVarList['m5LowValue'] = min(curVarList['m5LowValue'], m5Bar.low)
            if curVarList['m5HighValue'] == m5Bar.high:
                curVarList['m5HighOpenInterest'] = m5Bar.openInterest
                curVarList['m5HighVolume'] = m5Bar.volume
                curVarList['m5HighChange'] = abs(m5Bar.high - m5Bar.low)

            if curVarList['m5LowValue'] == m5Bar.low:
                curVarList['m5LowOpenInterest'] = m5Bar.openInterest
                curVarList['m5LowChange'] = abs(m5Bar.high - m5Bar.low)

            if abs(curVarList['m5HighValue'] - curVarList['m5LowValue']) > m5Bar.close * 0.016:
                curVarList['isBigChange'] = True
            if m5Bar.close < m5Bar.open:
                curVarList['isContinuousRise'] = False
            else:
                curVarList['isContinuousFall'] = False

        if curVarList['fiveMinKCount'] >= 5:
            self.writeCtaLog(u'out of 5 bars')
            curVarList['m5PreVolume'] = curVarList['m5CurVolume']
            curVarList['m5CurVolume'] = m5Bar.volume
            curVarList['m5PreOpenInterest'] = curVarList['m5CurOpenInterest']
            curVarList['m5CurOpenInterest'] = m5Bar.openInterest
            curVarList['m5PreChangeArray'][0:4] = curVarList['m5PreChangeArray'][1:5]
            curVarList['m5PreChangeArray'][-1] = abs(m5Bar.high - m5Bar.low)

            self.MARKET[curSymbol]['varList'] = curVarList

            self.writeCtaCritical(u'{0}: 当前价{1}, 前25分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.format(
                m5Bar.symbol, m5Bar.close, curVarList['m5HighValue'], curVarList['m5HighVolume'], curVarList['m5HighOpenInterest'], m5Bar.volume, m5Bar.openInterest))

            if curVarList['isContinuousRise']:
                self.writeCtaLog(u'前5根k线持续上涨不开仓')
                return
            if curVarList['isContinuousRise']:
                self.writeCtaLog(u'前5根线持续下跌不开仓')
                return

            if curVarList['isBigChange']:
                self.writeCtaLog(u'前5根K线的高点和低点幅度适当，不能差距太大，如果差价太大，不能开仓，其中参考范围是振幅差距在1.6%以内')
                return

            changeSum = 0
            if m5Bar.close > curVarList['m5HighValue'] and (m5Bar.openInterest > curVarList['m5HighOpenInterest'] or m5Bar.openInterest > curVarList['m5PreOpenInterest']):
                self.writeCtaLog(u'价格突破前5根5分钟K线最高点,持仓量增加')
                if m5Bar.volume > curVarList['m5HighValue'] * 0.7 or m5Bar.volume > curVarList['m5PreVolume']:
                    self.writeCtaLog(u'成交量增加，成交量高于前面K线成交量或者成交量是高点K线的70%以上')
                    for item in curVarList['m5PreChangeArray']:
                        changeSum = changeSum + item
                    if abs(m5Bar.high - m5Bar.low) > (changeSum/5 * 1.2):
                        self.writeCtaLog(u'中阳线 这跟K线是近期震荡的几根K线的振幅的1.2倍以上')
                        ddRobot = dingRobot()
                        self.writeCtaLog(u'+--- send message')
                        ddRobot.postStart(u'{0}可以开多仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                      format(m5Bar.symbol, m5Bar.close, curVarList['m5HighValue'], curVarList['m5HighVolume'], curVarList['m5HighOpenInterest'], m5Bar.volume, m5Bar.openInterest))

            if m5Bar.close < curVarList['m5LowValue'] and (m5Bar.openInterest < curVarList['m5LowOpenInterest'] or m5Bar.openInterest < curVarList['m5PreOpenInterest']):
                self.writeCtaLog(u'价格突破前5根5分钟K线最低点,持仓量减少')
                if abs(m5Bar.high - m5Bar.low) < (changeSum / 5 * 1.2):
                    self.writeCtaLog(u'这跟K线是近期震荡的几根K线的振幅的1.2倍以下')
                    ddRobot = dingRobot()
                    self.writeCtaLog(u'+--- send message')
                    ddRobot.postStart(u'{0}可以开空仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                        format(m5Bar.symbol, m5Bar.close, curVarList['m5HighValue'], curVarList['m5HighVolume'], curVarList['m5HighOpenInterest'], m5Bar.volume, m5Bar.openInterest))

    def onBarM3(self, m3Bar):
        print('*' * 20 + 'onBarM3 start' + '*' * 20)
        print('\n'.join(['%s:%s' % item for item in m3Bar.__dict__.items()]))

        curSymbol = m3Bar.symbol[:-4].upper()
        curVarList = self.MARKET[curSymbol]['varList']

        if curVarList['threeMinKCount'] <= curVarList['threeMinK']:
            self.writeCtaLog(u'top 9 bars')
            curVarList['threeMinKCount'] += 1
            if curVarList['m3HighValue'] == 0:
                curVarList['m3HighValue'] = m3Bar.high

            if curVarList['m3LowValue'] == 0:
                curVarList['m3LowValue'] = m3Bar.low

            curVarList['m3HighValue'] = max(curVarList['m3HighValue'], m3Bar.high)
            curVarList['m3LowValue'] = min(curVarList['m3LowValue'], m3Bar.low)
            if curVarList['m3HighValue'] == m3Bar.high:
                curVarList['m3HighOpenInterest'] = m3Bar.openInterest
                curVarList['m3HighVolume'] = m3Bar.volume
                curVarList['m3HighChange'] = abs(m3Bar.high - m3Bar.low)

            if curVarList['m3LowValue'] == m3Bar.low:
                curVarList['m3LowOpenInterest'] = m3Bar.openInterest
                curVarList['m3LowChange'] = abs(m3Bar.high - m3Bar.low)

            if abs(curVarList['m3HighValue'] - curVarList['m3LowValue']) > m3Bar.close * 0.016:
                curVarList['isBigChange'] = True
            if m3Bar.close < m3Bar.open:
                curVarList['isContinuousRise'] = False
            else:
                curVarList['isContinuousFall'] = False

        if curVarList['fiveMinKCount'] >= 9:
            self.writeCtaLog(u'out of 9 bars')
            curVarList['m3PreVolume'] = curVarList['m3CurVolume']
            curVarList['m3CurVolume'] = m3Bar.volume
            curVarList['m3PreOpenInterest'] = curVarList['m3CurOpenInterest']
            curVarList['m3CurOpenInterest'] = m3Bar.openInterest
            curVarList['m3PreChangeArray'][0:4] = curVarList['m3PreChangeArray'][1:5]
            curVarList['m3PreChangeArray'][-1] = abs(m3Bar.high - m3Bar.low)

            self.MARKET[curSymbol]['varList'] = curVarList

            self.writeCtaCritical(u'{0}: 当前价{1}, 前27分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.format(
                m3Bar.symbol, m3Bar.close, curVarList['m3HighValue'], curVarList['m3HighVolume'],
                curVarList['m3HighOpenInterest'], m3Bar.volume, m3Bar.openInterest))

            if curVarList['isContinuousRise']:
                self.writeCtaLog(u'前9根k线持续上涨不开仓')
                return
            if curVarList['isContinuousRise']:
                self.writeCtaLog(u'前9根线持续下跌不开仓')
                return

            if curVarList['isBigChange']:
                self.writeCtaLog(u'前9根K线的高点和低点幅度适当，不能差距太大，如果差价太大，不能开仓，其中参考范围是振幅差距在1.6%以内')
                return

            changeSum = 0
            if m3Bar.close > curVarList['m3HighValue'] and (
                    m3Bar.openInterest > curVarList['m3HighOpenInterest'] or m3Bar.openInterest > curVarList['m3PreOpenInterest']):
                self.writeCtaLog(u'价格突破前9根3分钟K线最高点,持仓量增加')
                if m3Bar.volume > curVarList['m3HighValue'] * 0.7 or m3Bar.volume > curVarList['m3PreVolume']:
                    self.writeCtaLog(u'成交量增加，成交量高于前面K线成交量或者成交量是高点K线的70%以上')
                    for item in curVarList['m3PreChangeArray']:
                        changeSum = changeSum + item
                    if abs(m3Bar.high - m3Bar.low) > (changeSum / 9 * 1.2):
                        self.writeCtaLog(u'中阳线 这跟K线是近期震荡的几根K线的振幅的1.2倍以上')
                        ddRobot = dingRobot()
                        self.writeCtaLog(u'send message')
                        ddRobot.postStart(u'{0}可以开多仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                          format(m3Bar.symbol, m3Bar.close, curVarList['m3HighValue'],
                                                 curVarList['m3HighVolume'], curVarList['m3HighOpenInterest'],
                                                 m3Bar.volume, m3Bar.openInterest))

            if m3Bar.close < curVarList['m3LowValue'] and (
                    m3Bar.openInterest < curVarList['m3LowOpenInterest'] or m3Bar.openInterest < curVarList['m3PreOpenInterest']):
                self.writeCtaLog(u'价格突破前5根5分钟K线最低点,持仓量减少')
                if abs(m3Bar.high - m3Bar.low) < (changeSum / 9 * 1.2):
                    self.writeCtaLog(u'这跟K线是近期震荡的几根K线的振幅的1.2倍以下')
                    ddRobot = dingRobot()
                    self.writeCtaLog(u'+--- send message')
                    ddRobot.postStart(u'{0}可以开空仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                      format(m3Bar.symbol, m3Bar.close, curVarList['m3HighValue'],
                                             curVarList['m3HighVolume'], curVarList['m3HighOpenInterest'], m3Bar.volume,
                                             m3Bar.openInterest))

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()
