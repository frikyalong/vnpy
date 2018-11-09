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
        'bufferSize': 10,
        'isBigSwing': False,
        'isContinuousRise': True,
        'isContinuousFall': True,
        'm5HighValue': 0,
        'm5HighOpenInterest': 0,
        'm5HighVolume': 0,
        'm5HighSwing': 0,
        'm5LowValue': 0,
        'm5LowOpenInterest': 0,
        'm5LowVolume': 0,
        'm5LowSwing': 0,
        'm5PreVolume': 0,
        'm5CurVolume': 0,
        'm5PreOpenInterest': 0,
        'm5CurOpenInterest': 0,
        'm5PreSwingArray': np.zeros(10),
        'm5PreVolumeArray': np.zeros(10),
        'm5PreOpenInterestArray': np.zeros(10),
        'm5MaxRecordedKline': 5,
        'm5RecordedKline': 0,
        'm3HighValue': 0,
        'm3HighOpenInterest': 0,
        'm3HighVolume': 0,
        'm3HighSwing': 0,
        'm3LowValue': 0,
        'm3LowOpenInterest': 0,
        'm3LowVolume': 0,
        'm3LowSwing': 0,
        'm3PreVolume': 0,
        'm3CurVolume': 0,
        'm3PreOpenInterest': 0,
        'm3CurOpenInterest': 0,
        'm3PreSwingArray': np.zeros(10),
        'm3MaxRecordedKline': 9,
        'm3RecordedKline': 0,
    }

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MainForceBreakStrategy, self).__init__(ctaEngine, setting)
        bar_class = getCtaBarClass('minute')

        m5LineSettingBase = {}
        m5LineSettingBase['period'] = 'minute'
        m5LineSettingBase['barTimeInterval'] = 5
        m5LineSettingBase['mode'] = CtaLineBar.TICK_MODE

        m3LineSettingBase = {}
        m3LineSettingBase['period'] = 'minute'
        m3LineSettingBase['barTimeInterval'] = 3
        m3LineSettingBase['mode'] = CtaLineBar.TICK_MODE

        # 螺纹RB
        m5RBLineSetting = copy.copy(m5LineSettingBase)
        m5RBLineSetting['shortSymbol'] = 'RB'
        m5RBLineSetting['name'] = 'M5RB'
        m5RBLineSetting['minDiff'] = 1
        m3RBLineSetting = copy.copy(m3LineSettingBase)
        m3RBLineSetting['shortSymbol'] = 'RB'
        m3RBLineSetting['name'] = 'M3RB'
        m3RBLineSetting['minDiff'] = 1

        # 橡胶RU
        m5RULineSetting = copy.copy(m5LineSettingBase)
        m5RULineSetting['shortSymbol'] = 'RU'
        m5RULineSetting['name'] = 'M5RU'
        m5RULineSetting['minDiff'] = 5
        m3RULineSetting = copy.copy(m3LineSettingBase)
        m3RULineSetting['shortSymbol'] = 'RU'
        m3RULineSetting['name'] = 'M3RU'
        m3RULineSetting['minDiff'] = 5

        # 豆粕M
        m5MLineSetting = copy.copy(m5LineSettingBase)
        m5MLineSetting['shortSymbol'] = 'M'
        m5MLineSetting['name'] = 'M5M'
        m5MLineSetting['minDiff'] = 1
        m3MLineSetting = copy.copy(m3LineSettingBase)
        m3MLineSetting['shortSymbol'] = 'M'
        m3MLineSetting['name'] = 'M3M'
        m3MLineSetting['minDiff'] = 1

        # 铁矿石I
        m5ILineSetting = copy.copy(m5LineSettingBase)
        m5ILineSetting['shortSymbol'] = 'I'
        m5ILineSetting['name'] = 'M5I'
        m5ILineSetting['minDiff'] = 0.5
        m3ILineSetting = copy.copy(m3LineSettingBase)
        m3ILineSetting['shortSymbol'] = 'I'
        m3ILineSetting['name'] = 'M3I'
        m3ILineSetting['minDiff'] = 0.5

        # 沪铜CU
        m5CULineSetting = copy.copy(m5LineSettingBase)
        m5CULineSetting['shortSymbol'] = 'CU'
        m5CULineSetting['name'] = 'M5CU'
        m5CULineSetting['minDiff'] = 10
        m3CULineSetting = copy.copy(m3LineSettingBase)
        m3CULineSetting['shortSymbol'] = 'CU'
        m3CULineSetting['name'] = 'M3CU'
        m3CULineSetting['minDiff'] = 10

        # 沪镍NI
        m5NILineSetting = copy.copy(m5LineSettingBase)
        m5NILineSetting['shortSymbol'] = 'NI'
        m5NILineSetting['name'] = 'M5NI'
        m5NILineSetting['minDiff'] = 10
        m3NILineSetting = copy.copy(m3LineSettingBase)
        m3NILineSetting['shortSymbol'] = 'NI'
        m3NILineSetting['name'] = 'M3NI'
        m3NILineSetting['minDiff'] = 10

        # 热轧卷板HC
        m5HCLineSetting = copy.copy(m5LineSettingBase)
        m5HCLineSetting['shortSymbol'] = 'HC'
        m5HCLineSetting['name'] = 'M5HC'
        m5HCLineSetting['minDiff'] = 2
        m3HCLineSetting = copy.copy(m3LineSettingBase)
        m3HCLineSetting['shortSymbol'] = 'HC'
        m3HCLineSetting['name'] = 'M3HC'
        m3HCLineSetting['minDiff'] = 2

        # 豆油Y
        m5YLineSetting = copy.copy(m5LineSettingBase)
        m5YLineSetting['shortSymbol'] = 'Y'
        m5YLineSetting['name'] = 'M5Y'
        m5YLineSetting['minDiff'] = 2
        m3YLineSetting = copy.copy(m3LineSettingBase)
        m3YLineSetting['shortSymbol'] = 'Y'
        m3YLineSetting['name'] = 'M3Y'
        m3YLineSetting['minDiff'] = 2

        # 焦煤JM
        m5JMLineSetting = copy.copy(m5LineSettingBase)
        m5JMLineSetting['shortSymbol'] = 'JM'
        m5JMLineSetting['name'] = 'M5JM'
        m5JMLineSetting['minDiff'] = 1
        m3JMLineSetting = copy.copy(m3LineSettingBase)
        m3JMLineSetting['shortSymbol'] = 'JM'
        m3JMLineSetting['name'] = 'M3JM'
        m3JMLineSetting['minDiff'] = 1

        # 棉花CF
        m5CFLineSetting = copy.copy(m5LineSettingBase)
        m5CFLineSetting['shortSymbol'] = 'CF'
        m5CFLineSetting['name'] = 'M5CF'
        m5CFLineSetting['minDiff'] = 5
        m3CFLineSetting = copy.copy(m3LineSettingBase)
        m3CFLineSetting['shortSymbol'] = 'CF'
        m3CFLineSetting['name'] = 'M3CF'
        m3CFLineSetting['minDiff'] = 5

        # 沪锌ZN
        m5ZNLineSetting = copy.copy(m5LineSettingBase)
        m5ZNLineSetting['shortSymbol'] = 'ZN'
        m5ZNLineSetting['name'] = 'M5ZN'
        m5ZNLineSetting['minDiff'] = 5
        m3ZNLineSetting = copy.copy(m3LineSettingBase)
        m3ZNLineSetting['shortSymbol'] = 'ZN'
        m3ZNLineSetting['name'] = 'M3ZN'
        m3ZNLineSetting['minDiff'] = 5

        # 白糖SR
        m5SRLineSetting = copy.copy(m5LineSettingBase)
        m5SRLineSetting['shortSymbol'] = 'SR'
        m5SRLineSetting['name'] = 'M5SR'
        m5SRLineSetting['minDiff'] = 1
        m3SRLineSetting = copy.copy(m3LineSettingBase)
        m3SRLineSetting['shortSymbol'] = 'SR'
        m3SRLineSetting['name'] = 'M3SR'
        m3SRLineSetting['minDiff'] = 1

        self.MARKET = {
            'RB': {'name': 'RB', 'm5Setting': m5RBLineSetting, 'm3Setting': m3RBLineSetting, 'varList': copy.copy(self.varList)},
            'RU': {'name': 'RU', 'm5Setting': m5RULineSetting, 'm3Setting': m3RULineSetting, 'varList': copy.copy(self.varList)},
            'M': {'name': 'M', 'm5Setting': m5MLineSetting, 'm3Setting': m3MLineSetting, 'varList': copy.copy(self.varList)},
            'I': {'name': 'I', 'm5Setting': m5ILineSetting, 'm3Setting': m3ILineSetting, 'varList': copy.copy(self.varList)},
            'CU': {'name': 'CU', 'm5Setting': m5CULineSetting, 'm3Setting': m3CULineSetting, 'varList': copy.copy(self.varList)},
            'NI': {'name': 'NI', 'm5Setting': m5NILineSetting, 'm3Setting': m3NILineSetting, 'varList': copy.copy(self.varList)},
            'HC': {'name': 'HC', 'm5Setting': m5HCLineSetting, 'm3Setting': m3HCLineSetting, 'varList': copy.copy(self.varList)},
            'Y': {'name': 'Y', 'm5Setting': m5YLineSetting, 'm3Setting': m3YLineSetting, 'varList': copy.copy(self.varList)},
            'JM': {'name': 'JM', 'm5Setting': m5JMLineSetting, 'm3Setting': m3JMLineSetting, 'varList': copy.copy(self.varList)},
            'CF': {'name': 'CF', 'm5Setting': m5CFLineSetting, 'm3Setting': m3CFLineSetting, 'varList': copy.copy(self.varList)},
            'ZN': {'name': 'ZN', 'm5Setting': m5ZNLineSetting, 'm3Setting': m3ZNLineSetting, 'varList': copy.copy(self.varList)},
            'SR': {'name': 'SR', 'm5Setting': m5SRLineSetting, 'm3Setting': m3SRLineSetting, 'varList': copy.copy(self.varList)},
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
        if hasattr(tick, 'vtSymbol'):
            if tick.vtSymbol == 'rb1901':
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

    def onBarM5(self, bar):
        self.writeCtaLog('*' * 20 + 'onBarM5 start' + '*' * 20)
        # print('\n'.join(['%s:%s' % item for item in bar.__dict__.items()]))
        short_symbol = bar.symbol[:-4].upper()
        var_list = self.MARKET[short_symbol]['varList']
        self.writeCtaLog('=' * 20 + id(var_list))
        self.writeCtaLog('=' * 20 + id(self.MARKET[short_symbol]['varList']))
        self.writeCtaLog('=' * 20 + id(self.MARKET[short_symbol]['varList']['m5PreSwingArray']))

        var_list['m5PreSwingArray'][0: var_list['bufferSize'] - 1] = \
            var_list['m5PreSwingArray'][1: var_list['bufferSize']]
        var_list['m5PreVolumeArray'][0: var_list['bufferSize'] - 1] = \
            var_list['m5PreVolumeArray'][1: var_list['bufferSize']]
        var_list['m5PreOpenInterestArray'][0: var_list['bufferSize'] - 1] = \
            var_list['m5PreOpenInterestArray'][1: var_list['bufferSize']]

        var_list['m5PreSwingArray'][-1] = bar.high - bar.low
        var_list['m5PreVolumeArray'][-1] = bar.volume
        var_list['m5PreOpenInterestArray'][-1] = bar.openInterest

        if var_list['m5RecordedKline'] <= var_list['m5MaxRecordedKline']:
            self.writeCtaLog(u'In top {} - {} bars'.format(var_list['m5MaxRecordedKline'], var_list['m5RecordedKline']))
            var_list['m5RecordedKline'] += 1
            var_list['m5HighValue'] = 0 if var_list['m5HighValue'] == 0 else bar.high
            var_list['m5LowValue'] = 0 if var_list['m5LowValue'] == 0 else bar.low
            var_list['m5HighValue'] = max(var_list['m5HighValue'], bar.high)
            var_list['m5LowValue'] = min(var_list['m5LowValue'], bar.low)

            if var_list['m5HighValue'] == bar.high:
                var_list['m5HighOpenInterest'] = bar.openInterest
                var_list['m5HighVolume'] = bar.volume
                var_list['m5HighSwing'] = bar.high - bar.low

            if var_list['m5LowValue'] == bar.low:
                var_list['m5LowOpenInterest'] = bar.openInterest
                var_list['m5LowVolume'] = bar.volume
                var_list['m5LowSwing'] = bar.high - bar.low

            if var_list['m5HighValue'] - var_list['m5LowValue'] > bar.close * 0.016:
                var_list['isBigSwing'] = True
            if bar.close < bar.open:
                var_list['isContinuousRise'] = False
            else:
                var_list['isContinuousFall'] = False

        self.MARKET[short_symbol]['varList'] = var_list
        var_list = None
        self.writeCtaLog('*' * 20 + short_symbol + 'after')
        for (k, v) in self.MARKET[short_symbol]['varList'].items():
            self.writeCtaLog('%s: %s' % (k, v))

        if self.MARKET[short_symbol]['varList']['m5RecordedKline'] >= 5:
            self.writeCtaLog(u'out of {} bars'.format(self.MARKET[short_symbol]['varList']['m5MaxRecordedKline']))
            self.writeCtaLog(u'{0}: 当前价{1}, 前25分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.format(
                bar.symbol, bar.close, self.MARKET[short_symbol]['varList']['m5HighValue'], self.MARKET[short_symbol]['varList']['m5HighVolume'], self.MARKET[short_symbol]['varList']['m5HighOpenInterest'], bar.volume, bar.openInterest))

            if self.MARKET[short_symbol]['varList']['isContinuousRise']:
                self.writeCtaLog(u'前5根k线持续上涨不开仓')
                return
            if self.MARKET[short_symbol]['varList']['isContinuousRise']:
                self.writeCtaLog(u'前5根线持续下跌不开仓')
                return

            if self.MARKET[short_symbol]['varList']['isBigSwing']:
                self.writeCtaLog(u'前5根K线的高点和低点幅度适当，不能差距太大，如果差价太大，不能开仓，其中参考范围是振幅差距在1.6%以内')
                return

            swing_sum = 0
            if bar.close > self.MARKET[short_symbol]['varList']['m5HighValue'] and bar.openInterest > self.MARKET[short_symbol]['varList']['m5PreOpenInterestArray'][-2] and bar.openInterest > self.MARKET[short_symbol]['varList']['m5HighOpenInterest'] * 0.5:
                self.writeCtaLog(u'价格突破前5根5分钟K线最高点,持仓量增加')
                if bar.volume > self.MARKET[short_symbol]['varList']['m5HighValue'] * 0.7 or bar.volume > self.MARKET[short_symbol]['varList']['m5PreVolumeArray'][-2]:
                    self.writeCtaLog(u'成交量增加，成交量高于前面K线成交量或者成交量是高点K线的70%以上')
                    for item in self.MARKET[short_symbol]['varList']['m5PreSwingArray'][7:10]:
                        swing_sum = swing_sum + item
                    if bar.high - bar.low > (swing_sum/3 * 1.2):
                        self.writeCtaLog(u'中阳线 这跟K线是近期震荡的几根K线的振幅的1.2倍以上')
                        ddRobot = dingRobot()
                        self.writeCtaLog(u'send message')
                        ddRobot.postStart(u'{0}可以开多仓, 当前价{1}, 前5分钟最高价{2}， 最高价时成交量{3}， 最高价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                          format(bar.symbol, bar.close, self.MARKET[short_symbol]['varList']['m5HighValue'], self.MARKET[short_symbol]['varList']['m5HighVolume'], self.MARKET[short_symbol]['varList']['m5HighOpenInterest'], bar.volume, bar.openInterest))

            if bar.close < self.MARKET[short_symbol]['varList']['m5LowValue'] and bar.openInterest > self.MARKET[short_symbol]['varList']['m5PreOpenInterestArray'][-2] and bar.openInterest > self.MARKET[short_symbol]['varList']['m5LowOpenInterest'] * 0.5:
                self.writeCtaLog(u'价格突破前5根5分钟K线最低点,持仓量减少')
                if abs(bar.high - bar.low) > (swing_sum / 3 * 1.2):
                    self.writeCtaLog(u'这跟K线是近期震荡的几根K线的振幅的1.2倍以上')
                    ddRobot = dingRobot()
                    self.writeCtaLog(u'send message')
                    ddRobot.postStart(u'{0}可以开空仓, 当前价{1}, 前5分钟最低价{2}， 最低价时成交量{3}， 最低价时持仓量{4}， 当前成交量{5}， 当前持仓量{6}。'.
                                      format(bar.symbol, bar.close, self.MARKET[short_symbol]['varList']['m5LowValue'], self.MARKET[short_symbol]['varList']['m5LowVolume'], self.MARKET[short_symbol]['varList']['m5LowOpenInterest'], bar.volume, bar.openInterest))

    def onBarM3(self, bar):
        self.writeCtaLog('*' * 20 + 'onBarM3 start' + '*' * 20)
        pass

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()
