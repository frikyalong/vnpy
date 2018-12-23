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


class StrategyLBreaker(CtaTemplate):
    className = 'StrategyLBreaker'
    author = u'Gary'
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    ma = 40                    # 平均波动周期 MA Length

    def __init__(self, ctaEngine, setting=None):
        super(StrategyLBreaker, self).__init__(ctaEngine, setting)
        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('ma')  # MA40
        self.paramList.append('vtSymbol')  # MA40
        self.paramList.append('shortSymbol')  # MA40
        self.paramList.append('name')  # MA40
        self.paramList.append('mode')  # MA40
        self.paramList.append('minDiff')  # MA40
        self.paramList.append('backtesting')  # MA40
        self.paramList.append('percentLimit')  # MA40

        # 增加监控变量项目
        self.varList.append('pos')              # 仓位
        self.varList.append('entrust')          # 是否正在委托
        self.varList.append('globalPreHigh')  # 前高
        self.varList.append('globalPreLow')  # 前低
        self.varList.append('maValue')

        self.isMonitorMode = False

        self.globalPreHigh = 0  # 初始化前高
        self.globalPreLow = 1000000  # 初始化前低
        self.maValue = 0

        # 仓位状态
        self.maxPos = 10
        self.position = CtaPosition(self)  # 0 表示没有仓位，1 表示持有多头，-1 表示持有空头
        self.position.maxPos = self.maxPos
        self.lastTradedTime = datetime.now()  # 上一交易时间

        self.tradingOpen = True  # 允许开仓
        self.recheckPositions = True

        self.forceClose = EMPTY_STRING  # 强制平仓的日期（参数，字符串）
        self.forceCloseDate = None  # 强制平仓的日期（日期类型）
        self.forceTradingClose = False  # 强制平仓标志
        self.firstTrade = True  # 交易日的首个交易

        self.curDateTime = None  # 当前Tick时间
        self.curTick = None  # 最新的tick
        self.lastOrderTime = None  # 上一次委托时间
        self.cancelSeconds = 60   # 撤单时间(秒)
        self.tradingDay = EMPTY_STRING  # 交易日期

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
        self.recheckPositions = True              # 重新提交平仓订单。在每个交易日的下午14点59分时激活，在新的交易日（21点）开始时，重新执行。

        self.highPriceInLong = EMPTY_FLOAT  # 成交后，最高价格
        self.lowPriceInShort = EMPTY_FLOAT  # 成交后，最低价格
        # open_point, lose_point, win_point1 = 0.0, 0.0, 0.0
        self.long_open = EMPTY_FLOAT
        self.long_win = EMPTY_FLOAT
        self.long_lose = EMPTY_FLOAT
        self.short_open = EMPTY_FLOAT
        self.short_win = EMPTY_FLOAT
        self.short_lose = EMPTY_FLOAT
        self.message_title = "乐天天"

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
            lineH1Setting['inputMa1Len'] = self.ma
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

        # 初始化持仓相关数据
        self.position.pos = EMPTY_INT
        self.pos = EMPTY_INT                 # 初始化持仓
        self.entrust = EMPTY_INT             # 初始化委托状态

        if not self.backtesting:
            if not self.__init_data_from_shcifo():
                self.inited = False
                self.trading = False
        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

    def __init_data_from_shcifo(self):
        api = ShcifcoApi('dsdx.shcifco.com', '10083', '50404935ba9cb370de2ac22474966163')
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
        if self.isMonitorMode:
            return
        """报单更新"""
        self.writeCtaLog(u'OnOrder()报单更新，orderID:{0},{1},totalVol:{2},tradedVol:{3},offset:{4},price:{5},direction:{6},status:{7}'
                         .format(order.orderID, order.vtSymbol, order.totalVolume,order.tradedVolume,
                                 order.offset, order.price, order.direction, order.status))

        # 委托单主键，vnpy使用 "gateway.orderid" 的组合
        orderkey = order.gatewayName+u'.'+order.orderID

        if orderkey in self.uncompletedOrders:
            if order.totalVolume == order.tradedVolume:
                # 开仓，平仓委托单全部成交
                # 平空仓完成(cover)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平空仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 平多仓完成(sell)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平多仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 开多仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开多仓完成')
                    # 更新仓位
                    self.pos = order.tradedVolume

                # 开空仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开空仓完成')
                    self.pos = 0 - order.tradedVolume

                del self.uncompletedOrders[orderkey]
                if len(self.uncompletedOrders) == 0:
                    self.entrust = 0

            elif order.tradedVolume > 0 and not order.totalVolume == order.tradedVolume and order.offset != OFFSET_OPEN:
                # 平仓委托单部分成交
                pass

            elif order.offset == OFFSET_OPEN and order.status == STATUS_CANCELLED:
                # 开仓委托单被撤销
                self.entrust = 0
                pass

            else:
                self.writeCtaLog(u'OnOrder()委托单返回，total:{0},traded:{1}'
                                 .format(order.totalVolume, order.tradedVolume,))

        self.putEvent()         # 更新监控事件

    def onStopOrder(self, orderRef):
        """停止单更新"""
        self.writeCtaLog(u'{0},停止单触发，orderRef:{1}'.format(self.curDateTime, orderRef))
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
        if (tick.datetime.hour == 21 and tick.datetime.minute == 0 and tick.datetime.second == 1):
            self.globalPreHigh = max(tick.lastPrice, 0)
            self.globalPreLow = min(tick.lastPrice, 1000000)

        # 2、计算交易时间和平仓时间
        self.__timeWindow(self.curDateTime)

        # 推送Tick到lineM5
        self.lineM5.onTick(tick)
        # 推送Tick到lineH1
        self.lineH1.onTick(tick)

        # 首先检查是否是实盘运行还是数据预处理阶段
        if not (self.inited and len(self.lineH1.lineMa1) > 0):
            return

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
        if not self.inited:
            if len(self.lineH1.lineBar) > self.ma + 2:
                self.inited = True
            else:
                return

    def onBarM5(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineM5的回调"""
        self.writeCtaLog('-' * 20 + 'onBarM5 start' + '-' * 20)
        self.writeCtaLog(self.lineM5.displayLastBar())
        self.writeCtaLog(u'前高: {0} 前低: {1} ma40: {2}'.format(self.globalPreHigh, self.globalPreLow, self.maValue))
        if not self.inited:
            return
        self.tradingDay = bar.tradingDay
        # 执行撤单逻辑
        self.__cancelLogic(dt=self.curDateTime)

        if self.lineM5.mode == self.lineM5.TICK_MODE:
            idx = 2
        else:
            idx = 1

        if len(self.lineH1.lineMa1) > 0:
            self.maValue = self.lineH1.lineMa1[-1]

        if self.tradeWindow:
            self.writeCtaLog(u'### {0} in tradeWindow'.format(self.symbol))
            if self.pos == 0:
                self.writeCtaLog(u'### {0} 持仓为0'.format(self.symbol))
                if bar.close > self.lineH1.lineMa1[-1]:
                    self.writeCtaLog(u'### {0} 向上突破MA40 {1} 前高 {2}'.format(self.symbol, self.lineH1.lineMa1[-1], self.globalPreHigh))
                    if bar.close > self.globalPreHigh:
                        self.writeCtaLog(u'### {0} 向上突破前高 {1}'.format(self.symbol, self.globalPreHigh))
                        if float(bar.openInterest) > float(self.lineM5.lineBar[-1].openInterest) * 1.003:
                            self.writeCtaLog(u'### {0} 持仓量比前一根K线持仓量增加千分之三以上 {1}'.format(self.symbol, bar.openInterest))
                            if float(bar.close) < float(self.globalPreLow) * 1.015:
                                self.writeCtaLog(u'### {0} 收盘价小于前低的 1 + 1.5% {1}'.format(self.symbol, self.globalPreLow * 1.015))
                                if bar.high - bar.low > 20 * self.minDiff:
                                    self.long_open = bar.close + (bar.high - bar.low)//2 + 2 * self.minDiff
                                    self.long_lose = bar.close - 2 * self.minDiff
                                else:
                                    self.long_open = self.globalPreHigh + 2 * self.minDiff
                                    self.long_lose = self.lineM5.preLow[-1] - 2 * self.minDiff
                                self.long_win = bar.close + (self.long_open - self.long_lose) * 1.5
                                message = u'{0}可以开多仓, 当前价{1}, 开仓点{2}， 第一止盈点{3}, 止损点{4}'. \
                                    format(bar.symbol, bar.close, self.long_open, self.long_win, self.long_lose)
                                self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                                if not self.backtesting:
                                    send_wx_msg(self.message_title, message)
                                self.writeCtaLog(u'{0},开仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, self.long_open))
                                orderid = self.buy(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                                if orderid:
                                    self.lastOrderTime = self.curDateTime

                if bar.close < self.lineH1.lineMa1[-1]:
                    self.writeCtaLog(u'### {0} 向下突破MA40 {1}'.format(self.symbol, self.lineH1.lineMa1[-1]))
                    if bar.close < self.globalPreLow:
                        self.writeCtaLog(u'### {0} 向下突破前低 {1}'.format(self.symbol, self.globalPreLow))
                        if float(bar.openInterest) < float(self.lineM5.lineBar[-1].openInterest) * 0.997:
                            self.writeCtaLog(u'### {0} 持仓量比前一根K线持仓量减少千分之三以上 {1}'.format(self.symbol, bar.openInterest))
                            if float(bar.close) > float(self.globalPreHigh) * 0.985:
                                self.writeCtaLog(u'### {0} 收盘价大于前高的 1 - 1.5% {1}'.format(self.symbol, self.globalPreHigh * 0.985))
                                if bar.high - bar.low > 20 * self.minDiff:
                                    self.short_open = bar.close + (bar.high - bar.low)//2 - 2 * self.minDiff
                                    self.short_lose = bar.close + 2 * self.minDiff
                                else:
                                    self.short_open = self.globalPreLow - 2 * self.minDiff
                                    self.short_lose = self.lineM5.preHigh[-1] + 2 * self.minDiff
                                self.short_win = bar.close + (self.short_open - self.short_lose) * 1.5
                                message = u'{0}可以开空仓, 当前价{1}, 开仓点{2}， 第一止盈点{3}, 止损点{4}'.\
                                    format(bar.symbol, bar.close, self.short_open, self.short_win, self.short_lose)
                                self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                                if not self.backtesting:
                                    send_wx_msg(self.message_title, message)
                                self.writeCtaLog(u'{0},开仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, self.short_open))
                                orderid = self.short(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                                if orderid:
                                    self.lastOrderTime = self.curDateTime
            else:
                self.writeCtaLog(u'### {0} 持仓不为0'.format(self.symbol))
                if bar.close > self.long_win:
                    if not self.backtesting:
                        message = u'{0}平仓多单止盈, 当前价{1}'. format(bar.symbol, bar.close)
                        self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                        send_wx_msg(self.message_title, message)
                    self.writeCtaLog(u'{0},平仓多单止盈{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        self.lastOrderTime = self.curDateTime

                if bar.close < self.long_lose:
                    if not self.backtesting:
                        message = u'{0}平仓多单止损, 当前价{1}'. format(bar.symbol, bar.close)
                        self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                        send_wx_msg(self.message_title, message)
                    self.writeCtaLog(u'{0},平仓多单止损{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        self.lastOrderTime = self.curDateTime

                if bar.close < self.short_win:
                    if not self.backtesting:
                        message = u'{0}平仓多单止盈, 当前价{1}'.format(bar.symbol, bar.close)
                        self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                        send_wx_msg(self.message_title, message)
                    self.writeCtaLog(u'{0},平仓空单止损{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        self.lastOrderTime = self.curDateTime

                if bar.close > self.short_lose:
                    if not self.backtesting:
                        message = u'{0}平仓多单止损, 当前价{1}'.format(bar.symbol, bar.close)
                        self.writeCtaLog(u'### {0} send message: {1}'.format(self.symbol, message))
                        send_wx_msg(self.message_title, message)
                    self.writeCtaLog(u'{0},平仓空单止损{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        self.lastOrderTime = self.curDateTime

        # 持有多仓/空仓时，更新最高价和最低价
        # 更新最高价和最低价
        self.globalPreHigh = max(bar.high, self.globalPreHigh)
        self.globalPreLow = min(bar.low, self.globalPreLow)


    def onBarH1(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineH1的回调"""
        self.writeCtaLog('*' * 20 + 'onBarH1 start' + '*' * 20)
        self.writeCtaLog(self.lineH1.displayLastBar())
        # 未初始化完成
        # self.writeCtaLog(u'MA40:{0}'.format(self.lineH1.lineMa1[-1]))
        # self.maValue = self.lineH1.lineMa1[-1]
        if not self.inited:
            if len(self.lineH1.lineBar) > self.ma + 2:
                self.writeCtaLog('+' * 20 + 'data inited' + '+' * 20)
                self.inited = True
            else:
                return

    def __cancelLogic(self, dt, force=False):
        "撤单逻辑"""

        if len(self.uncompletedOrders) < 1:
            return

        if not self.lastOrderTime:
            self.writeCtaLog(u'异常，上一交易时间为None')
            return

        # 平仓检查时间比开开仓时间需要短一倍
        if (self.pos >= 0 and self.entrust == 1) \
                or (self.pos <= 0 and self.entrust == -1):
            i = 1
        else:
            i = 1  # 原来是2，暂时取消

        canceled = False

        if ((dt - self.lastOrderTime).seconds > self.cancelSeconds / i ) or force:  # 超过设置的时间还未成交

            for order in self.uncompletedOrders.keys():
                self.writeCtaLog(u'{0}超时{1}秒未成交，取消委托单：{2}'.format(dt, (dt - self.lastOrderTime).seconds, order))

                self.cancelOrder(str(order))

                canceled = True

            # 取消未完成的订单
            self.uncompletedOrders.clear()

            if canceled:
                self.entrust = 0
            else:
                self.writeCtaLog(u'异常：没有撤单')


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

    def strToTime(self, t, ms):
        """从字符串时间转化为time格式的时间"""
        hh, mm, ss = t.split(':')
        tt = datetime.time(int(hh), int(mm), int(ss), microsecond=ms)
        return tt

    def saveData(self, id):
        """保存过程数据"""
        # 保存K线
        if not self.backtesting:
            return

    def __save_data(self):
        jsonFileName = self.name + u'.json'
        j = {}
        j['pos'] = self.position.pos
        j['globalPreHigh'] = self.globalPreHigh
        j['globalPreLow'] = self.globalPreLow
        j['maValue'] = self.maValue
        j['long_open'] = self.long_open
        j['long_win'] = self.long_win
        j['long_lose'] = self.long_lose
        j['short_open'] = self.short_open
        j['short_win'] = self.short_win
        j['short_lose'] = self.short_lose
        j['tradingDay'] = self.tradingDay

        with open(jsonFileName, 'w') as f:
            jsonL = json.dumps(j, indent=4)
            f.write(jsonL)

    def __load_data(self):
        jsonFileName = self.name + u'.json'
        data = {}
        if not os.path.isfile(jsonFileName):
            self.__save_data()
        with open(jsonFileName, 'r', encoding='utf8') as f:
            try:
                data['temp'] = json.load(f)
            except Exception:
                self.__save_data()
                return
        if 'tradingDay' in data['temp'].keys():
            if self.tradingDay != data['temp']['tradingDay']:
                self.globalPreHigh = 0  # 初始化前高
                self.globalPreLow = 1000000  # 初始化前低
                self.long_win = 0
                self.long_lose = 0
                self.short_open = 0
                self.short_win = 0
                self.short_lose = 0
            else:
                self.globalPreHigh = data['temp']['globalPreHigh']
                self.globalPreLow = data['temp']['globalPreLow']
                self.long_open = data['temp']['long_open']
                self.long_win = data['temp']['long_win']
                self.long_lose = data['temp']['long_lose']
                self.short_open = data['temp']['short_open']
                self.short_win = data['temp']['short_win']
                self.short_lose = data['temp']['short_lose']

def testRbByTick():

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20170101')

    # 设置回测用的数据结束日期
    engine.setEndDate('20170315')

    # engine.connectMysql()
    engine.setDatabase(dbName='VnTrader_Tick_Db', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['vtSymbol'] = 'rb'
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'G01_LBreaker_RB'
    settings['mode'] = 'tick'
    settings['minDiff'] = 5
    settings['backtesting'] = True
    settings['percentLimit'] = 30

    # 在引擎中创建策略对象
    engine.initStrategy(StrategyLBreaker, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 100000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60*5  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）
    # 开始跑回测
    engine.runBackTestingWithMongoDBTicks('00')

    # 显示回测结果
    engine.showBacktestingResult()

def testRbByBar():
    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为bar
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20180101')

    # 设置回测用的数据结束日期
    engine.setEndDate('20181201')

    engine.setDatabase(dbName='stockcn',symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)     # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))    # 万1
    engine.setSize(10)         # 合约大小

    settings = {}
    settings['vtSymbol'] = 'rb'
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'G01_LBreaker_RB'
    settings['mode'] = 'bar'
    settings['minDiff'] = 5
    settings['backtesting'] = True
    settings['percentLimit'] = 30


    # 在引擎中创建策略对象
    engine.initStrategy(StrategyLBreaker, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False     # True时rb，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 100000      # 设置期初资金
    engine.percentLimit = 30        # 设置资金使用上限比例(%)
    engine.barTimeInterval = 300    # bar的周期秒数，用于csv文件自动减时间

    # 开始跑回测
    engine.runBackTestingWithBarFile('X:/gary/data/2.csv')

    # 显示回测结果
    engine.showBacktestingResult()


# 从csv文件进行回测
if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from vnpy.trader.app.ctaStrategy.ctaBacktesting_he import *
    from vnpy.trader.setup_logger import setup_logger

    setup_logger(
        filename=u'TestLogs/{0}_{1}.log'.format(StrategyLBreaker.className, datetime.now().strftime('%m%d_%H%M')),
        debug=False)
    # 回测螺纹
    testRbByTick()
    #testRbByTick()
