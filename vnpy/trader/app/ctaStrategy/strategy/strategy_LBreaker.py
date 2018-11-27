# encoding: UTF-8

import sys
sys.path.append('..')
from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_INT
from vnpy.trader.app.ctaStrategy.ctaPolicy import  *
from vnpy.trader.app.ctaStrategy.ctaPosition import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.strategy.dingTalkSend import dingRobot
from vnpy.data.shcifco.vnshcifco import *


class StrategyLBreaker(CtaTemplate):
    className = 'StrategyLBreaker'
    author = u'Gary'

    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    minDiff = 1                # 商品的最小交易单位
    maLength = 40              # 平均波动周期 MA Length
    maxPos = 4

    def __init__(self, ctaEngine, setting=None):
        super(StrategyLBreaker, self).__init__(ctaEngine, setting)
        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('minDiff')
        self.paramList.append('shortSymbol')

        # 增加监控变量项目
        self.varList.append('pos')  # 仓位
        self.varList.append('entrust')  # 是否正在委托
        self.varList.append('ma40')  # MA40
        self.varList.append('globalPreHigh')  # 前高
        self.varList.append('globalPreLow')  # 前低

        self.curDateTime = None  # 当前Tick时间
        self.curTick = None  # 最新的tick
        self.lastOrderTime = None  # 上一次委托时间
        self.cancelSeconds = 60  # 撤单时间(秒)

        # 定义日内的交易窗口
        self.openWindow = False  # 开市窗口
        self.tradeWindow = False  # 交易窗口
        self.closeWindow = False  # 收市平仓窗口

        self.inited = False  # 是否完成了策略初始化
        self.backtesting = False  # 是否回测
        self.lineM5 = None  # 5分钟K线
        self.lineH1 = None  # 1小时k线

        # 创建一个策略规则
        self.policy = CtaPolicy()
        self.policy.addPos = True  # 是否激活加仓策略
        self.policy.addPosOnPips = 1  # 加仓策略1，固定点数（动态ATR）

        self.highPriceInLong = EMPTY_FLOAT  # 成交后，最高价格
        self.lowPriceInShort = EMPTY_FLOAT  # 成交后，最低价格

        # 增加仓位管理模块
        self.position = CtaPosition(self)
        self.position.maxPos = self.maxPos

        if setting:
            self.setParam(setting)

            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'
            lineM5Setting['barTimeInterval'] = 60 * 5
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            lineM5Setting['inputPreLen'] = 5
            lineM5Setting['mode'] = CtaLineBar.TICK_MODE
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            self.lineM5 = CtaLineBar(self, self.onBarM5, lineM5Setting)

            lineH1Setting = {}
            lineH1Setting['name'] = u'H1'
            lineH1Setting['period'] = 'hour'
            lineH1Setting['barTimeInterval'] = 1
            lineH1Setting['inputPreLen'] = 5
            lineH1Setting['inputMa1Len'] = self.maLength
            lineH1Setting['mode'] = CtaLineBar.TICK_MODE
            lineH1Setting['minDiff'] = self.minDiff
            lineH1Setting['shortSymbol'] = self.shortSymbol
            self.lineH1 = CtaHourBar(self, self.onBarH1, lineH1Setting)

        self.onInit()

    def onInit(self, force=False):
        """初始化 """
        if force:
            self.writeCtaLog(u'策略强制初始化')
            self.inited = False
            self.trading = False
        else:
            self.writeCtaLog(u'策略初始化')
            if self.inited:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        self.pos = EMPTY_INT                 # 初始化持仓
        self.entrust = EMPTY_INT             # 初始化委托状态
        self.globalPreHigh = 0  # 初始化前高
        self.globalPreLow = 1000000  # 初始化前低
        self.ma_40 = EMPTY_INT  # 初始化ma_40

        if not self.backtesting:
            if not self.__initDataFromShcifo():
                self.inited = True
                self.trading = True

        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

    def __initDataFromShcifo(self):
        ip = 'dsdx.shcifco.com'
        port = '10083'
        token = '50404935ba9cb370de2ac22474966163'
        api = ShcifcoApi(ip, port, token)
        ret = api.getMinBars(self.symbol, self.lineH1.addBar)
        if not ret:
            self.writeCtaLog(u'获取M5数据失败')
            return False

        return True

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'启动')

    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.uncompletedOrders.clear()
        self.pos = EMPTY_INT
        self.entrust = EMPTY_INT

        self.writeCtaLog(u'停止')
        self.putEvent()

    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.position.pos))

    def onOrder(self, order):
        """报单更新"""
        pass

    def onStopOrder(self, orderRef):
        """停止单更新"""
        pass

    def onTick(self, tick):
        """行情更新
        :type tick: object
        """
        self.curTick = tick

        if (tick.datetime.hour >= 3 and tick.datetime.hour <= 8) or (tick.datetime.hour >= 16 and tick.datetime.hour <= 20):
            self.writeCtaLog(u'休市/集合竞价排名时数据不处理')
            return

        # 更新策略执行的时间（用于回测时记录发生的时间）
        self.curDateTime = tick.datetime

        # 2、计算交易时间和平仓时间
        self.__timeWindow(self.curDateTime)

        # 推送Tick到lineM5
        self.lineM5.onTick(tick)
        # 推送Tick到lineH1
        self.lineH1.onTick(tick)

        # 首先检查是否是实盘运行还是数据预处理阶段
        if not (self.inited and len(self.lineH1.lineMa1) > 0):
            return

        self.globalPreHigh = max(tick.lastPrice, self.globalPreHigh)
        self.globalPreLow = min(tick.lastPrice, self.globalPreLow)

    def onBar(self, bar):
        # 更新策略执行的时间（用于回测时记录发生的时间）
        # 回测数据传送的bar.datetime，为bar的开始时间，所以，到达策略时，当前时间为bar的结束时间
        self.curDateTime = bar.datetime + timedelta(seconds=self.lineM5.barTimeInterval)

        # 2、计算交易时间和平仓时间
        self.__timeWindow(bar.datetime)

        # 推送tick到15分钟K线
        self.lineM5.addBar(bar)
        self.lineH1.addBar(bar)

        # 4、交易逻辑
        # 首先检查是否是实盘运行还是数据预处理阶段

    def onBarM5(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineM5的回调"""
        self.writeCtaLog('-' * 20 + 'onBarM5 start' + '-' * 20)
        self.writeCtaLog(self.lineM5.displayLastBar())
        if not self.inited:
            return

        if self.lineM5.mode == self.lineM5.TICK_MODE:
            idx = 2
        else:
            idx = 1

        # 更新最高价/最低价
        if self.backtesting:
            # 持有多仓/空仓时，更新最高价和最低价
            # 更新最高价和最低价
            self.globalPreHigh = max(bar.high, self.globalPreHigh)
            self.globalPreLow = min(bar.low, self.globalPreLow)

        if len(self.lineH1.lineMa1) > 0:
            self.ma_40 = self.lineH1.lineMa1[-1]

        if self.tradeWindow and self.position.pos == 0:
            self.writeCtaLog(u'~{0} in tradeWindow'.format(self.symbol))
            open_point, lose_point, win_point1 = 0.0, 0.0, 0.0
            if bar.close > self.lineH1.lineMa1[-1]:
                self.writeCtaLog(u'~{0} 向上突破MA40 {1}'.format(self.symbol, self.lineH1.lineMa1[-1]))
                if bar.close > self.globalPreHigh:
                    self.writeCtaLog(u'~{0} 向上突破前高 {1}'.format(self.symbol, self.globalPreHigh))
                    if bar.openInterest > self.lineM5.lineBar[-1].openInterest * 1.003:
                        self.writeCtaLog(u'~{0} 持仓量比前一根K线持仓量增加千分之三以上 {1}'.format(self.symbol, bar.openInterest))
                        if bar.close < self.globalPreLow * 1.015:
                            self.writeCtaLog(u'~{0} 收盘价小于前低的 1 + 1.5% {1}'.format(self.symbol, self.globalPreLow * 1.015))
                            if bar.high - bar.low > 20 * self.minDiff:
                                open_point = bar.close + (bar.high - bar.low)//2 + 2 * self.minDiff
                                lose_point = bar.close - 2 * self.minDiff
                            else:
                                open_point = self.globalPreHigh + 2 * self.minDiff
                                lose_point = self.lineM5.preLow[-1] - 2 * self.minDiff
                            win_point1 = bar.close + (open_point - lose_point) * 1.5

                            ddRobot = dingRobot()
                            message = u'{0}可以开多仓, 当前价{1}, 开仓点{2}， 第一止盈点{3}, 止损点{4}'.\
                                format(bar.symbol, bar.close, open_point, win_point1, lose_point)
                            self.writeCtaLog(u'~{0} send message: {1}'.format(self.symbol, message))
                            ddRobot.postStart(message)
            if bar.close < self.lineH1.lineMa1[-1]:
                self.writeCtaLog(u'~{0} 向下突破MA40 {1}'.format(self.symbol, self.lineH1.lineMa1[-1]))
                if bar.close < self.globalPreLow:
                    self.writeCtaLog(u'~{0} 向下突破前低 {1}'.format(self.symbol, self.globalPreLow))
                    if bar.openInterest < self.lineM5.lineBar[-1].openInterest * 0.997:
                        self.writeCtaLog(u'~{0} 持仓量比前一根K线持仓量减少千分之三以上 {1}'.format(self.symbol, bar.openInterest))
                        if bar.close > self.globalPreHigh * 0.985:
                            self.writeCtaLog(u'~{0} 收盘价大于前高的 1 - 1.5% {1}'.format(self.symbol, self.globalPreHigh * 0.985))
                            if bar.high - bar.low > 20 * self.minDiff:
                                open_point = bar.close + (bar.high - bar.low)//2 - 2 * self.minDiff
                                lose_point = bar.close + 2 * self.minDiff
                            else:
                                open_point = self.globalPreLow - 2 * self.minDiff
                                lose_point = self.lineM5.preHigh[-1] + 2 * self.minDiff
                            win_point1 = bar.close + (open_point - lose_point) * 1.5

                            ddRobot = dingRobot()
                            message = u'{0}可以开多仓, 当前价{1}, 开仓点{2}， 第一止盈点{3}, 止损点{4}'.\
                                format(bar.symbol, bar.close, open_point, win_point1, lose_point)
                            self.writeCtaLog(u'~{0} send message: {1}'.format(self.symbol, message))
                            ddRobot.postStart(message)

    def onBarH1(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineH1的回调"""
        self.writeCtaLog('*' * 20 + 'onBarH1 start' + '*' * 20)
        self.writeCtaLog(self.lineH1.displayLastBar())
        # 未初始化完成
        # self.writeCtaLog(u'MA40:{0}'.format(self.lineH1.lineMa1[-1]))
        if not self.inited:
            if len(self.lineH1.lineBar) > 40 + 2:
                self.inited = True
            else:
                return


    def __timeWindow(self, dt):
        """交易与平仓窗口"""
        # 交易窗口 避开早盘和夜盘的前5分钟，防止隔夜跳空。

        self.closeWindow = False
        self.tradeWindow = False
        self.openWindow = False

        # 初始化当日的首次交易
        # if (tick.datetime.hour == 9 or tick.datetime.hour == 21) and tick.datetime.minute == 0 and tick.datetime.second ==0:
        #  self.firstTrade = True

        # 开市期，波动较大，用于判断止损止盈，或开仓
        if (dt.hour == 9 or dt.hour == 21) and dt.minute < 2:
            self.openWindow = True

        # 日盘
        if dt.hour == 9 and dt.minute >= 30:
            self.tradeWindow = True
            return

        if dt.hour == 10:
            if dt.minute <= 15 or dt.minute >= 30:
                self.tradeWindow = True
                return

        if dt.hour == 11 and dt.minute <= 30:
            self.tradeWindow = True
            return

        if dt.hour == 13 and dt.minute >= 30:
            self.tradeWindow = True
            return

        if dt.hour == 14:

            if dt.minute < 59:
                self.tradeWindow = True
                return

            if dt.minute == 59:  # 日盘平仓
                self.closeWindow = True
                return

        # 夜盘

        if dt.hour == 21 and dt.minute >= 30:
            self.tradeWindow = True
            return

        # 上期 贵金属， 次日凌晨2:30
        if self.shortSymbol in NIGHT_MARKET_SQ1:

            if dt.hour == 22 or dt.hour == 23 or dt.hour == 0 or dt.hour == 1:
                self.tradeWindow = True
                return

            if dt.hour == 2:
                if dt.minute < 29:  # 收市前29分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return

        # 上期 有色金属，黑色金属，沥青 次日01:00
        if self.shortSymbol in NIGHT_MARKET_SQ2:
            if dt.hour == 22 or dt.hour == 23:
                self.tradeWindow = True
                return

            if dt.hour == 0:
                if dt.minute < 59:  # 收市前29分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

            return

        # 上期 天然橡胶  23:00
        if self.shortSymbol in NIGHT_MARKET_SQ3:

            if dt.hour == 22:
                if dt.minute < 59:  # 收市前1分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

        # 郑商、大连 23:30
        if self.shortSymbol in NIGHT_MARKET_ZZ or self.shortSymbol in NIGHT_MARKET_DL:
            if dt.hour == 22:
                self.tradeWindow = True
                return

            if dt.hour == 23:
                if dt.minute < 29:  # 收市前1分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29 and dt.second > 30:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return
