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

    def __init__(self, ctaEngine, setting=None):
        super(StrategyLBreaker, self).__init__(ctaEngine, setting)
        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('minDiff')
        self.paramList.append('shortSymbol')

        # 增加监控变量项目
        self.varList.append('pos')  # 仓位
        self.varList.append('entrust')  # 是否正在委托
        # self.varList.append('globalPreHigh')  # 前高
        # self.varList.append('globalPreLow')  # 前低

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
        self.atr = 10  # 平均波动
        self.policy.addPos = True  # 是否激活加仓策略
        self.policy.addPosOnPips = 1  # 加仓策略1，固定点数（动态ATR）

        self.highPriceInLong = EMPTY_FLOAT  # 成交后，最高价格
        self.lowPriceInShort = EMPTY_FLOAT  # 成交后，最低价格

        # 增加仓位管理模块
        self.position = CtaPosition(self)

        if setting:
            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M5 K线
            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'  # k线名称
            lineM5Setting['barTimeInterval'] = 60 * 5  # K线的Bar时长
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            lineM5Setting['inputPreLen'] = 3   # 前高/前低
            self.lineM5 = CtaLineBar(self, self.onBarM5, lineM5Setting)

            # 创建的H1 K线
            lineH1Setting = {}
            lineH1Setting['name'] = u'H1'  # k线名称
            lineH1Setting['period'] = 'hour'
            lineH1Setting['barTimeInterval'] = 1  # K线的Bar时长
            lineH1Setting['mode'] = CtaLineBar.BAR_MODE
            lineH1Setting['inputMa1Len'] = 30  # 第1条均线
            lineH1Setting['minDiff'] = self.minDiff
            lineH1Setting['shortSymbol'] = self.shortSymbol
            self.lineH1 = CtaLineBar(self, self.onBarH1, lineH1Setting)

            try:
                mode = setting['mode']
                if mode != EMPTY_STRING:
                    self.lineH1.setMode(setting['mode'])
            except KeyError:
                self.lineH1.setMode(self.lineH1.TICK_MODE)

        self.onInit()

    def onInit(self, force=False):
        """初始化 """
        if force:
            self.writeCtaLog(u'策略强制初始化')
            self.inited = False
            self.trading = False                        # 控制是否启动交易
        else:
            self.writeCtaLog(u'策略初始化')
            if self.inited:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        self.pos = EMPTY_INT                 # 初始化持仓
        self.entrust = EMPTY_INT             # 初始化委托状态
        self.globalPreHigh = EMPTY_INT  # 初始化前高
        self.globalPreLow = EMPTY_INT  # 初始化前低

        if not self.backtesting:
            # 这里需要加载前置数据哦。
            if not self.__initDataFromShcifo():
                self.inited = True                   # 更新初始化标识
                self.trading = True                  # 启动交易

        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

    def __initDataFromShcifo(self):
        """从sina初始化5分钟数据"""
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

        self.writeCtaLog(u'停止' )
        self.putEvent()

    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.position.pos))

    def onOrder(self, order):
        """报单更新"""
        self.putEvent()  # 更新监控事件
        pass

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

        # 2、计算交易时间和平仓时间
        self.__timeWindow(self.curDateTime)

        # 推送Tick到lineM5
        self.lineM5.onTick(tick)
        # 推送Tick到lineH1
        self.lineH1.onTick(tick)

        # 首先检查是否是实盘运行还是数据预处理阶段
        self.writeCtaLog('*' * 20 + '首先检查是否是实盘运行还是数据预处理阶段' + '*' * 20)
        if not (self.inited and len(self.lineH1.lineMa1) > 0):
            return

        # 更新最高价和最低价
        if tick.lastPrice > self.globalPreHigh:
            self.globalPreHigh = tick.lastPrice

        if tick.lastPrice < self.globalPreLow:
            self.globalPreLow = tick.lastPrice


    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟K线数据更新（仅用于回测时，从策略外部调用)"""

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
            if len(self.lineH1.lineBar) > 40 + 2:
                self.inited = True
            else:
                return

    def onBarM5(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineM5的回调"""

        # 未初始化完成
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
            if bar.high > self.globalPreHigh:
                self.globalPreHigh = bar.high

            if bar.low < self.globalPreLow:
                self.globalPreLow = bar.low

        # 如果未持仓，检查是否符合开仓逻辑
        if self.tradeWindow and self.position.pos == 0:
            self.writeCtaLog('*' * 20 + 'tradeWindow start' + '*' * 20)
            open_point = EMPTY_INT
            lose_point = EMPTY_INT
            win_point1 = EMPTY_INT
            if bar.close > self.lineH1.lineMa1[-1]:
                if bar.close > self.globalPreHigh:
                    if bar.openInterest > self.lineM5[-1].openInterest * 1.003:
                        if bar.close < self.globalPreLow * 1.015:
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
                            ddRobot.postStart(message)
            if bar.close < self.lineH1.lineMa1[-1]:
                if bar.close < self.globalPreHigh:
                    if bar.openInterest < self.lineM5[-1].openInterest * 0.997:
                        if bar.close > self.globalPreHigh * 0.985:
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
                            ddRobot.postStart(message)

    def onBarH1(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineH1的回调"""
        # self.writeCtaLog('*' * 20 + 'onBarM5 start' + '*' * 20)
        # self.writeCtaLog(self.lineH1.displayLastBar())
        # 未初始化完成
        if not self.inited:
            if len(self.lineH1.lineBar) > 40 + 2:
                self.inited = True
            else:
                return
        else:
            self.writeCtaLog(u'MA40:{0}'.format(self.lineH1.lineMa1[-1]))


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
