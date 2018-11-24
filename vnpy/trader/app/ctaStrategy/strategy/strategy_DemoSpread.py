# encoding: UTF-8

# 首先写系统内置模块
import sys
import os
from datetime import datetime, timedelta, date
from time import sleep
import copy
import logging
import traceback

# 第三方模块
import talib as ta
import math
import numpy
import requests
import execjs

# vntrader基础模块
from vnpy.trader.vtConstant import *

# 然后CTA模块
from vnpy.trader.app.ctaStrategy.ctaTemplate import *
from vnpy.trader.app.ctaStrategy.ctaBase import *
from vnpy.trader.app.ctaStrategy.ctaPolicy import *
from vnpy.trader.app.ctaStrategy.ctaLineBar import *
from vnpy.trader.app.ctaStrategy.ctaPosition import *
from vnpy.trader.app.ctaStrategy.ctaGridTrade import *
from vnpy.trader.app.ctaStrategy.ctaPeriod import *

cta_engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

######################################from##################################
class Strategy_DemoSpread(CtaTemplate):
    """非标准合约的协整套利+网格交易
        # 随机套利，超过标准差4STD时，满足返回1.2STD 达到6个minDiff时，开仓。
        # 开仓后分钟级别判断close是否保持在上轨/下轨，若仍然保持在上轨/下轨外，则止损。
        
        策略限于demo，开仓后的止损，条件判断，需要自行改进
        
    配置参考
        {
          "name": "S_螺纹钢跨期套利",
          "className": "Strategy_DemoSpread",
          "vtSymbol": "rb1705;rb1710",
          "symbol": "rb1705;rb1710",
          "shortSymbol":"RB",
          "Leg1Symbol":"rb1705",
          "Leg2Symbol":"rb1710",
          "baseUpLine":240,
          "baseMidLine":0,
          "baseDnLine":-240,
          "minDiff":1,
          "inputSS":1,
          "height":5,
          "win":10,
          "maxPos":4,
          "maxLots":4,
          "deadLine":"2017-4-20",
          "mode":"tick"
        }

    """
    className = 'Strategy_DemoSpread'
    author = u'李来佳'

    # 策略在外部设置的参数
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    minDiff = 1                # 商品的最小交易单位
    maxPos = 10                # 最大仓位（网格）数量

#----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting=None):
        """Constructor"""
        super(Strategy_DemoSpread, self).__init__(ctaEngine, setting)

        self.paramList.append('inputSS')
        self.paramList.append('Leg1Symbol')       # 近期合约
        self.paramList.append('Leg2Symbol')       # 远期合约
        self.paramList.append('minDiff')
        self.paramList.append('maxPos')
        self.paramList.append('maxLots')
        self.paramList.append('height')           #
        self.paramList.append('win')
        self.paramList.append('baseUpLine')
        self.paramList.append('baseMidLine')    # 基准中轴
        self.paramList.append('baseDnLine')
        self.paramList.append('deadLine')       # 最后开仓期限，超过设置期限就不再开仓
        self.paramList.append('forceClose')     # 强制平仓期限，超过设置期限就强制
        self.paramList.append('volumeList')
        self.paramList.append('autoLock')
        #self.varList.remove('pos')
        self.varList.append('gridpos')
        #self.varList.append('entrust')
        self.varList.append('upGrids')
        self.varList.append('dnGrids')
        self.varList.append('m60_atan')
        self.varList.append('m60_period')
        self.varList.append('m5_atan')
        self.varList.append('m5_period')
        self.varList.append('m1_atan')
        self.varList.append('tradingOpen')

        self.autoLock = False
        self.cancelSeconds = 1                  # 未成交撤单的秒数
        self.activeDayJump = False              # 隔夜跳空处理

        self.curDateTime = None                 # 当前Tick时间
        self.curTick = None                     # 最新的tick

        self.Leg1Symbol = EMPTY_STRING
        self.Leg2Symbol = EMPTY_STRING
        self.lastLeg1Tick = None
        self.lastLeg2Tick = None

        self.firstTrade = True                  # 交易日的首个交易

        # 交易窗口
        self.tradeWindow = False
        # 开市窗口
        self.openWindow = False
        # 收市平仓窗口
        self.closeWindow = False

        # 仓位状态
        self.position = CtaPosition(self)       # 网格交易的仓位：0 表示没有仓位，1 表示持有多头，-1 表示持有空头
        self.position.maxPos = self.maxPos
        self.gridpos = 0

        self.period_position = CtaPosition(self)    # 周期仓位
        self.period_position.maxPos = self.maxPos

        self.lastTradedTime = datetime.now()    # 上一交易时间
        self.deadLine = EMPTY_STRING            # 允许最后的开仓期限（参数，字符串）
        self.deadLineDate = None                # 允许最后的开仓期限（日期类型）
        self.tradingOpen = True                 # 允许开仓
        self.recheckPositions = True

        self.forceClose = EMPTY_STRING  # 强制平仓的日期（参数，字符串）
        self.forceCloseDate = None  # 强制平仓的日期（日期类型）
        self.forceTradingClose = False          # 强制平仓标志

        # 是否完成了策略初始化
        self.inited = False

        self.backtesting = False

        # 初始化时读取的历史数据的起始日期(可以选择外部设置)
        self.startDate = None
        self.policy = CtaPolicy()               # 成交后的执行策略

        self.recheckPositions = True              # 重新提交平仓订单。在每个交易日的下午14点59分时激活，在新的交易日（21点）开始时，重新执行。

        self.volumeList = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        self.height = 4
        self.win = 4
        self.upGrids = EMPTY_STRING          # 做空网格的显示字符串
        self.dnGrids = EMPTY_STRING          # 做多网格的显示字符串
#
        self.baseUpLine = EMPTY_INT             # 网格做空起步线
        self.baseMidLine = EMPTY_INT         # 基准中轴线，区分多空
        self.baseDnLine = EMPTY_INT             # 网格做多起步线

        self.upRate = 1                      # 做空网格间距放大比率
        self.dnRate = 1                      # 做多网格间距放大比率
        self.rebuildUpGrid = False           # 重建网格标志
        self.rebuildDnGrid = False           # 重建网格标志
        self.rebuildGrid = False             # 分钟触发重建网格

        self.maxLots = 10                       # 网格的最大数量#

        self.lineDiff = None                    # 1分钟价差K线
        self.lineRatio = None                   # 1分钟比价K线
        self.lineMD = None                      # 1分钟残差K线


        self.m60_atan = None
        self.m60_period = EMPTY_STRING

        self.m5_atan = None
        self.m5_period = EMPTY_STRING

        self.m1_atan = None

        self.logMsg = EMPTY_STRING              # 临时输出日志变量
        self.delayMission = []  # 延迟的任务
        self.save_orders = []
        self.save_signals = {}

        if setting:

            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M1 Spread K线, = Leg1 - Leg2
            lineDiffSetting = {}
            lineDiffSetting['name'] = u'M1Diff'
            lineDiffSetting['barTimeInterval'] = 60
            lineDiffSetting['inputBollLen'] = 20
            lineDiffSetting['inputBollStdRate'] = 2
            lineDiffSetting['minDiff'] = self.minDiff
            lineDiffSetting['shortSymbol'] = self.shortSymbol
            self.lineDiff = CtaLineBar(self, self.onBar, lineDiffSetting)

            # 创建的M1 Ratio  K线 = Leg2/Leg1
            lineRatioSetting = {}
            lineRatioSetting['name'] = u'M1Ratio'
            lineRatioSetting['barTimeInterval'] = 60
            lineRatioSetting['inputKF'] = True
            lineRatioSetting['minDiff'] = 0.0001
            lineRatioSetting['shortSymbol'] = self.shortSymbol
            self.lineRatio = CtaLineBar(self, self.onBarRatio, lineRatioSetting)

            # 创建的M1 Mean Diff K线 Mean-Leg2
            lineMDSetting = {}
            lineMDSetting['name'] = u'M1MeanDiff'
            lineMDSetting['barTimeInterval'] = 60
            lineMDSetting['inputBollLen'] = 60
            lineMDSetting['inputBollStdRate'] = 1.5
            lineMDSetting['minDiff'] = self.minDiff
            lineMDSetting['shortSymbol'] = self.shortSymbol
            self.lineMD = CtaLineBar(self, self.onBarMeanDiff, lineMDSetting)

            lineM5Setting = {}
            lineM5Setting['name'] = u'M5Ratio'
            lineM5Setting['barTimeInterval'] = 5
            lineM5Setting['period'] = PERIOD_MINUTE
            lineM5Setting['inputRsi1Len'] = 14
            lineM5Setting['inputBollLen'] = 20
            lineM5Setting['inputBollStdRate'] = 1.2
            lineM5Setting['minDiff'] =  0.0001
            lineM5Setting['shortSymbol'] = self.shortSymbol
            self.lineM5 = CtaLineBar(self, self.onBarM5, lineM5Setting)
            self.lineM5.onPeriodChgFunc = self.onM5PeriodChanged

        #self.onInit()

    #----------------------------------------------------------------------
    def onInit(self, force = False):
        """初始化
        从sina上读取近期合约和远期合约，合成价差
        """

        if force:
            self.writeCtaLog(u'策略强制初始化')
            self.inited = False
            self.trading = False                        # 控制是否启动交易
        else:
            self.writeCtaLog(u'策略初始化')
            if self.inited:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        if not self.backtesting:
            # 从sina获取最近5天的数据，初始化K线数据
            if self.shortSymbol.upper() in MARKET_ZJ:

                if not self.__InitZJDataFromSina():
                    self.writeCtaError(u'初始化获取中金所分时数据失败')
                    return
            else:

                if not self.__InitDataFromSina():
                    self.writeCtaError(u'初始化获取分时数据失败')
                    return

        # 初始化持仓相关数据
        self.position.pos = EMPTY_INT
        self.pos = self.position.pos
        self.gridpos = self.position.pos
        self.position.maxPos = self.maxPos

        # 初始化网格
        self.gridHeight = self.height * self.minDiff      # 网格距离跳数*每跳高度
        self.gridWin = self.win * self.minDiff            # 止盈跳数*每跳高度

        if self.baseUpLine == EMPTY_INT:
            self.writeCtaLog(u'初始化baseUpLine为空，缺省设置为50个MinDiff')
            self.baseUpLine = 50 * self.minDiff         # 网格做空起步线
        if self.baseDnLine == EMPTY_INT:
            self.writeCtaLog(u'baseDnLine，缺省设置为-50个MinDiff')
            self.baseDnLine = -50 * self.minDiff        # 网格做多起步线

        self.upLine = self.baseMidLine      #self.baseUpLine     # 网格做空的上轨
        self.dnLine = self.baseMidLine      #self.baseDnLine     # 网格做多的下轨

        # 创建网格交易策略
        self.gt = CtaGridTrade(strategy=self, maxlots=self.maxLots, height=self.gridHeight, win=self.gridWin,
                               vol=self.inputSS, minDiff=self.minDiff)
        # 更新网格仓位策略
        if self.volumeList:
            self.gt.volumeList = self.volumeList
        else:
            self.gt.volumeList = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        # 更新初始化标识和交易标识
        self.inited = True
        self.trading = True                             # 控制是否启动交易
        self.recheckPositions = True

        if self.deadLine != EMPTY_STRING:
            try:
                self.deadLineDate = datetime.strptime(self.deadLine, '%Y-%m-%d')
                if not self.backtesting:
                    dt = datetime.now()
                    if (dt - self.deadLineDate).days >= 0:
                        self.tradingOpen = False
                        self.writeCtaLog(u'日期超过最后开仓日期，不再开仓')
                        if not self.backtesting:
                            self.writeCtaNotification(u'日期超过最后开仓日期{0}，不再开仓'.format(self.deadLine))
            except Exception:
                pass

        if self.forceClose != EMPTY_STRING:
            try:
                self.forceCloseDate = datetime.strptime(self.forceClose, '%Y-%m-%d')
                if not self.backtesting:
                    dt = datetime.now()
                    if (dt - self.forceCloseDate).days >= 0:
                        self.forceTradingClose = True
                        self.writeCtaLog(u'日期超过最后平仓日期，强制平仓')
            except Exception:
                pass

        self.__updatePeriod()
        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

        if not self.backtesting:
            self.writeCtaNotification(u'策略初始化完成,启动交易.')

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'启动')
        self.trading = True

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.uncompletedOrders.clear()
        self.recheckPositions = True

        self.position.clear()
        self.gridpos = self.position.pos
        self.entrust = 0

        self.writeCtaLog(u'保存下网格')
        self.gt.save(direction=DIRECTION_LONG)
        self.writeCtaLog(u'保存上网格')
        self.gt.save(direction=DIRECTION_SHORT)

        self.trading = False
        self.writeCtaLog(u'停止' )
        self.writeCtaNotification(u'停止')
        self.putEvent()

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.position.pos))

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """报单更新"""
        msg = u'orderID:{0},{1},totalVol:{2},tradedVol:{3},offset:{4},price:{5},direction:{6},status:{7}'\
            .format(order.orderID, order.vtSymbol, order.totalVolume,order.tradedVolume, order.offset,
                    order.price, order.direction, order.status)
        if self.backtesting:
            self.writeCtaLog(u'OnOrder()报单更新: {}'.format(msg))
        else:
            self.writeCtaLog(u'{}OnOrder()报单更新: {}'.format(datetime.now().strftime('%H:%M:%S.%f'),msg))

        orderkey = order.gatewayName+u'.'+order.orderID

        if orderkey in self.uncompletedOrders:

            if order.totalVolume == order.tradedVolume:
                # 开仓，平仓委托单全部成交
                self.__onOrderAllTraded(order)

            #elif order.tradedVolume > 0 and not order.totalVolume == order.tradedVolume :
            #    # 委托单部分成交
            #    self.__onOrderPartTraded(order)

            elif order.offset == OFFSET_OPEN and order.status == STATUS_CANCELLED:
                # 开仓委托单被撤销
                self.__onOpenOrderCanceled(order)

            elif order.offset != OFFSET_OPEN and order.status == STATUS_CANCELLED:
                # 平仓委托单被撤销
                self.__onCloseOrderCanceled(order)
            elif order.status == STATUS_REJECTED:

                if order.offset == OFFSET_OPEN:
                    self.writeCtaCritical(u'OnOrder({})委托单开{}被拒，price:{},total:{},traded:{}，status:{}'
                                          .format(order.vtSymbol,order.direction, order.price,order.totalVolume, order.tradedVolume, order.status))
                    self.__onOpenOrderCanceled(order)
                else:
                    self.writeCtaCritical(u'OnOrder({})委托单平{}被拒，price:{},total:{},traded:{}，status:{}'
                                          .format(order.vtSymbol,order.direction,order.price, order.totalVolume, order.tradedVolume, order.status))
                    self.__onCloseOrderCanceled(order)
            else:
                self.writeCtaLog(u'OnOrder()委托单返回，total:{0},traded:{1}'
                                 .format(order.totalVolume, order.tradedVolume,))

        self.__updateGridsDisplay()
        self.pos = self.position.pos
        self.gridpos = self.position.pos
        self.writeCtaLog(u'OnOrder()self.gridpos={0}'.format(self.gridpos))
        self.putEvent()

    def __onOrderAllTraded(self, order):
        """订单的所有成交事件"""
        self.writeCtaLog(u'onOrderAllTraded(),{0},委托单全部完成'.format(order.orderTime ))
        orderkey = order.gatewayName+u'.'+order.orderID

        # 平空仓完成(cover)
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset != OFFSET_OPEN:
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey]['Grid']

            if grid is not None:
                orders = grid.orderRef.split(';')
                if len(orders) >= 2 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:closePrice={0}的{1}平空'.format(grid.closePrice, order.vtSymbol))
                    orders.remove(orderkey)
                    grid.orderRef = orders[0]
                elif len(orders) == 1 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:closePrice={0}的{1}平空'.format(grid.closePrice, order.vtSymbol))
                    grid.orderRef = EMPTY_STRING
                    grid.orderStatus = False
                    grid.openStatus = False
                    grid.closeStatus = False
                    grid.tradedVolume = EMPTY_INT
                    grid.openDatetime = EMPTY_STRING
                    # 更新仓位
                    direction = grid.direction
                    if direction == DIRECTION_LONG:
                        self.writeCtaLog(u'更新仓位，正套网格平多仓{0}手'.format(grid.volume))
                        self.position.closePos(DIRECTION_SHORT, vol=grid.volume)
                        if not grid.reuse:
                            if len(self.gt.dnGrids)>1:
                                self.writeCtaLog(u'移除网格{0},{1}'.format(grid.direction,grid.openPrice))
                                try:
                                    self.gt.dnGrids.remove(grid)
                                except:
                                    self.writeCtaError(u'未能移除做多网格')
                            else:
                                grid.openPrice = -99999
                    else:
                        self.writeCtaLog(u'更新仓位，反套网格平空仓{0}手'.format(grid.volume))
                        self.position.closePos(DIRECTION_LONG, vol=grid.volume)
                        if not grid.reuse:
                            if len(self.gt.upGrids)>1:
                                self.writeCtaLog(u'移除网格{0},{1}'.format(grid.direction, grid.openPrice))
                                try:
                                    self.gt.upGrids.remove(grid)
                                except:
                                    self.writeCtaError(u'未能移除做空网格')
                            else:
                                grid.openPrice = 99999
                    self.entrust = 0
                    self.gridpos = self.position.pos
                    self.gt.save(direction=direction)

                    if abs(self.position.pos) / self.inputSS > 5:
                        self.writeCtaLog(u'持仓超过5个，提升第一个网格的平仓价')
                        self.__resubmitFirstGrid(direction=direction, lastVolume=order.tradedVolume)

                else:
                    self.writeCtaError(u'异常，__onOrderAllTraded,cover() orderRef:{0}对应的网格内，Ref字段:{1}'.format(orderkey, grid.orderRef))
            else:
                self.writeCtaError(u'异常，__onOrderAllTraded.cover()找不到orderRef:{0}对应的网格'.format(orderkey))

        # 平多仓完成(sell)
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset != OFFSET_OPEN:
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey]['Grid']
            if grid is not None:
                orders = grid.orderRef.split(';')
                if len(orders) >= 2 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:closePrice={0}的{1}平多'.format(grid.closePrice, order.vtSymbol))
                    orders.remove(orderkey)
                    grid.orderRef = orders[0]
                elif len(orders) == 1 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:closePrice={0}的{1}平多'.format(grid.closePrice, order.vtSymbol))
                    grid.orderRef = EMPTY_STRING
                    grid.orderStatus = False
                    grid.openStatus = False
                    grid.closeStatus = False
                    grid.tradedVolume = EMPTY_INT
                    grid.openDatetime = EMPTY_STRING
                    # 更新仓位
                    direction = grid.direction
                    if direction == DIRECTION_LONG: # 网格的开仓方向是开多
                        self.writeCtaLog(u'更新仓位，正套网格平多仓{0}手'.format(grid.volume))
                        self.position.closePos(DIRECTION_SHORT, vol=grid.volume)
                        if not grid.reuse:
                            if len(self.gt.dnGrids) > 1:
                                self.writeCtaLog(u'移除网格{0},{1}'.format(grid.direction,grid.openPrice))
                                try:
                                    self.gt.dnGrids.remove(grid)
                                except:
                                    self.writeCtaError(u'未能移除做多网格')
                            else:
                                grid.openPrice = -99999
                    else:                           # 网格的开仓方向是开空
                        self.writeCtaLog(u'更新仓位，反套网格平空仓{0}手'.format(grid.volume))
                        self.position.closePos(DIRECTION_LONG, vol=grid.volume)
                        # 不是重用网格，非最后一个网格，移除
                        if not grid.reuse:
                            if len(self.gt.upGrids)>1:
                                self.writeCtaLog(u'移除网格{0},{1}'.format(grid.direction, grid.openPrice))
                                try:
                                    self.gt.upGrids.remove(grid)
                                except:
                                    self.writeCtaError(u'未能移除做空网格')
                            else:
                                grid.openPrice = 99999

                    self.gridpos = self.position.pos
                    self.entrust = 0
                    self.gt.save(direction=direction)

                    if abs(self.position.pos) / self.inputSS > 5:
                        self.writeCtaLog(u'持仓超过5个，提升第一个网格的平仓价')
                        self.__resubmitFirstGrid(direction=direction, lastVolume=order.tradedVolume)

                else:
                    self.writeCtaError(u'异常，__onOrderAllTraded.sell()orderRef:{0}对应的网格内，Ref字段:{1}'.format(orderkey, grid.orderRef))
            else:
                self.writeCtaError(u'异常，__onOrderAllTraded.sell()找不到orderRef:{0}对应的网格'.format(orderkey))

        # 开多仓完成（buy）
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset == OFFSET_OPEN:
            self.writeCtaLog(u'{0}开多仓完成'.format(order.vtSymbol))
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey]['Grid']

            if grid is not None:
                orders = grid.orderRef.split(';')
                if len(orders) >= 2 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:Grid.OpenPrice={0}的{1}开多{2}'.format(grid.openPrice, order.vtSymbol, order.price))
                    orders.remove(orderkey)
                    grid.orderRef = orders[0]
                elif len(orders) == 1 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:Grid.OpenPrice={0}的{1}开多{2}'.format(grid.openPrice, order.vtSymbol, order.price))
                    grid.orderRef = EMPTY_STRING
                    grid.openStatus = True
                    grid.orderStatus = False
                    grid.openDatetime = self.curDateTime
                    # 更新仓位
                    self.writeCtaLog(u'更新仓位，网格{0}仓{1}手'.format(grid.direction, grid.volume))
                    self.position.openPos(grid.direction, vol=grid.volume, price=grid.openPrice)
                    self.pos = self.position.pos
                    self.gridpos = self.position.pos
                    self.entrust = 0

                else:
                    self.writeCtaError(u'{0}开多仓完成（buy），{1}不在对应的网格Ref字段:{2}，无法更新'.format(order.vtSymbol, orderkey, grid.orderRef))

                direction = grid.direction
                # 在本策略中，合并网格
                self.gt.combineOpenedGrids(direction=direction)

                self.gt.save(direction=direction)
            else:
                self.writeCtaError(u'{0}开多仓完成（buy），找不到{1}对应的网格'.format(order.vtSymbol, orderkey))

        # 开空仓完成(Short)
        if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
            self.writeCtaLog(u'开空仓完成'.format(order.vtSymbol))
            # 通过orderID，找到对应的网格
            grid = self.uncompletedOrders[orderkey]['Grid']

            if grid is not None:
                orders = grid.orderRef.split(';')
                if len(orders) >= 2 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:Grid.OpenPrice={0}的{1}开空{2}'.format(grid.openPrice, order.vtSymbol,order.price))
                    orders.remove(orderkey)
                    grid.orderRef = orders[0]
                elif len(orders) == 1 and orderkey in orders:
                    self.writeCtaLog(u'更新网格:Grid.OpenPrice={0}的{1}开空{2}'.format(grid.openPrice, order.vtSymbol,order.price))
                    grid.orderRef = EMPTY_STRING
                    grid.orderStatus = False
                    grid.openStatus = True
                    grid.openDatetime = self.curDateTime
                    # 更新仓位
                    self.writeCtaLog(u'更新仓位，网格{0}仓{1}手'.format(grid.direction, grid.volume))
                    self.position.openPos(grid.direction, vol=grid.volume, price=grid.openPrice)
                    self.pos = self.position.pos
                    self.gridpos = self.position.pos
                    self.entrust = 0
                else:
                    self.writeCtaError(u'{0}开空仓完成(Short)，{1}不在对应的网格Ref:{2}内，无法更新'.format(order.vtSymbol, orderkey, grid.orderRef))

                direction = grid.direction
                # 在本策略中，合并网格
                self.gt.combineOpenedGrids(direction=direction)

                self.gt.save(direction=direction)

            else:
                self.writeCtaError(u'{0}开空仓完成(Short)，找不到{01}对应的网格'.format(order.vtSymbol, orderkey))
        try:
            del self.uncompletedOrders[orderkey]
        except Exception as ex:
            self.writeCtaError(u'onOrder uncompletedOrders中找不到{0}委托单{1}'.format(order.vtSymbol, orderkey))

    def __onOrderPartTraded(self, order):
        """订单部分成交"""
        self.writeCtaLog(u'{} onOrderPartTraded,{}委托单部分完成,开{},成交{}'.format(order.orderTime,order.vtSymbol,order.totalVolume, order.tradedVolume ))
        orderkey = order.gatewayName+u'.'+order.orderID
        if orderkey in self.uncompletedOrders:
            self.uncompletedOrders[orderkey]['TradedVolume'] = order.tradedVolume
        else:
            self.writeCtaError(u'PartTraded uncompletedOrders中找不到{0}委托单{1}'.format(order.vtSymbol, orderkey))

    def __onOpenOrderCanceled(self, order):
        """委托开仓单撤销"""
        """这里要特殊处理拒单情况"""
        self.writeCtaWarning(u'{},__onOpenOrderCanceled(),{}委托开仓单已撤销,开{},成交{}，未成交{}'
                             .format(datetime.now().strftime('%H:%M:%S.%f'), order.vtSymbol,order.totalVolume,order.tradedVolume, order.totalVolume - order.tradedVolume))

        orderkey = order.gatewayName+u'.'+order.orderID

        if orderkey not in self.uncompletedOrders:
            self.writeCtaError(u'{0}__onOrderPartTraded()不在未完成的委托单中。'.format(orderkey))
            return

        # 回测时不需要执行后续追单
        if self.backtesting:
            return

        old_order = self.uncompletedOrders[orderkey]
        old_order['TradedVolume'] = order.tradedVolume
        order_time = old_order['OrderTime']
        order_symbol = copy.copy(old_order['SYMBOL'])
        order_volume = old_order['Volume'] - old_order['TradedVolume']
        if order_volume <=0:
            self.writeCtaError(u'__onOrderPartTraded {}{}重新开仓数量为{}，不再开仓'.format(orderkey,order_symbol,order_volume))
            del self.uncompletedOrders[orderkey]
            return

        order_price = old_order['Price']
        order_priceType = old_order['PriceType']
        order_retry = old_order['Retry']
        if order_retry > 20:
            self.writeCtaCritical(u'__onOrderPartTraded {}/{}手， 重试开仓次数{}>20'.format(order_symbol,order_volume,order_retry))
            del self.uncompletedOrders[orderkey]
            return
        order_retry += 1

        if old_order['DIRECTION'] == DIRECTION_LONG and order_priceType == PRICETYPE_FAK:
            # 更新网格交易器
            grid = old_order['Grid']
            if order_symbol == self.Leg1Symbol:
                buyPrice = max(self.lastLeg1Tick.askPrice1, self.lastLeg1Tick.lastPrice,order_price) + self.minDiff
            else:
                buyPrice = max(self.lastLeg2Tick.askPrice1, self.lastLeg2Tick.lastPrice,order_price) + self.minDiff

            # 发送委托
            orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_BUY, buyPrice, order_volume,strategy=self,priceType=PRICETYPE_FAK)
            if orderID is None or len(orderID) == 0:
                self.writeCtaError(u'重新提交{0} {1}手开多单{2}失败'.format(order_symbol, order_volume, buyPrice))
                return

            grid.orderRef = grid.orderRef.replace(orderkey, orderID)
            if buyPrice > order_price:
                # 修正止盈点位
                if grid.direction == DIRECTION_SHORT:
                    grid.closePrice -= (buyPrice - order_price)
                else:
                    grid.closePrice += (buyPrice - order_price)

            # 重新添加开空委托单
            self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_LONG,
                                               'OFFSET': OFFSET_OPEN, 'Volume': order_volume,
                                               'Price': buyPrice, 'TradedVolume': EMPTY_INT,
                                               'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': order_retry}
            self.gt.save(direction=grid.direction)
            del self.uncompletedOrders[orderkey]

        if old_order['DIRECTION'] == DIRECTION_SHORT and order_priceType == PRICETYPE_FAK:
            grid = old_order['Grid']
            if order_symbol == self.Leg1Symbol:
                shortPrice = min(self.lastLeg1Tick.bidPrice1, self.lastLeg1Tick.lastPrice, order_price) - self.minDiff
            else:
                shortPrice = min(self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.lastPrice, order_price) - self.minDiff

            # 发送委托
            orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_SHORT, shortPrice, order_volume, strategy=self,priceType=PRICETYPE_FAK)
            if orderID is None or len(orderID) == 0:
                self.writeCtaError(u'重新提交{0} {1}手开空单{2}失败'.format(order_symbol, order_volume, shortPrice))
                return

            # 更新网格的委托单
            grid.orderRef = grid.orderRef.replace(orderkey, orderID)
            if shortPrice < order_price:
                # 修正止盈点位
                if grid.direction == DIRECTION_SHORT:
                    grid.closePrice -= (order_price - shortPrice)
                else:
                    grid.closePrice += (order_price - shortPrice)

            # 重新添加开空委托单
            self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_SHORT,
                                               'OFFSET': OFFSET_OPEN, 'Volume': order_volume,
                                               'Price': shortPrice, 'TradedVolume': EMPTY_INT,
                                               'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': order_retry}
            self.gt.save(direction=grid.direction)
            del self.uncompletedOrders[orderkey]

        self.__updateGridsDisplay()

    def __onCloseOrderCanceled(self, order):
        """委托平仓单撤销"""
        self.writeCtaLog(u'{} __onCloseOrderCanceled(),{}委托平仓单已撤销，委托数:{},成交数:{},未成交:{}'
                         .format(datetime.now().strftime('%H:%M:%S.%f'),
                                 order.vtSymbol,
                                 order.totalVolume,
                                 order.tradedVolume,
                                 order.totalVolume - order.tradedVolume))

        orderkey = order.gatewayName + u'.' + order.orderID

        if orderkey not in self.uncompletedOrders:
            self.writeCtaError(u'{0}__onCloseOrderCanceled()不在未完成的委托单中。'.format(orderkey))
            return

        # 回测时不需要执行后续追单
        if self.backtesting:
            return

        old_order = self.uncompletedOrders[orderkey]
        old_order['TradedVolume'] = order.tradedVolume
        order_time = old_order['OrderTime']
        order_symbol = copy.copy(old_order['SYMBOL'])
        order_volume = old_order['Volume'] - old_order['TradedVolume']
        if order_volume <=0:
            self.writeCtaError(u'__onCloseOrderCanceled {}{}重新平仓数量为{}，不再开仓'.format(orderkey,order_symbol,order_volume))
            del self.uncompletedOrders[orderkey]
            return

        order_price = old_order['Price']
        order_priceType = old_order['PriceType']
        order_retry = old_order['Retry']
        if order_retry > 50:
            self.writeCtaCritical(
                u'__onCloseOrderCanceled {}/{}手,价格:{}， 重试平仓次数{}>20'.format(order_symbol, order_volume,order_price,order_retry))
            del self.uncompletedOrders[orderkey]
            return
        order_retry += 1

        if old_order['DIRECTION'] == DIRECTION_LONG and order_priceType == PRICETYPE_FAK:
            # 更新网格交易器
            grid = old_order['Grid']
            if order_symbol == self.Leg1Symbol:
                coverPrice = max(self.lastLeg1Tick.askPrice1, self.lastLeg1Tick.lastPrice, order_price) + self.minDiff
            else:
                coverPrice = max(self.lastLeg2Tick.askPrice1, self.lastLeg2Tick.lastPrice, order_price) + self.minDiff

            # 发送委托
            orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_COVER, coverPrice, order_volume, strategy=self,priceType=PRICETYPE_FAK)
            if orderID is None:
                self.writeCtaError(u'重新提交{0} {1}手平空单{2}失败'.format(order_symbol, order_volume, coverPrice))
                return

            grid.orderRef = grid.orderRef.replace(orderkey, orderID)
            # 重新添加平空委托单
            self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_LONG,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': order_volume,
                                               'TradedVolume': EMPTY_INT,
                                               'Price': coverPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': order_retry}

            self.gt.save(direction=grid.direction)
            del self.uncompletedOrders[orderkey]

        if old_order['DIRECTION'] == DIRECTION_SHORT and order_priceType == PRICETYPE_FAK:
            grid = old_order['Grid']
            if order_symbol == self.Leg1Symbol:
                sellPrice = min(self.lastLeg1Tick.bidPrice1, self.lastLeg1Tick.lastPrice, order_price) - self.minDiff
            else:
                sellPrice = min(self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.lastPrice, order_price) - self.minDiff
            # 发送委托
            orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_SELL, sellPrice, order_volume, strategy=self,priceType=PRICETYPE_FAK)

            if orderID is None or len(orderID) == 0:
                self.writeCtaError(u'重新提交{0} {1}手平多单{2}失败'.format(order_symbol, order_volume, sellPrice))
                return

            # 更新网格的委托单
            grid.orderRef = grid.orderRef.replace(orderkey, orderID)

            # 重新添加平多委托单
            self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_SHORT,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': order_volume,
                                               'TradedVolume': EMPTY_INT,
                                               'Price': sellPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry':order_retry}

            self.gt.save(direction=grid.direction)
            del self.uncompletedOrders[orderkey]

        self.__updateGridsDisplay()

    # ----------------------------------------------------------------------
    def onStopOrder(self, orderRef):
        """停止单更新"""
        self.writeCtaLog(u'{0},停止单触发，orderRef:{1}'.format(self.curDateTime, orderRef))
        pass

    # ----------------------------------------------------------------------
    def __combineTick(self, tick):
        """合并两腿合约，成为套利合约"""

        combinable = False

        if tick.vtSymbol == self.Leg1Symbol:
            # leg1合约
            self.lastLeg1Tick = tick
            if self.lastLeg2Tick is not None:
                if self.lastLeg1Tick.datetime == self.lastLeg2Tick.datetime:
                    combinable = True
        elif tick.vtSymbol == self.Leg2Symbol:
            # leg2合约
            self.lastLeg2Tick = tick
            if self.lastLeg1Tick is not None:
                if self.lastLeg2Tick.datetime == self.lastLeg1Tick.datetime:
                    combinable = True

        # 不能合并
        if not combinable:
            return None, None, None

        spread_tick = CtaTickData()
        spread_tick.vtSymbol = self.vtSymbol
        spread_tick.symbol = self.symbol

        spread_tick.datetime = tick.datetime
        spread_tick.date = tick.date
        spread_tick.time = tick.time

        # 以下情况，基本为单腿涨跌停，不合成价差Tick
        if (self.lastLeg1Tick.askPrice1 == float('1.79769E308') or self.lastLeg1Tick.askPrice1 == 0 or self.lastLeg1Tick.bidPrice1 == self.lastLeg1Tick.upperLimit) and self.lastLeg1Tick.askVolume1 == 0:
            self.writeCtaLog(u'leg1:{0}涨停{1}，不合成价差Tick'.format(self.lastLeg1Tick.vtSymbol,self.lastLeg1Tick.bidPrice1))
            return None, None, None
        if (self.lastLeg1Tick.bidPrice1 == float('1.79769E308') or self.lastLeg1Tick.bidPrice1 == 0 or self.lastLeg1Tick.askPrice1 == self.lastLeg1Tick.lowerLimit) and self.lastLeg1Tick.bidVolume1 == 0:
            self.writeCtaLog(u'leg1:{0}跌停{1}，不合成价差Tick'.format(self.lastLeg1Tick.vtSymbol, self.lastLeg1Tick.askPrice1))
            return None, None, None
        if (self.lastLeg2Tick.askPrice1 == float('1.79769E308') or self.lastLeg2Tick.askPrice1 == 0 or self.lastLeg2Tick.bidPrice1 == self.lastLeg2Tick.upperLimit) and self.lastLeg2Tick.askVolume1 == 0:
            self.writeCtaLog(u'leg2:{0}涨停{1}，不合成价差Tick'.format(self.lastLeg2Tick.vtSymbol, self.lastLeg2Tick.bidPrice1))
            return None, None, None
        if (self.lastLeg2Tick.bidPrice1 == float('1.79769E308') or self.lastLeg2Tick.bidPrice1 == 0 or self.lastLeg2Tick.askPrice1 == self.lastLeg2Tick.lowerLimit) and self.lastLeg2Tick.bidVolume1 == 0:
            self.writeCtaLog(u'leg2:{0}跌停{1}，不合成价差Tick'.format(self.lastLeg2Tick.vtSymbol, self.lastLeg2Tick.askPrice1))
            return None, None, None

        # 叫卖价差=leg1.askPrice1 - leg2.bidPrice1，volume为两者最小
        spread_tick.askPrice1 = self.lastLeg1Tick.askPrice1 - self.lastLeg2Tick.bidPrice1
        spread_tick.askVolume1 = min(self.lastLeg1Tick.askVolume1, self.lastLeg2Tick.bidVolume1)

        # 叫买价差=leg1.bidPrice1 - leg2.askPrice1，volume为两者最小
        spread_tick.bidPrice1 = self.lastLeg1Tick.bidPrice1 - self.lastLeg2Tick.askPrice1
        spread_tick.bidVolume1 = min(self.lastLeg1Tick.bidVolume1, self.lastLeg2Tick.askVolume1)

        # 比率tick
        ratio_tick = copy.copy(spread_tick)
        ratio_tick.askPrice1 = self.lastLeg1Tick.askPrice1 / self.lastLeg2Tick.bidPrice1
        ratio_tick.bidPrice1 = self.lastLeg1Tick.bidPrice1 / self.lastLeg2Tick.askPrice1
        ratio_tick.lastPrice = (ratio_tick.askPrice1 + ratio_tick.bidPrice1) / 2

        # 残差tick
        ratio = ratio_tick.lastPrice
        if len(self.lineRatio.lineStateMean) > 0:
            ratio = self.lineRatio.lineStateMean[-1]

        mean_tick = copy.copy(spread_tick)
        mean_tick.askPrice1 = self.lastLeg1Tick.askPrice1 / ratio - self.lastLeg2Tick.bidPrice1
        mean_tick.bidPrice1 = self.lastLeg1Tick.bidPrice1 / ratio - self.lastLeg2Tick.askPrice1
        mean_tick.lastPrice = (mean_tick.askPrice1 + mean_tick.bidPrice1) / 2

        return spread_tick, ratio_tick, mean_tick

    def __checkLiquidity(self):
        """检查流动性缺失"""
        if not self.lastLeg1Tick.bidPrice1 <= self.lastLeg1Tick.lastPrice <= self.lastLeg1Tick.askPrice1 and self.lastLeg1Tick.volume > 0:
            self.writeCtaLog(u'流动性缺失导致leg1最新价{0} /V:{1}超出买1 {2}卖1 {3}范围,'
                             .format(self.lastLeg1Tick.lastPrice,self.lastLeg1Tick.volume,
                                     self.lastLeg1Tick.bidPrice1,self.lastLeg1Tick.askPrice1))
            return False

        if not self.lastLeg2Tick.bidPrice1 <= self.lastLeg2Tick.lastPrice <= self.lastLeg2Tick.askPrice1 and self.lastLeg2Tick.volume >0:
            self.writeCtaLog(u'流动性缺失导致leg2最新价{0} /V:{1}超出买1 {2}卖1 {3}范围,'
                             .format(self.lastLeg2Tick.lastPrice, self.lastLeg2Tick.volume,
                                     self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.askPrice1))
            return False

        return True

    def __checkNearMaxNorMin(self):
        """检查当前价与涨跌停价格的距离是否太近"""
        if self.backtesting:
            return False

        # leg1 接近涨停价（10个minDiff以内)
        if self.lastLeg1Tick.upperLimit > EMPTY_FLOAT and self.lastLeg1Tick.askPrice1 + 10* self.minDiff > self.lastLeg1Tick.upperLimit:
            self.writeCtaLog(u'Leg1 askPrice1{} 接近涨停价{}'.format(self.lastLeg1Tick.askPrice1, self.lastLeg1Tick.upperLimit))
            return True
        # leg1 接近跌停价（10个minDiff 以内）
        if self.lastLeg1Tick.lowerLimit > EMPTY_FLOAT and self.lastLeg1Tick.bidPrice1 - 10 * self.minDiff < self.lastLeg1Tick.lowerLimit:
            self.writeCtaLog(
                u'Leg1 askPrice1{} 接近跌停价{}'.format(self.lastLeg1Tick.bidPrice1, self.lastLeg1Tick.upperLimit))
            return True

        # leg2 接近涨停价（10个minDiff以内)
        if self.lastLeg2Tick.upperLimit > EMPTY_FLOAT and self.lastLeg2Tick.askPrice1 + 10 * self.minDiff > self.lastLeg2Tick.upperLimit:
            self.writeCtaLog(
                u'Leg2 askPrice1{} 接近涨停价{}'.format(self.lastLeg2Tick.askPrice1, self.lastLeg2Tick.upperLimit))
            return True

        # leg2 接近跌停价（10个minDiff 以内）
        if self.lastLeg2Tick.lowerLimit > EMPTY_FLOAT and self.lastLeg2Tick.bidPrice1 - 10 * self.minDiff < self.lastLeg2Tick.lowerLimit:
            self.writeCtaLog(
                u'Leg2 bidPrice1{} 接近跌停价{}'.format(self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.upperLimit))
            return True

        return False

    def __shortGrid(self, spread_tick,grid):
        # 开空网格

        if self.position.avaliablePos2Add() < 1:
            msg = u'持空仓数量已满，不再开仓'
            if msg != self.logMsg:
                self.logMsg = msg
                self.writeCtaLog(msg)
            return

        if not self.__checkAccountLimit():
            msg = u'资金占用超过限制值，不开仓'
            if msg != self.logMsg:
                self.logMsg = msg
                self.writeCtaLog(msg)
            return

        # 止损价为M5上轨
        grid.stopPrice = spread_tick.bidPrice1 + 2 * self.gridHeight

        # 调用套利下单指令
        ref = self.__arbShort(grid)
        if ref is not None and len(ref) > 0:
            self.writeCtaLog(u'开空委托单号{0}'.format(ref))
            grid.orderRef = ref
            grid.orderStatus = True
            self.gt.upGrids.append(grid)
        else:
            self.writeCtaLog(u'开空委托单失败:{0},v:{1}'.format(grid.openPrice, grid.volume))

    def __longGrid(self,spread_tick, grid):
        if self.position.avaliablePos2Add() < 1:
            msg = u'持多仓数量已满，不再开多仓'
            if msg != self.logMsg:
                self.logMsg = msg
                self.writeCtaLog(msg)
            return

        if not self.__checkAccountLimit():
            msg = u'资金占用超过限制值，不开仓'
            if msg != self.logMsg:
                self.logMsg = msg
                self.writeCtaLog(msg)
            return

        grid.stopPrice = spread_tick.askPrice1 - 2 * self.gridHeight

        ref = self.__arbBuy(grid)
        if ref is not None and len(ref) > 0:
            self.writeCtaLog(u'开多委托单号{0}'.format(ref))
            grid.orderRef= ref
            grid.orderStatus = True
            self.gt.dnGrids.append(grid)
        else:
            self.writeCtaLog(u'开多委托单失败:{0},v:{1}'.format(grid.openPrice, grid.volume))

    # ----------------------------------------------------------------------
    def __arbShort(self, grid, force=False):
        """非标准合约的套利反套（开空）指令"""
        self.writeCtaLog(u'套利价差反套（开空）单,price={0},volume={1}'.format(grid.openPrice, grid.volume))

        if not self.trading:
            self.writeCtaLog(u'停止状态，不开仓')
            return None

        if self.forceTradingClose:
            self.writeCtaLog(u'强制平仓日，不开仓')
            return None

        # 检查流动性缺失
        if not self.__checkLiquidity() and not force: return

        # 检查涨跌停距离
        if self.__checkNearMaxNorMin():
            return None

        bidPrice = self.lastLeg1Tick.bidPrice1 - self.lastLeg2Tick.askPrice1

        if self.lastLeg1Tick.bidPrice1 >= self.lastLeg1Tick.lastPrice:
            if self.lastLeg1Tick.bidVolume1 < 3:
                shortPrice = self.lastLeg1Tick.lastPrice - 2*self.minDiff
            elif self.lastLeg1Tick.bidVolume1 < 10:
                shortPrice = self.lastLeg1Tick.lastPrice - self.minDiff
            else:
                shortPrice = self.lastLeg1Tick.lastPrice
        else:
            if self.lastLeg1Tick.bidVolume1 < 10 or self.lastLeg1Tick.bidVolume1 <= grid.volume:
                shortPrice = self.lastLeg1Tick.bidPrice1 - self.minDiff
            else:
                shortPrice = self.lastLeg1Tick.bidPrice1

        if self.lastLeg2Tick.askPrice1 <= self.lastLeg2Tick.lastPrice:
            if self.lastLeg2Tick.askVolume1 < 3:
                buyPrice = self.lastLeg2Tick.lastPrice+2*self.minDiff
            elif self.lastLeg2Tick.askVolume1 < 10:
                buyPrice = self.lastLeg2Tick.lastPrice + self.minDiff
            else:
                buyPrice = self.lastLeg2Tick.lastPrice
        else:
            if self.lastLeg2Tick.askVolume1 < 10 or self.lastLeg2Tick.bidVolume1 <= grid.volume:
                buyPrice = self.lastLeg2Tick.askPrice1 + self.minDiff
            else:
                buyPrice = self.lastLeg2Tick.askPrice1

        if bidPrice < grid.openPrice:
            self.writeCtaLog(u'实际价差{0}不满足:{1}'.format(bidPrice, grid.openPrice))
            return None

        if (shortPrice - buyPrice + self.minDiff) < grid.openPrice:
            self.writeCtaLog(u'买卖价差{0}不满足:{1}'.format(shortPrice - buyPrice + self.minDiff, grid.openPrice))
            return None

        if shortPrice - buyPrice !=grid.openPrice:
            grid.openPrice = shortPrice - buyPrice
            #grid.closePrice = grid.openPrice - self.gridHeight

        # 回测模式下，保存order
        if self.backtesting:
            save_order = {"datetime": self.curDateTime.strftime('%Y-%m-%d %H:%M:%S'),
                          "direction": 'short',
                          "offset": 'open',
                          "price": shortPrice - buyPrice,
                          "volume": grid.volume,
                          'type': grid.type,
                          'force': 'true' if force else 'false'
                          }
            self.save_orders.append(save_order)

        # 开空leg1
        orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_SHORT, shortPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
        if orderID is None or len(orderID) == 0:
            self.writeCtaError(u'ArbShort()，Leg1 {0}开空仓{1}手失败，委托价:{2}'.format(self.Leg1Symbol,grid.volume,shortPrice))
            return None
        orders = orderID
        self.uncompletedOrders[orderID] = {'SYMBOL':self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
                                           'OFFSET': OFFSET_OPEN, 'Volume': grid.volume,
                                           'Price': shortPrice, 'TradedVolume': EMPTY_INT,
                                           'OrderTime': self.curDateTime,
                                           'Grid': grid,
                                           'PriceType':PRICETYPE_FAK,
                                           'Retry': 0}

        # 开多leg2
        orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_BUY, buyPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
        if orderID is None or len(orderID) == 0:
            self.writeCtaCritical(u'ArbShort，Leg2 {0}开多仓手{1}失败,委托价:{2}'.format(self.Leg2Symbol,grid.volume,buyPrice))
            # 这里要不要处理之前的Leg1开仓？（放在后面cancelorder中处理）
            return None
        orders = orders + ';' + orderID
        self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_LONG,
                                           'OFFSET': OFFSET_OPEN, 'Volume': grid.volume,
                                           'Price': buyPrice, 'TradedVolume': EMPTY_INT,
                                           'OrderTime': self.curDateTime,
                                           'Grid': grid,
                                           'PriceType':PRICETYPE_FAK,
                                           'Retry': 0}
        grid.orderStatus = True
        grid.orderDatetime = self.curDateTime

        self.entrust = -1
        self.writeCtaLog(u'arb short Orders：{0}'.format(orders))
        return orders

    # ----------------------------------------------------------------------
    def __arbBuy(self,grid, force=False):
        """非标准合约的套利正套（开多）指令"""
        self.writeCtaLog(u'套利价差正套（开多）单,price={0},volume={1}'.format(grid.openPrice, grid.volume))
        if not self.trading:
            self.writeCtaLog(u'停止状态，不开仓')
            return None
        if self.forceTradingClose:
            self.writeCtaLog(u'强制平仓日，不开仓')
            return None

        # 检查流动性缺失
        if not self.__checkLiquidity() and not force: return

        # 检查涨跌停距离
        if self.__checkNearMaxNorMin():
            return None

        askPrice = self.lastLeg1Tick.askPrice1 - self.lastLeg2Tick.bidPrice1
        if self.lastLeg1Tick.askPrice1 <= self.lastLeg1Tick.lastPrice:
            if self.lastLeg1Tick.askVolume1 < 3:
                buyPrice = self.lastLeg1Tick.lastPrice+2*self.minDiff
            elif self.lastLeg1Tick.askVolume1 < 10:
                buyPrice = self.lastLeg1Tick.lastPrice + self.minDiff
            else:
                buyPrice = self.lastLeg1Tick.lastPrice
        else:
            if self.lastLeg1Tick.askVolume1 < 10 or self.lastLeg1Tick.bidVolume1 <= grid.volume:
                buyPrice = self.lastLeg1Tick.askPrice1 + self.minDiff
            else:
                buyPrice = self.lastLeg1Tick.askPrice1

        if self.lastLeg2Tick.bidPrice1 >= self.lastLeg2Tick.lastPrice:
            if self.lastLeg2Tick.bidVolume1 < 3:
                shortPrice = self.lastLeg2Tick.lastPrice - 2*self.minDiff
            elif self.lastLeg2Tick.bidVolume1 < 10:
                shortPrice = self.lastLeg2Tick.lastPrice - self.minDiff
            else:
                shortPrice = self.lastLeg2Tick.lastPrice
        else:
            if self.lastLeg2Tick.bidVolume1 < 10 or self.lastLeg2Tick.bidVolume1 <= grid.volume:
                shortPrice = self.lastLeg2Tick.bidPrice1 - self.minDiff
            else:
                shortPrice = self.lastLeg2Tick.bidPrice1

        if askPrice > grid.openPrice and not force:
            self.writeCtaLog(u'实际价差{0}不满足:{1}'.format(askPrice, grid.openPrice))
            return None

        if (buyPrice - shortPrice - self.minDiff) > grid.openPrice and not force:
            self.writeCtaLog(u'对价价差{0}不满足:{1}'.format((buyPrice - shortPrice - self.minDiff), grid.openPrice))
            return None

        if buyPrice - shortPrice != grid.openPrice:
            grid.openPrice = buyPrice - shortPrice
            #grid.closePrice = grid.openPrice + self.gridHeight

        # 回测模式下，保存order
        if self.backtesting:
            save_order = {"datetime": self.curDateTime.strftime('%Y-%m-%d %H:%M:%S'),
                          "direction": 'long',
                          "offset": 'open',
                          "price": buyPrice - shortPrice,
                          "volume": grid.volume,
                          'type': grid.type,
                          'force': 'true' if force else 'false'}
            self.save_orders.append(save_order)

        # 开多leg1
        orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_BUY, buyPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
        if orderID is None or len(orderID) == 0:
            self.writeCtaError(u'ArbBuy，Leg1 {0}开多仓{1}手失败,委托价:{2}'.format(self.Leg1Symbol,grid.volume, buyPrice))
            return None
        orders = orderID
        self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_LONG,
                                           'OFFSET': OFFSET_OPEN, 'Volume': grid.volume,
                                           'Price': buyPrice, 'TradedVolume': EMPTY_INT,
                                           'OrderTime': self.curDateTime,
                                           'Grid': grid,
                                           'PriceType':PRICETYPE_FAK,
                                           'Retry': 0}

        # 开空leg2
        orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_SHORT, shortPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
        if (orderID is None) or len(orderID) == 0:
            self.writeCtaCritical(u'ArbBuy，Leg2 {0}开空仓{1}手失败，委托价：{2}'.format(self.Leg2Symbol,grid.volume,shortPrice))
            # 这里要不要处理之前的Leg1开仓？（放在后面cancelorder中处理）
            return None
        orders = orders + ';' + orderID
        self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_SHORT,
                                           'OFFSET': OFFSET_OPEN, 'Volume': grid.volume,
                                           'Price': shortPrice, 'TradedVolume': EMPTY_INT,
                                           'OrderTime': self.curDateTime,
                                           'Grid':grid,
                                           'PriceType':PRICETYPE_FAK,
                                           'Retry': 0}
        grid.orderStatus = True
        self.entrust = 1
        grid.orderDatetime = self.curDateTime
        self.writeCtaLog(u'arb Buy Orders：{0}'.format(orders))
        return orders

    # ----------------------------------------------------------------------
    def __arbSell(self, grid, force = False):
        """非标准合约的套利平正套（平多）指令"""
        self.writeCtaLog(u'套利价差正套（平多）单,price={0},volume={1}'.format(grid.closePrice, grid.volume))
        if not self.trading:
            self.writeCtaLog(u'停止状态，不开仓')
            return None

        # 检查流动性缺失
        if not self.__checkLiquidity() and not force: return

        # 检查涨跌停距离
        if self.__checkNearMaxNorMin():
            return None

        bidPrice = self.lastLeg1Tick.bidPrice1 - self.lastLeg2Tick.askPrice1

        if self.lastLeg1Tick.bidPrice1 >= self.lastLeg1Tick.lastPrice:
            if self.lastLeg1Tick.bidVolume1 < 3:
                sellPrice = self.lastLeg1Tick.lastPrice - 2*self.minDiff
            elif self.lastLeg1Tick.bidVolume1 < 10:
                sellPrice = self.lastLeg1Tick.lastPrice - self.minDiff
            else:
                sellPrice = self.lastLeg1Tick.lastPrice
        else:
            if self.lastLeg1Tick.bidVolume1 < 10 or self.lastLeg1Tick.bidVolume1 <= grid.volume:
                sellPrice = self.lastLeg1Tick.bidPrice1 - self.minDiff
            else:
                sellPrice = self.lastLeg1Tick.bidPrice1

        if self.lastLeg2Tick.askPrice1 <= self.lastLeg2Tick.lastPrice:

            if self.lastLeg2Tick.askVolume1 < 3:
                coverPrice = self.lastLeg2Tick.lastPrice + 2*self.minDiff
            elif self.lastLeg2Tick.askVolume1 < 10:
                coverPrice = self.lastLeg2Tick.lastPrice + self.minDiff
            else:
                coverPrice = self.lastLeg2Tick.lastPrice

        else:
            if self.lastLeg2Tick.askVolume1 < 10 or self.lastLeg2Tick.bidVolume1 <= grid.volume:
                coverPrice = self.lastLeg2Tick.askPrice1 + self.minDiff
            else:
                coverPrice = self.lastLeg2Tick.askPrice1

        if bidPrice < grid.closePrice and not force:
            self.writeCtaLog(u'实际价差{0}不满足:{1}'.format(bidPrice, grid.closePrice))
            return None

        #if sellPrice - coverPrice < grid.closePrice and not force:
        #    self.writeCtaLog(u'对价差{0}不满足:{1}'.format(bidPrice, grid.closePrice))
        #    return None

        if force:
            sellPrice -= self.minDiff
            coverPrice += self.minDiff

        leg1Pos = self.ctaEngine.posBufferDict.get(self.Leg1Symbol, None)

        leg2Pos = self.ctaEngine.posBufferDict.get(self.Leg2Symbol, None)
        if not self.backtesting:
            # 实盘检查持仓
            if leg1Pos is None:
                self.writeCtaLog(u'查询不到Leg1:{0}的持仓数据'.format(self.Leg1Symbol))
                return None
            elif leg1Pos.longPosition < int(grid.volume) and int(leg1Pos.longYd+leg1Pos.longToday) < int(grid.volume):
                self.writeCtaCritical(
                    u'arbSell:{}多单仓位{}/今仓{}/昨{}/不足{}'.format(self.Leg1Symbol, leg1Pos.longPosition, leg1Pos.longToday,
                                                     leg1Pos.longYd, grid.volume))
                return None

            if leg2Pos is None :
                self.writeCtaLog(u'查询不到Leg2:{0}的持仓数据'.format(self.Leg2Symbol))
                return None
            elif leg2Pos.shortPosition < int(grid.volume) and int(leg2Pos.shortToday+leg2Pos.shortYd) < int(grid.volume):

                self.writeCtaCritical(
                    u'arbSell:{}空单仓位{}/今仓:{}/昨仓:{},不足{}'.format(self.Leg2Symbol, leg2Pos.shortPosition, leg2Pos.longToday,
                                                        leg2Pos.longYd, grid.volume))
                return None

        # 回测模式下，保存order
        if self.backtesting:
            save_order = {"datetime": self.curDateTime.strftime('%Y-%m-%d %H:%M:%S'),
                          "direction": 'short',
                          "offset": 'close',
                          "price": sellPrice - coverPrice,
                          "volume": grid.volume,
                          'type': grid.type,
                          'force': 'true' if force else 'false'}
            self.save_orders.append(save_order)

        # ------------------平多leg1---------------------------------
        # 只有1手的情况下
        if leg1Pos is None or grid.volume == 1 or self.backtesting:
            orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_SELL, sellPrice, grid.volume, strategy=self,
                                               priceType=PRICETYPE_FAK)
            orders = orderID
            if orderID is None:
                self.writeCtaError(u'ArbSell，Leg1:{0}平多仓{1}手失败，委托价：{2}'.format(self.Leg1Symbol,grid.volume,sellPrice))
                return None
            self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                               'Price': sellPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                                'PriceType':PRICETYPE_FAK,
                                                'Retry': 0}
            if leg1Pos is not None:
                if leg1Pos.longYd >0:
                    leg1Pos.longYd -= 1
                else:
                    leg1Pos.longToday -= 1
                leg1Pos.longPosition = leg1Pos.longToday + leg1Pos.longYd

        else:
            # 昨仓有，并且少于平仓数量
            if leg1Pos.longYd > EMPTY_INT and  leg1Pos.longYd <  grid.volume:
                volYd  = leg1Pos.longYd             # 昨仓全平
                volToday = grid.volume - volYd      # 剩余的数量，平今仓

                self.writeCtaLog(u'{0}昨仓:{1}/今仓:{2}，分别平昨仓:{3}手、:今仓{4}手'
                                 .format(self.Leg1Symbol, leg1Pos.longYd, leg1Pos.longToday, volYd, volToday))

                # 平昨仓(第一次调用时，ctaEngine同样使用昨仓优先）
                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_SELL, sellPrice,
                                                   volYd, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaError(u'ArbSell，Leg1:{0}平多仓（昨仓:{1}手）失败,委托价：{2}'.format(self.Leg1Symbol,volYd,sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volYd, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}
                # 更新持仓数据中的昨仓为0，避免瞬间连续平仓引发的昨仓数量不足
                leg1Pos.longYd = 0
                leg1Pos.longPosition = leg1Pos.longToday + leg1Pos.longYd

                orders = orderID
                 # 平今仓
                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_SELL, sellPrice, volToday, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaError(u'ArbSell，Leg1:{0}平多今仓:{1}手失败,委托价:{2}'.format(self.Leg1Symbol,volToday,sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volToday, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

                orders = orders + ';' + orderID

            # 剩余：要么昨仓数量大于平仓数量、要么没有昨仓数量，今仓数量 >= 平仓数量，都交给catEngine自己解决
            else:
                if leg1Pos.longYd > EMPTY_INT and leg1Pos.longYd > grid.volume:

                    leg1Pos.longYd -= grid.volume
                    leg1Pos.longPosition = leg1Pos.longToday + leg1Pos.longYd

                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_SELL, sellPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
                orders = orderID
                if orderID is None:
                    self.writeCtaError(u'ArbSell，Leg1:{0}平多仓:{1}手失败,委托价：{2}'.format(self.Leg1Symbol,grid.volume,sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

        # --------------平空leg2-----------------------
        leg2Pos = self.ctaEngine.posBufferDict.get(self.Leg2Symbol, None)
        # 只有1手的情况下
        if leg2Pos is None or grid.volume == 1 or self.backtesting:
            orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_COVER, coverPrice, grid.volume, strategy=self,
                                               priceType=PRICETYPE_FAK)
            if orderID is None:
                self.writeCtaCritical(u'ArbSell，Leg2:{0}平空仓{1}手失败，委托价:{2}'.format(self.Leg2Symbol,grid.volume,coverPrice))
                # 这里要不要处理之前的Leg1开仓？（放在后面cancelorder中处理）
                return None
            orders = orders + ';' + orderID
            self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_LONG,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                               'Price': coverPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': 0}
            if leg1Pos is not None:
                if leg2Pos.shortYd > 0:
                    leg2Pos.shortYd -= 1
                else:
                    leg2Pos.shortToday -= 1
                leg2Pos.shortPosition = leg2Pos.shortYd + leg2Pos.shortToday
        else:
            # 昨仓有，并且少于平仓数量
            if leg2Pos.shortYd > EMPTY_INT and leg2Pos.shortYd < grid.volume:
                volYd = leg2Pos.shortYd                 # 平所有的昨仓
                volToday = grid.volume - volYd          # 剩余的今仓平
                self.writeCtaLog(u'{0}当前昨仓{1}/今仓:{2},分别平昨仓:{3}、今仓:{4}'
                                 .format(self.Leg2Symbol,leg2Pos.shortYd, leg2Pos.shortToday, volYd, volToday))

                # 平昨仓
                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_COVER, coverPrice, volYd, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaCritical(u'ArbSell，Leg2:{0}平空昨仓:{1}手失败，委托价：{2}'.format(self.Leg2Symbol, volYd, coverPrice))
                    return None

                orders = orders + ';' + orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volYd, 'TradedVolume': EMPTY_INT,
                                                   'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}
                # 更新持仓数据中的昨仓为0，避免瞬间连续平仓引发的昨仓数量不足
                leg2Pos.shortYd = 0
                leg2Pos.shortPosition = leg2Pos.shortYd + leg2Pos.shortToday

                # 平今仓
                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_COVER, coverPrice, volToday, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaCritical(u'ArbSell，Leg2:{0}平空今仓:{1}手失败，委托价:{2}'.format(self.Leg2Symbol, volToday,coverPrice))
                    return None

                orders = orders + ';' + orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volToday, 'TradedVolume': EMPTY_INT,
                                                   'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}
            else:
                # 其他情况
                if leg2Pos.shortYd > EMPTY_INT and leg2Pos.shortYd > grid.volume:
                    leg2Pos.shortYd -= grid.volume
                    leg2Pos.shortPosition = leg2Pos.shortYd + leg2Pos.shortToday

                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_COVER, coverPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaCritical(u'ArbSell,Leg2:{0}平空仓{1}手失败，委托价:{2}'.format(self.Leg2Symbol, grid.volume,coverPrice))
                    # 这里要不要处理之前的Leg1开仓？（放在后面cancelorder中处理）
                    return None
                orders = orders + ';' + orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume,
                                                   'Price': coverPrice, 'TradedVolume': EMPTY_INT,
                                                   'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

        self.entrust = -1
        grid.orderDatetime = self.curDateTime
        self.writeCtaLog(u'arb Sell Orders：{0}'.format(orders))
        return orders

    # ----------------------------------------------------------------------
    def __arbCover(self, grid, force = False):
        """非标准合约的套利平反套（平空）指令"""
        self.writeCtaLog(u'套利价差平反套（平多）单,price={0},volume={1}'.format(grid.closePrice, grid.volume))
        if not self.trading:
            self.writeCtaLog(u'停止状态，不开仓')
            return None

        # 检查流动性缺失
        if not self.__checkLiquidity() and not force: return

        # 检查涨跌停距离
        if self.__checkNearMaxNorMin():
            return None

        askPrice = self.lastLeg1Tick.askPrice1 - self.lastLeg2Tick.bidPrice1
        if self.lastLeg1Tick.askPrice1 <= self.lastLeg1Tick.lastPrice:
            if self.lastLeg1Tick.askVolume1 < 3:
                coverPrice = self.lastLeg1Tick.lastPrice+2*self.minDiff
            elif self.lastLeg1Tick.askVolume1 < 10:
                coverPrice = self.lastLeg1Tick.lastPrice + self.minDiff
            else:
                coverPrice = self.lastLeg1Tick.lastPrice

        else:
            if self.lastLeg1Tick.askVolume1 < 10 or self.lastLeg1Tick.bidVolume1 <= grid.volume:
                coverPrice = self.lastLeg1Tick.askPrice1 + self.minDiff
            else:
                coverPrice = self.lastLeg1Tick.askPrice1

        if self.lastLeg2Tick.bidPrice1 >= self.lastLeg2Tick.lastPrice:
            if self.lastLeg2Tick.bidVolume1 < 3:
                sellPrice = self.lastLeg2Tick.lastPrice - 2*self.minDiff
            elif self.lastLeg2Tick.bidVolume1 < 10:
                sellPrice = self.lastLeg2Tick.lastPrice - self.minDiff
            else:
                sellPrice = self.lastLeg2Tick.lastPrice

        else:
            if self.lastLeg2Tick.bidVolume1 < 10 or self.lastLeg2Tick.bidVolume1 <= grid.volume:
                sellPrice = self.lastLeg2Tick.bidPrice1 - self.minDiff
            else:
                sellPrice = self.lastLeg2Tick.bidPrice1

        if askPrice > grid.closePrice and not force:
            self.writeCtaLog(u'实际价差{0}不满足:{1}'.format(askPrice, grid.closePrice))
            return None

        #if (coverPrice - sellPrice) > grid.closePrice and not force:
        #    self.writeCtaLog(u'对价价差{0}不满足:{1}'.format((coverPrice - sellPrice), grid.closePrice))
        #    return None

        if force:
            coverPrice += self.minDiff
            sellPrice -= self.minDiff

        leg1Pos = self.ctaEngine.posBufferDict.get(self.Leg1Symbol, None)
        leg2Pos = self.ctaEngine.posBufferDict.get(self.Leg2Symbol, None)

        if not self.backtesting:
            # 实盘检查持仓
            if leg1Pos is None :
                self.writeCtaError(u'查询不到Leg1:{0}的持仓数据'.format(self.Leg1Symbol))
                return None
            elif int(leg1Pos.shortToday+leg1Pos.shortYd) < int(grid.volume):  # leg1Pos.shortPosition < grid.volume and
                self.writeCtaCritical(u'arbCover:{}空单仓位{}/今仓:{}/昨仓:{},不足{}'.format(self.Leg1Symbol, leg1Pos.shortPosition,leg1Pos.shortToday,leg1Pos.shortYd, grid.volume))
                return None

            if leg2Pos is None:
                self.writeCtaError(u'查询不到Leg2:{0}的持仓数据'.format(self.Leg2Symbol))
                return None

            elif int(leg2Pos.longYd + leg2Pos.longToday) < int(grid.volume): # leg2Pos.longPosition < grid.volume and
                self.writeCtaCritical(u'arbCover:{}多单仓位{}/今仓{}/昨{}/不足{}'.format(self.Leg2Symbol, leg2Pos.longPosition,leg2Pos.longToday,leg2Pos.longYd, grid.volume))
                return None
        # 回测模式下，保存order
        if self.backtesting:
            save_order = {"datetime": self.curDateTime.strftime('%Y-%m-%d %H:%M:%S'),
                          "direction": 'long',
                          "offset": 'close',
                          "price": coverPrice - sellPrice,
                          "volume": grid.volume,
                          'type': grid.type,
                          'force': 'true' if force else 'false'
                          }
            self.save_orders.append(save_order)

        # 平空leg1
        # 只有1手的情况下
        if leg1Pos is None or grid.volume == 1 or self.backtesting:
            orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_COVER, coverPrice, grid.volume, strategy=self,
                                               priceType=PRICETYPE_FAK)
            if orderID is None:
                self.writeCtaError(u'ArbCover,Leg1:{0}平空仓({1}手)失败，委托价:{2}'.format(self.Leg1Symbol, grid.volume,coverPrice))
                return None
            orders = orderID
            self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_LONG,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                               'Price': coverPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': 0}
            if leg1Pos is not None:
                if leg1Pos.shortYd > 0:
                    leg1Pos.shortYd -= 1
                else:
                    leg1Pos.shortToday -= 1
                leg1Pos.shortPosition = leg1Pos.shortToday + leg1Pos.shortYd

        else:
            # 昨仓有，并且少于平仓数量
            if leg1Pos.shortYd > EMPTY_INT and leg1Pos.shortYd < grid.volume:
                volYd = leg1Pos.shortYd             # 昨仓全平
                volToday = grid.volume - volYd      # 今仓平剩余部分
                self.writeCtaLog(u'{0}分别平昨仓:{1}、今仓:{2}'.format(self.Leg1Symbol, volYd, volToday))

                # 优先平昨仓
                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_COVER, coverPrice, volYd, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaError(u'ArbCover, Leg1:{0}平空仓(昨仓:{1}手）失败,委托价:{2}'.format(self.Leg1Symbol, volYd,coverPrice))
                    return None
                orders = orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volYd, 'TradedVolume': EMPTY_INT,
                                                   'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}
                # 更新持仓数据中的昨仓为0，避免瞬间连续平仓引发的昨仓数量不足
                leg1Pos.shortYd = 0
                leg1Pos.shortPosition = leg1Pos.shortToday + leg1Pos.shortYd

                # 平今仓
                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_COVER, coverPrice, volToday, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaError(u'ArbCover, Leg1:{0}平空仓(今仓:{1}手）失败,委托价:{2}'.format(self.Leg1Symbol, volToday,coverPrice))

                    return None
                orders = orders + ';' + orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volToday, 'TradedVolume': EMPTY_INT,
                                                   'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}
            else:
                # 其他情况(全部昨天仓/全部今仓）
                if leg1Pos.shortYd > EMPTY_INT and leg1Pos.shortYd > grid.volume:
                    leg1Pos.shortYd -= grid.volume
                    leg1Pos.shortPosition =leg1Pos.shortToday + leg1Pos.shortYd

                orderID = self.ctaEngine.sendOrder(self.Leg1Symbol, CTAORDER_COVER, coverPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaError(u'ArbCover,Leg1:{0}平空仓({1}手)失败,委托价:{2}'.format(self.Leg1Symbol, grid.volume,coverPrice))

                    return None
                orders = orderID
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_LONG,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                                   'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

        # 平多leg2

        # 只有1手的情况下
        if leg2Pos is None or grid.volume == 1 or self.backtesting:
            orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_SELL, sellPrice, grid.volume, strategy=self,
                                               priceType=PRICETYPE_FAK)
            orders = orders + ';' + orderID
            if orderID is None:
                self.writeCtaCritical(u'ArbCover,Leg2:{0}平多仓({1}手)失败,委托价：{2}'.format(self.Leg2Symbol, grid.volume,sellPrice))
                return None
            self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_SHORT,
                                               'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                               'Price': sellPrice, 'OrderTime': self.curDateTime,
                                               'Grid': grid,
                                               'PriceType': PRICETYPE_FAK,
                                               'Retry': 0}
            if leg2Pos is not None:
                if leg2Pos.longYd >0:
                    leg2Pos.longYd -= 1
                else:
                    leg2Pos.longToday -= 1
                leg2Pos.longPosition = leg2Pos.longYd + leg2Pos.longToday

        else:
            # 昨仓有，并且少于平仓数量
            if leg2Pos.longYd > EMPTY_INT and leg2Pos.longYd < grid.volume:
                volYd= leg2Pos.longYd
                volToday = grid.volume - volYd

                self.writeCtaLog(u'{0}分别平今仓:{1}、:昨仓{2}'.format(self.Leg2Symbol, volToday, volYd))

                # 平昨仓(第一次调用时，ctaEngine同样使用昨仓优先）
                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_SELL, sellPrice, volYd, strategy=self, priceType=PRICETYPE_FAK)

                if orderID is None:
                    self.writeCtaCritical(u'ArbCover,Leg2:{0}平多仓（昨仓:{1}手）失败,委托价：{2}'.format(self.Leg2Symbol, volYd, sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volYd, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

                # 更新持仓数据中的昨仓为0，避免瞬间连续平仓引发的昨仓数量不足
                leg2Pos.longYd = 0
                leg2Pos.longPosition = leg2Pos.longYd + leg2Pos.longToday

                orders = orders + ';' + orderID
                # 平今仓
                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_SELL, sellPrice, volToday, strategy=self, priceType=PRICETYPE_FAK)
                if orderID is None:
                    self.writeCtaCritical(u'ArbCover, Leg2:{0}平多仓（昨仓{1}手）失败，委托价：{2}'.format(self.Leg2Symbol,volToday,sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': volToday, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

                orders = orders + ';' + orderID

            # 剩余：要么昨仓数量大于平仓数量、要么没有昨仓数量，今仓数量 >= 平仓数量，都交给catEngine自己解决
            else:
                if leg2Pos.longYd > EMPTY_INT and leg2Pos.longYd > grid.volume:
                    leg2Pos.longYd -= grid.volume
                    leg2Pos.longPosition = leg2Pos.longYd + leg2Pos.longToday

                orderID = self.ctaEngine.sendOrder(self.Leg2Symbol, CTAORDER_SELL, sellPrice, grid.volume, strategy=self, priceType=PRICETYPE_FAK)
                orders = orders + ';' + orderID
                if orderID is None:
                    self.writeCtaCritical(u'ArbCover, Leg2:{0}平多仓（{1}手）失败，委托价：{2}'.format(self.Leg2Symbol, grid.volume,sellPrice))
                    return None
                self.uncompletedOrders[orderID] = {'SYMBOL': self.Leg2Symbol, 'DIRECTION': DIRECTION_SHORT,
                                                   'OFFSET': OFFSET_CLOSE, 'Volume': grid.volume, 'TradedVolume': EMPTY_INT,
                                                   'Price': sellPrice,
                                                   'OrderTime': self.curDateTime,
                                                   'Grid': grid,
                                                   'PriceType': PRICETYPE_FAK,
                                                   'Retry': 0}

        self.entrust = 1
        grid.orderDatetime = self.curDateTime
        self.writeCtaLog(u'arb Cover Orders：{0}'.format(orders))
        return orders

    def __lockGrids(self, **args):
        """在趋势转向时锁定网格
        direction : 当前的趋势，若为多方向，则检查空单是否存在淌口，若为空方向，则检查多单是否存在风险淌口
        """
        try:
            direction = args['direction']
            lockVolume = args['lockVolume']
            multiRate = args['multiRate']
        except Exception as ex:
            self.writeCtaError(u'__delayLockGrids({}) 异常:{}'.format(args, ex.message))
            return

        if not self.inited:
            self.writeCtaCritical(u'当前未初始化，不能锁仓，当前趋势：{}'.format(direction))
            return

        if not self.trading:
            self.writeCtaError(u'当前未启动交易，不能锁仓，当前趋势：{}'.format(direction))
            return

        if not self.autoLock:
            self.writeCtaError(u'未设置自动锁单，需要在CTA_setting中设置autoLock=True')
            return

        if multiRate < 0 or lockVolume < 1:
            self.writeCtaError(u'锁仓比率必须大于0,锁仓数量必须大于0')

        # 使用已开仓的平均价，重新计算一次
        self.gt.recount_avg_open_price()

        # 若为多方向，则检查空单是否存在淌口
        if direction == DIRECTION_LONG:
            if abs(self.position.shortPos) == 0:
                self.writeCtaError(u'当前没有持仓空单，不用锁定')
                return

            lock_volume = max(round(lockVolume * multiRate,0),1)

            lossPrice = abs(self.curTick.askPrice1 - self.gt.avg_up_open_price)
            lossPrice = max(self.gridWin, lossPrice) + self.minDiff
            lossPrice = lossPrice - lossPrice % self.minDiff

            openedGrids = self.gt.getGrids(direction=DIRECTION_SHORT, opened=True)

            self.writeCtaNotification(u'存在空单{0}手，均价{1},浮亏{2}，对锁多单{3}手，开仓价{4}，止盈价:{5}'.
                                      format(abs(self.position.shortPos), self.gt.avg_up_open_price,
                                             lossPrice, lock_volume,
                                             self.curTick.askPrice1, self.curTick.askPrice1+lossPrice))

            lock_grid = CtaGrid(direction=DIRECTION_LONG,
                               openprice=self.curTick.askPrice1,
                               closeprice=self.curTick.askPrice1 + lossPrice ,
                               volume=lock_volume,
                               type = LOCK_GRID)

            lock_grid.lockGrids = [grid.openPrice for grid in openedGrids]
            self.gt.dnGrids.append(lock_grid)

            ref = self.__arbBuy(lock_grid, force=True)

            if ref is not None and len(ref) > 0:
                self.writeCtaLog(u'对锁，开多委托单号{0}'.format(ref))
                self.gt.updateOrderRef(direction=DIRECTION_LONG, openPrice=lock_grid.openPrice, orderRef=ref)
            else:
                self.writeCtaError(u'对锁，开多委托单失败:{0},v:{1}'.format(lock_grid.openPrice, lock_grid.volume))

            return

        # 若为空方向，则检查多单是否存在风险淌口
        if direction == DIRECTION_SHORT:
            if abs(self.position.longPos) == 0:
                self.writeCtaError(u'当前没有持仓多单，不用锁定')
                return

            lock_volume = max(round(lockVolume * multiRate, 0), 1)

            lossPrice = abs(self.gt.avg_dn_open_price - self.curTick.bidPrice1)
            lossPrice = max(self.gridWin,lossPrice) + self.minDiff
            lossPrice = lossPrice - lossPrice % self.minDiff

            self.writeCtaNotification(u'存在多单{0}手，均价{1},浮亏{2}，对锁空单{3}手，开仓价{4}，止盈价:{5}'.
                                      format(abs(self.position.longPos), self.gt.avg_dn_open_price,
                                             lossPrice, lock_volume,
                                             self.curTick.askPrice1, self.curTick.bidPrice1 - lossPrice))

            openedGrids = self.gt.getGrids(direction=DIRECTION_LONG, opened=True)

            lock_grid = CtaGrid(direction=DIRECTION_SHORT,
                                openprice=self.curTick.bidPrice1,
                                closeprice=self.curTick.bidPrice1 - lossPrice,
                                volume=lock_volume,
                                type = LOCK_GRID)

            lock_grid.lockGrids = [grid.openPrice for grid in openedGrids]

            self.gt.upGrids.append(lock_grid)
            ref = self.__arbShort(lock_grid, force=True)

            if ref is not None and len(ref) > 0:
                self.writeCtaLog(u'对锁，开空委托单号{0}'.format(ref))
                self.gt.updateOrderRef(direction=DIRECTION_SHORT, openPrice=lock_grid.openPrice, orderRef=ref)
            else:
                self.writeCtaCritical(u'对锁，开空委托单失败:{0},v:{1}'.format(lock_grid.openPrice, lock_grid.volume))
            return

    def __insert_signal(self, direction, price, dt):
        """保存信号"""

        dt = dt.replace(second=0)

        k = u'{}_{}_{}'.format(dt, 'long' if direction == DIRECTION_LONG else 'short', price)

        if k in self.save_signals:
            return

        self.save_signals[k] = {'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'direction': 'long' if direction == DIRECTION_LONG else 'short',
                                'price': price,
                                'M5_pre': self.lineM5.curPeriod.pre_mode if self.lineM5.curPeriod is not None else '-',
                                'M5': self.lineM5.curPeriod.mode if self.lineM5.curPeriod is not None else '-',
                                'M1_pre': self.lineRatio.curPeriod.pre_mode if self.lineRatio.curPeriod is not None else '-',
                                'M1': self.lineRatio.curPeriod.mode if self.lineRatio.curPeriod is not None else '-',
                                'cond1':  u'false',
                                'cond2':  u'false'
                                }
    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """行情更新
        :type tick: object
        """
        # 更新策略执行的时间（用于回测时记录发生的时间）
        self.curDateTime = tick.datetime

        spread_tick = None
        ratio_tick = None
        mean_tick = None

        # 合并tick
        if tick.vtSymbol != self.vtSymbol:
            spread_tick, ratio_tick, mean_tick = self.__combineTick(tick)
        if spread_tick is None or ratio_tick is None or mean_tick is None:
            if self.backtesting:
                # 虽然未合成价差，仍然要检查是否满足撤单逻辑
                self.__cancelLogic(self.curDateTime)
            return

        # 修正lastPrice，大于中轴(0)时，取最小值，小于中轴时，取最大值
        if spread_tick.bidPrice1 > self.baseMidLine and spread_tick.askPrice1 > self.baseMidLine:
            spread_tick.lastPrice = min(spread_tick.bidPrice1, spread_tick.askPrice1)
        elif spread_tick.bidPrice1 < self.baseMidLine and spread_tick.askPrice1 < self.baseMidLine:
            spread_tick.lastPrice = max(spread_tick.bidPrice1, spread_tick.askPrice1)

        self.curTick = spread_tick

        if not self.backtesting:
            dt = datetime.now()
            if (dt.hour >= 3 and dt.hour < 8) or (dt.hour >= 16 and dt.hour < 20):
                return

        if (spread_tick.datetime.hour >= 3 and spread_tick.datetime.hour <= 8) or (spread_tick.datetime.hour >= 16 and spread_tick.datetime.hour <= 20):
            self.writeCtaLog(u'休市/集合竞价排名时数据不处理')
            if self.inited and len(self.lineDiff.lineMiddleBand) > 0:
                self.__initGrids()
            return

        if not self.recheckPositions and self.closeWindow:
            self.writeCtaLog(u'激活重新提交平仓单')
            self.recheckPositions = True

        if self.deadLineDate is not None and self.tradingOpen:
            if spread_tick.datetime > self.deadLineDate:
                self.tradingOpen = False
                self.writeCtaLog(u'日期超过最后开仓日期，不再开仓')

        if self.forceCloseDate is not None and not self.forceTradingClose:
            if spread_tick.datetime > self.forceCloseDate:
                self.forceTradingClose = True
                self.writeCtaLog(u'日期到达强制平仓日期，强制平仓')

        # 2、计算交易时间和平仓时间
        self.__timeWindow(spread_tick)

        self.lineRatio.onTick(ratio_tick)
        self.lineDiff.onTick(spread_tick)
        self.lineMD.onTick(mean_tick)
        if self.inited:
            self.lineM5.onTick(ratio_tick)

        # 4、交易逻辑
        # 首先检查是否是实盘运行还是数据预处理阶段
        if not (self.inited and len(self.lineDiff.lineMiddleBand) > 0 and len(self.lineRatio.lineStateMean) > 0 and len(self.lineMD.lineMiddleBand) > 0 and len(self.lineM5.atan_list) > 1):
            return

        # 初始化网格交易器（或从本地记录文件中获取）
        self.__initGrids()

        if not self.backtesting and self.tradeWindow and not self.closeWindow and self.recheckPositions:
            self.writeCtaLog(u'交易时间，重新计算持仓')
        # 重新计算持仓
            self.__recheckPositions()

        if not self.tradeWindow and self.closeWindow and not self.recheckPositions:
            self.writeCtaLog(u'收盘时间，重置计算持仓标志')
            self.recheckPositions = True
            if self.inited:
                self.gt.save(direction=DIRECTION_LONG)
                self.gt.save(direction=DIRECTION_SHORT)

        # 执行撤单逻辑
        self.__cancelLogic(self.curDateTime)

        # 执行延迟任务逻辑
        while len(self.delayMission) > 0 and self.tradeWindow:
            mission = self.delayMission.pop(0)
            try:
                func = mission['func']
                args = mission['args']
                func(**args)
            except Exception as ex:
                self.writeCtaError(u'执行任务出错:{}'.format(str(ex)))

        # 执行平仓逻辑
        # 持有正套的单
        if self.position.longPos > 0 and self.entrust == 0 and self.tradeWindow:

            if self.forceTradingClose:
                self.writeCtaLog(u'强制平仓日期，强制平所有正套单')
                self.__closeAllGrids(direction=DIRECTION_LONG, closePrice=spread_tick.bidPrice1)
                return

            # 出现做空信号
            if spread_tick.bidPrice1 > self.lineDiff.lineUpperBand[-1] \
                    and mean_tick.bidPrice1 > self.lineMD.lineUpperBand[-1]:
                update_long_grid_flag = False
                update_long_lock_grids = None

                # 3、只平不开时间段
                if not self.tradingOpen:
                    update_long_grid_flag = True
                    update_long_lock_grids = self.gt.getGrids(direction=DIRECTION_LONG, opened=True, closed=False,
                                                              ordered=False,
                                                              begin=999999, end=-999999, type=LOCK_GRID)

                if update_long_grid_flag:
                    self.writeCtaLog(u'Short Signal:{} ，平仓不亏损的正套单'.format(spread_tick.bidPrice1))
                    update_long_grids = self.gt.getGrids(direction=DIRECTION_LONG, opened=True, closed=False,
                                                         ordered=False,
                                                         begin=999999, end=-999999)

                    if update_long_lock_grids is not None:
                        update_long_grids.extend(update_long_lock_grids)

                    for x in update_long_grids:
                        if x.openPrice < spread_tick.bidPrice1 - 2 * self.minDiff or not self.tradingOpen:
                            x.closePrice = spread_tick.bidPrice1
            # 从网格获取，未平仓状态，价格，注意检查是否有可以平仓的网格
            pendingGrids = self.gt.getGrids(direction=DIRECTION_LONG, opened=True, closed=False, ordered=False,
                                            begin=999999, end=-999999)
            for x in pendingGrids:
                if x.closePrice <= spread_tick.bidPrice1 :
                    ref = self.__arbSell(x)
                    if ref is not None:
                        self.writeCtaLog(u'平正套（平多）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_LONG, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'平正套（平多）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))
                elif (spread_tick.bidPrice1 > (self.lineM5.lineUpperBand[-1] - 1) * self.lastLeg2Tick.lastPrice and spread_tick.bidPrice1 >= x.openPrice + 2 * self.minDiff) \
                    or (spread_tick.bidPrice1 > self.lineDiff.lineUpperBand[-1] and spread_tick.bidPrice1 >= x.openPrice + 2 * self.minDiff and x.type == EMPTY_STRING):
                    x.closePrice = spread_tick.bidPrice1
                    ref = self.__arbSell(x)
                    if ref is not None:
                        self.writeCtaNotification(u'止盈：平正套（平多）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_LONG, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'止盈：平正套（平多）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))

                elif x.stopPrice > spread_tick.askPrice1:
                    x.closePrice = spread_tick.askPrice1
                    ref = self.__arbSell(x)
                    if ref is not None:
                        self.writeCtaNotification(u'止损：平正套（平多）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_LONG, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'止损：平正套（平多）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))

        # 持有反套的单，检查平仓条件
        if self.position.shortPos < 0 and self.entrust == 0 and self.tradeWindow:

            if self.forceTradingClose:
                self.writeCtaLog(u'强制平仓日期，强制平所有反仓')
                self.__closeAllGrids(direction=DIRECTION_SHORT, closePrice=spread_tick.askPrice1)
                return
                # 出现多信号,处理逆周期势单子

            if spread_tick.askPrice1 < self.lineDiff.lineLowerBand[-1] \
                    and mean_tick.askPrice1 < self.lineMD.lineLowerBand[-1]:
                update_short_grid_flag = False
                update_short_lock_grids = None
                #
                # # 3、只平不开时间段
                if not self.tradingOpen:
                    update_short_grid_flag = True
                    update_short_lock_grids = self.gt.getGrids(direction=DIRECTION_SHORT, opened=True, closed=False,
                                                               ordered=False,
                                                               begin=-999999, end=999999, type=LOCK_GRID)

                if update_short_grid_flag:
                    self.writeCtaLog(u'Buy Signal:{} in,M5:{}=>{}，平满足不亏损的空单'
                                     .format(spread_tick.askPrice1,
                                             self.lineM5.curPeriod.pre_mode, self.lineM5.curPeriod.mode))

                    update_short_grids = self.gt.getGrids(direction=DIRECTION_SHORT, opened=True, closed=False,
                                                          ordered=False,
                                                          begin=-999999, end=999999)

                    if update_short_lock_grids is not None:
                        update_short_grids.extend(update_short_lock_grids)

                    for x in update_short_grids:
                        if x.openPrice > spread_tick.askPrice1 + 2 * self.minDiff or not self.tradingOpen:
                            x.closePrice = spread_tick.askPrice1

            # 从网格获取，未平仓状态，价格
            pendingGrids = self.gt.getGrids(direction=DIRECTION_SHORT, opened=True, closed=False, ordered=False,
                                            begin=-999999, end=999999)
            for x in pendingGrids:
                if x.closePrice >= spread_tick.askPrice1:
                    ref = self.__arbCover(x)
                    if ref is not None:
                        self.writeCtaLog(u'平反套（平空）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_SHORT, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'平反套（平空）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))
                elif (spread_tick.askPrice1 < (self.lineM5.lineLowerBand[-1]-1)*self.lastLeg2Tick.lastPrice and spread_tick.askPrice1 <= x.openPrice - 2*self.minDiff)\
                        or (spread_tick.askPrice1 < self.lineDiff.lineLowerBand[-1] and spread_tick.askPrice1 <=x.openPrice - 2 * self.minDiff and x.type == EMPTY_STRING):
                    x.closePrice = spread_tick.askPrice1
                    ref = self.__arbCover(x)
                    if ref is not None:
                        self.writeCtaNotification(u'止盈：平反套（平空）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_SHORT, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'止盈：平反套（平空）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))

                elif x.stopPrice < spread_tick.bidPrice1:
                    x.closePrice = spread_tick.bidPrice1
                    ref = self.__arbCover(x)
                    if ref is not None:
                        self.writeCtaNotification(u'止损：平反套（平空）委托单号{0}'.format(ref))
                        self.gt.updateOrderRef(direction=DIRECTION_SHORT, openPrice=x.openPrice, orderRef=ref)
                    else:
                        self.writeCtaLog(u'止损：平反套（平空）委托单失败:{0},v:{1}'.format(x.closePrice, x.volume))

        # 执行开仓逻辑
        m1_std = 2 if self.lineDiff.lineBollStd[-1] < 2 else self.lineDiff.lineBollStd[-1]

        if self.openWindow:
            m1_std = m1_std * 1.5

        if spread_tick.bidPrice1 > self.lineDiff.lineMiddleBand[-1] + m1_std * 4 \
                and ratio_tick.bidPrice1 > self.lineM5.lineMiddleBand[-1] + self.lineM5.lineBollStd[-1] * 4:
            self.writeCtaLog(u'Short Signal:{0}'.format(spread_tick.bidPrice1))

            self.__insert_signal(direction=DIRECTION_SHORT, price=spread_tick.bidPrice1, dt=self.curDateTime)

        if spread_tick.askPrice1 < self.lineDiff.lineMiddleBand[-1] - m1_std * 4 \
                and ratio_tick.askPrice1 < self.lineM5.lineMiddleBand[-1] - self.lineM5.lineBollStd[-1] * 4:
            self.writeCtaLog(u'Buy Signal:{0}'.format(spread_tick.askPrice1))

            self.__insert_signal(direction=DIRECTION_LONG, price=spread_tick.askPrice1, dt=self.curDateTime)

        # 判断开空条件
        if self.tradingOpen \
                    and spread_tick.bidPrice1 > self.lineDiff.lineMiddleBand[-1] + m1_std * 4 \
                    and ratio_tick.bidPrice1 > self.lineM5.lineMiddleBand[-1] + self.lineM5.lineBollStd[-1] * 4 \
                    and self.tradeWindow \
                    and self.entrust == 0 :
            if self.position.shortPos != 0:
                highest_short_price_grid = self.gt.getLastOpenedGrid(direction=DIRECTION_SHORT)
                if spread_tick.bidPrice1 < highest_short_price_grid.openPrice + m1_std:
                    return
            short_grid = CtaGrid(direction=DIRECTION_SHORT,
                                 openprice=spread_tick.bidPrice1,
                                 closeprice=self.lineDiff.lineMiddleBand[-1] ,
                                 volume=self.gt.volume
                                 )

            self.__shortGrid(spread_tick,short_grid)

        # 判断开多条件
        if self.tradingOpen \
                and spread_tick.askPrice1 < self.lineDiff.lineMiddleBand[-1] - m1_std * 4 \
                and ratio_tick.askPrice1 < self.lineM5.lineMiddleBand[-1] - self.lineM5.lineBollStd[-1] * 4\
                and self.tradeWindow \
                and self.entrust == 0 :

            if self.position.longPos != 0:
                lowest_long_price_grid = self.gt.getLastOpenedGrid(direction=DIRECTION_LONG)
                if spread_tick.askPrice1 > lowest_long_price_grid.openPrice - m1_std:
                    return

            long_grid = CtaGrid(direction=DIRECTION_LONG,
                                 openprice=spread_tick.askPrice1,
                                 closeprice=self.lineDiff.lineMiddleBand[-1] ,
                                 volume=self.gt.volume
                                 )

            self.__longGrid(spread_tick,long_grid)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟K线数据更新
        bar，k周期数据
        """

        if len(self.lineDiff.lineUpperBand) > 0:
            upper = self.lineDiff.lineUpperBand[-1]
        else:
            upper = 0

        if len(self.lineDiff.lineMiddleBand) > 0:
            middle = self.lineDiff.lineMiddleBand[-1]
        else:
            middle = 0

        if len(self.lineDiff.lineLowerBand) > 0:
            lower = self.lineDiff.lineLowerBand[-1]
        else:
            lower = 0

        if len(self.lineDiff.lineBollStd) > 0:
            boll_std = self.lineDiff.lineBollStd[-1]
        else:
            boll_std = 0

        self.writeCtaLog(u'[M1Diff]{0} [{1}] o:{2},c:{3},h:{4},l:{5},boll:{6}~{7}~{8},[{9}]'
                         .format(bar.datetime, bar.color, bar.open, bar.close, bar.high, bar.low,
                                 upper, middle, lower, boll_std))

        upper = upper - upper % self.minDiff
        middle = middle - middle % self.minDiff
        lower = lower - lower % self.minDiff + self.minDiff

        # 若初始化完毕，新bar比上一个bar的收盘价价差，小于5个网格(防止跳空）
        if self.inited: # and abs(bar.open - self.lineDiff.lineBar[-2].close) < self.gridHeight*5:

            if len(self.gt.upGrids) <= 0 or len(self.gt.dnGrids) <= 0:
                self.writeCtaLog(u'OnBar()初始化网格交易器')
                # 以允许做空线，以及布林上轨的最大值，作为做空网格的起点；
                # 以允许做多，已经布林下轨的最小值，作为做多网格的起点
                self.gt.initGrid(upline=max(self.baseMidLine, upper), dnline=min(self.baseMidLine, lower))

                self.recheckPositions = True
                self.__recheckPositions()
                self.__updateGridsDisplay()

            else:
                # 检查重建
                if (bar.close > self.baseUpLine and upper != self.upLine) and not self.rebuildGrid :
                    self.upLine = upper
                    self.gt.rebuildGrids(direction=DIRECTION_SHORT, upline=max(self.baseMidLine, self.upLine),
                                         midline=middle, upRate= self.upRate, dnRate=self.dnRate)
                    self.__updateGridsDisplay()

                if (bar.close < self.baseDnLine and lower != self.dnLine) and not self.rebuildGrid:

                    self.dnLine = lower
                    self.gt.rebuildGrids(direction=DIRECTION_LONG, dnline=min(self.baseMidLine, self.dnLine),
                                         midline=middle,upRate= self.upRate, dnRate=self.dnRate)
                    self.__updateGridsDisplay()

                if self.rebuildGrid:
                    if self.rebuildUpGrid:
                        self.gt.rebuildGrids(direction=DIRECTION_SHORT, upline=max(self.baseMidLine, self.upLine),
                                         midline=middle, upRate=self.upRate, dnRate=self.dnRate)

                    if self.rebuildDnGrid:
                        self.gt.rebuildGrids(direction=DIRECTION_LONG, dnline=min(self.baseMidLine, self.dnLine),
                                         midline=middle, upRate=self.upRate, dnRate=self.dnRate)

                    self.rebuildGrid = False
                    self.__updateGridsDisplay()

            self.__updatePeriod()
            self.putEvent()
            # ----------------------------------------------------------------------

        if abs(self.position.shortPos) > 0:
            opened_short_grids = self.gt.getGrids(direction=DIRECTION_SHORT,opened=True, ordered=False)

            for grid in opened_short_grids:

                if bar.close > self.lineDiff.lineUpperBand[-1] and (self.curDateTime - grid.openDatetime).seconds > 300 :
                    ref = self.__arbCover(grid,force=True)
                    if ref:
                        grid.orderRef = ref
                        grid.orderStatus = True

        if abs(self.position.longPos) > 0:
            opened_long_grids = self.gt.getGrids(direction=DIRECTION_LONG, opened=True)

            for grid in opened_long_grids:
                if bar.close < self.lineDiff.lineLowerBand[-1] and (self.curDateTime - grid.openDatetime).seconds > 300:
                    ref = self.__arbSell(grid, force=True)
                    if ref:
                        grid.orderStatus = True
                        grid.orderRef = ref


    def onBarRatio(self, bar):
        """比率线的OnBar事件"""

        l = len(self.lineRatio.lineStateMean)

        if l > 0:
            ma = self.lineRatio.lineStateMean[-1]
        else:
            ma = 1
        atan = 0
        if l > 6:
            listClose = [x for x in self.lineRatio.lineStateMean[-7:-1]]
            malist = ta.MA(numpy.array(listClose, dtype=float), 5)
            ma5 = malist[-1]
            ma5_ref1 = malist[-2]
            if ma5 <=0 or ma5_ref1 <= 0:
                self.writeCtaLog(u'[M1Ratio] 卡尔曼均线未完善')
                return
            self.m1_atan = math.atan((ma5 / ma5_ref1 - 1) * 100 * 180 / math.pi)
            self.m1_atan = round(self.m1_atan,4)


        if self.m1_atan <= -0.2 and not (self.rebuildDnGrid and not self.rebuildUpGrid):
            self.upRate = 1
            self.dnRate = 1.5
            self.rebuildDnGrid = True
            self.rebuildUpGrid = False
            self.rebuildGrid = True
        elif self.m1_atan >= 0.2 and not (self.rebuildUpGrid and not self.rebuildDnGrid):
            self.upRate = 1.5
            self.dnRate = 1
            self.rebuildUpGrid = True
            self.rebuildDnGrid = False
            self.rebuildGrid = True
        elif -0.2 < self.m1_atan < 0.2 and not (self.rebuildUpGrid and self.rebuildDnGrid):
            self.upRate = 1
            self.dnRate = 1
            self.rebuildUpGrid = True
            self.rebuildDnGrid = True
            self.rebuildGrid = True

        self.writeCtaLog(u'[M1Ratio]{0} c:{1},kf:{2},atan:{3},)'.format(bar.datetime, bar.close, ma, self.m1_atan ))

    def onBarMeanDiff(self, bar):
        """残差线的OnBar事件"""

        if len(self.lineMD.lineUpperBand) > 0:
            boll_upper = self.lineMD.lineUpperBand[-1]
        else:
            boll_upper = 0

        if len(self.lineMD.lineMiddleBand) > 0:
            boll_mid = self.lineMD.lineMiddleBand[-1]
        else:
            boll_mid = 0

        if len(self.lineMD.lineLowerBand) > 0:
            boll_lower = self.lineMD.lineLowerBand[-1]
        else:
            boll_lower = 0

        if len(self.lineMD.lineBollStd) > 0:
            boll_std = self.lineMD.lineBollStd[-1]
        else:
            boll_std = 0

        self.writeCtaLog(u'[MeanDiff]{0} [{1}] o:{2},c:{3},h:{4},l{5},boll:{6}~{7}~{8},[{9}]'
                         .format(bar.datetime, bar.color, bar.open, bar.close, bar.high, bar.low,
                                 boll_upper, boll_mid, boll_lower, boll_std))

    def onBarM5(self, bar):
        """5分钟Ratio的OnBar事件"""
        if self.inited:
            self.__updatePeriod()
            self.putEvent()

    def onM5PeriodChanged(self,period):
        """5分钟周期状态改变的事件处理"""
        if not self.inited:
            return

        # 震荡=》空
        if period.pre_mode == PERIOD_SHOCK and period.mode == PERIOD_SHORT:
            pass

        # 震荡=》多
        elif period.pre_mode == PERIOD_SHOCK and period.mode == PERIOD_LONG:
            pass

        # 空极端=>多
        elif period.pre_mode == PERIOD_SHORT_EXTREME and period.mode == PERIOD_LONG:
            pass

        # 多极端=>空
        elif period.pre_mode == PERIOD_LONG_EXTREME and period.mode == PERIOD_SHORT:
            pass

        self.__updatePeriod()
        self.putEvent()

    def __count_avg_open_price(self,grid_list):
        """计算平均开仓价"""
        total_price = EMPTY_FLOAT
        total_volume = EMPTY_INT
        avg_price = EMPTY_FLOAT

        for g in grid_list:
            total_price += g.openPrice * g.volume
            total_volume += g.volume

        if total_volume > EMPTY_INT:
            avg_price = total_price / total_volume
        return avg_price

    def __updatePeriod(self):
        """更新周期显示信息"""

        if self.lineM5.curPeriod is not None:
            self.m5_atan = self.lineM5.atan
            self.m5_period = u'{}=>{}'.format(self.lineM5.curPeriod.pre_mode, self.lineM5.curPeriod.mode)

    def __initGrids(self):
        """初始化网格"""
        if len(self.gt.upGrids) <= 0 or len(self.gt.dnGrids) <= 0:
            self.writeCtaLog(u'__initGrids(),初始化网格交易器')
            upper = round(self.lineDiff.lineUpperBand[-1], 2)
            upper = upper - upper % self.minDiff

            lower = round(self.lineDiff.lineLowerBand[-1], 2)
            lower = lower - lower % self.minDiff + self.minDiff

            self.upLine = upper
            self.dnLine = lower
            self.gt.initGrid(upline=max(self.baseMidLine, upper), dnline=min(self.baseMidLine, lower ))

            self.writeCtaLog(u'__initGrids(),初始化网格完成')
            self.recheckPositions = True
            self.__recheckPositions()

    def __updateGridsDisplay(self):
        """更新网格显示信息"""
        self.upGrids = self.gt.toStr(direction=DIRECTION_SHORT)
        self.writeCtaLog(self.upGrids)
        self.dnGrids = self.gt.toStr(direction=DIRECTION_LONG)
        self.writeCtaLog(self.dnGrids)

    def __closeAllGrids(self, **args):
        """对所有的网格强制平仓"""
        try:
            direction = args['direction']
            closePrice = args['closePrice']
        except Exception as ex:
            self.writeCtaError(u'__closeAllGrids({})异常:{}'.format(args,ex.message))
            return

        try:
            type = args['type']
        except:
            type = EMPTY_STRING

        if direction == DIRECTION_SHORT:
            # 扫描上网格
            for x in self.gt.upGrids[:]:
                # 已发送订单，已开仓，未平仓
                if not x.openStatus or x.closeStatus or not x.type==type:
                    self.writeCtaLog(u'网格[open={},close={} ,type={}不满足CloseGrid要求'.format(x.openPrice, x.closePrice, x.type))
                    continue

                if x.orderStatus and x.orderRef != EMPTY_STRING and x.orderDatetime is not None:
                    orders = x.orderRef.split(';')
                    if len(orders) == 1:
                        self.writeCtaLog(u'{0}只有单腿委托{1}'.format(x.openPrice, orders[0]))
                        continue

                    # 当前分钟内，不再委托强平
                    if x.orderDatetime.minute == self.curDateTime.minute:
                        continue

                    self.writeCtaLog(u'取消平仓单:[ref={0},closeprice={1}]'.format(x.orderRef, x.closePrice))
                    for order in orders:
                        self.writeCtaLog(u'撤单:{0}'.format(order))
                        self.cancelOrder(order)

                    sleep(0.1)

                oldPrice = x.closePrice
                x.closePrice = closePrice
                ref = self.__arbCover(x, force=True)

                if ref:
                    x.orderRef = ref
                    x.orderStatus = True
                    x.orderDatetime = self.curDateTime
                    self.writeCtaLog(u'强制提交平空委托单[closeprice={0},volume={1}]'
                                     .format(x.closePrice, x.volume))
                else:
                    self.writeCtaLog(u'提交平仓委托单失败')
                    x.closePrice = oldPrice

        if direction == DIRECTION_LONG:
            # 扫描下网格
            for x in self.gt.dnGrids[:]:
                if not x.openStatus or x.closeStatus or not x.type==type:
                    self.writeCtaLog(u'网格[open={},close={} ,type={}不满足CloseGrid要求'.format(x.openPrice, x.closePrice,x.type))
                    continue

                if x.orderStatus and x.orderRef != EMPTY_STRING and x.orderDatetime is not None:

                    orders = x.orderRef.split(';')
                    if len(orders) == 1:
                        self.writeCtaLog(u'{0}只有单腿委托{1}'.format(x.openPrice, orders[0]))
                        continue

                    if x.orderDatetime.minute == self.curDateTime.minute:
                        continue

                    self.writeCtaLog(u'取消平多单:[ref={0},closeprice={1}]'.format(x.orderRef, x.closePrice))

                    for order in orders:
                        self.writeCtaLog(u'撤单:{0}'.format(order))
                        self.cancelOrder(order)

                    sleep(0.3)

                oldPrice = x.closePrice
                x.closePrice = closePrice
                # 强制平仓
                ref = self.__arbSell(x, force=True)
                if ref:
                    x.orderRef = ref
                    x.orderStatus = True
                    x.orderDatetime = self.curDateTime
                    self.writeCtaLog(
                        u'强制提交平多委托单[closeprice={0},volume={1}]'.format(x.closePrice, x.volume ))
                else:
                    self.writeCtaLog(u'提交平仓委托单失败')
                    x.closePrice = oldPrice

    def __InitMinBarsFromSina(self):
        """# 从sina加载最新的60数据(针对商品期货）"""
        requests.adapters.DEFAULT_RETRIES = 5
        s = requests.session()
        s.keep_alive = False
        D2 = {}
        sinaBars = []

        try:
            # 获取Leg2Symbol的数据
            full_Leg2Symbol = self.getFullSymbol(self.Leg2Symbol)
            url = u'http://stock2.finance.sina.com.cn/futures/api/json.php/InnerFuturesService.getInnerFutures{0}MinKLine?symbol={1}'.format(60, full_Leg2Symbol)
            self.writeCtaLog(u'从sina下载{0}的60分钟数据 {1}'.format(full_Leg2Symbol, 60))
            responses = execjs.eval(s.get(url).content.decode('gbk').split('\n')[-1])
            dayVolume = 0

            for item in responses:
                bar = CtaBarData()
                bar.vtSymbol = self.Leg2Symbol
                bar.symbol = self.Leg2Symbol
                # bar的close time
                sinaDt = datetime.strptime(item[0], '%Y-%m-%d %H:%M:00')
                if sinaDt.hour in {11,23,1,2} and sinaDt.minute == 30:
                    bar.datetime = sinaDt - timedelta(seconds=30 * 60)
                else:
                    bar.datetime = sinaDt - timedelta(seconds=60 * 60)
                bar.date = bar.datetime.strftime('%Y%m%d')
                bar.tradingDay = bar.date       # todo: 需要修改，晚上21点后，修改为next workingday
                bar.time = bar.datetime.strftime('%H:%M:00')
                bar.open = float(item[1])
                bar.high = float(item[2])
                bar.low = float(item[3])
                bar.close = float(item[4])
                D2[bar.date + ' ' + bar.time] = bar

            if len(D2) > 0:
                self.writeCtaLog(u'从sina读取了{0}条60分钟数据'.format(len(D2)))
            else:
                self.writeCtaLog(u'从sina读取60分钟数据失败')
                return False

            sleep(0.2)

            # 获取Leg2Symbol的数据
            full_Leg1Symbol = self.getFullSymbol(self.Leg1Symbol)
            url = u'http://stock2.finance.sina.com.cn/futures/api/json.php/InnerFuturesService.getInnerFutures{0}MinKLine?symbol={1}'.format(
                60, full_Leg1Symbol)
            self.writeCtaLog(u'从sina下载{0}的60分钟数据 {1}'.format(full_Leg1Symbol,  url))
            responses = execjs.eval(s.get(url).content.decode('gbk').split('\n')[-1])
            dayVolume = 0

            for item in responses:
                bar = CtaBarData()
                bar.vtSymbol = self.Leg1Symbol
                bar.symbol = self.Leg1Symbol
                # bar的close time
                sinaDt = datetime.strptime(item[0], '%Y-%m-%d %H:%M:00')
                if sinaDt.hour in {11, 23, 1, 2} and sinaDt.minute == 30:
                    bar.datetime = sinaDt - timedelta(seconds=30 * 60)
                else:
                    bar.datetime = sinaDt - timedelta(seconds=60 * 60)
                bar.date = bar.datetime.strftime('%Y%m%d')
                bar.tradingDay = bar.date  # todo: 需要修改，晚上21点后，修改为next workingday
                bar.time = bar.datetime.strftime('%H:%M:00')

                dt_str = bar.date + ' ' + bar.time
                if dt_str in D2:
                    leg2bar = D2[dt_str]
                    leg1_close = float(item[4])

                    if leg1_close == 0:
                        self.writeCtaLog(u'{0}的60分钟数据,Close = 0，异常'.format(self.Leg1Symbol))
                        continue

                    bar.open = leg1_close / leg2bar.close
                    bar.high = leg1_close / leg2bar.close
                    bar.low = leg1_close / leg2bar.close
                    bar.close = leg1_close / leg2bar.close


            D2.clear()
            return True

        except Exception as e:
            self.writeCtaError(u'加载Sina历史60分钟数据失败：'+str(e))
            self.writeCtaError(u'{0}'.format(traceback.print_exc()))
            return False

    def __InitDataFromSina(self):
        """从sina获取初始化数据"""

        # 从sina加载最新的M1数据
        try:
            sleep(0.5)
            # 获取D2的分时数据
            D2 = {}
            requests.adapters.DEFAULT_RETRIES = 5
            s = requests.session()
            s.keep_alive = False

            full_Leg2Symbol = self.getFullSymbol(self.Leg2Symbol)
            url = u'http://stock2.finance.sina.com.cn/futures/api/json.php/InnerFuturesService.getInnerFutures5MLine?symbol={0}'.format(self.getFullSymbol(self.Leg2Symbol))
            self.writeCtaLog(u'从sina下载{0}数据 {1}'.format(full_Leg2Symbol, url))
            responses = execjs.eval(s.get(url).content.decode('gbk').split('\n')[-1])

            datevalue = datetime.now().strftime('%Y-%m-%d')

            for j, day_item in enumerate(responses[str(full_Leg2Symbol).upper()]):
                for i, item in enumerate(day_item):

                    tick = CtaTickData()

                    tick.vtSymbol = self.Leg2Symbol
                    tick.symbol = self.Leg2Symbol

                    if len(item) >= 6:
                        datevalue = item[6]

                    tick.date = datevalue
                    tick.time = item[4]+u':00'
                    tick.datetime = datetime.strptime(tick.date+' '+tick.time, '%Y-%m-%d %H:%M:%S')

                    tick.lastPrice = float(item[0])
                    tick.volume = int(item[2])

                    if type(item[3]) == type(None) :
                        tick.openInterest = 0
                    else:
                        tick.openInterest = int(item[3])

                    D2[tick.date+' '+tick.time] = tick

            sleep(1)
            full_Leg1Symbol = self.getFullSymbol(self.Leg1Symbol)

            url = u'http://stock2.finance.sina.com.cn/futures/api/json.php/InnerFuturesService.getInnerFutures5MLine?symbol={0}'.format(full_Leg1Symbol)
            responses = execjs.eval(s.get(url).content.decode('gbk').split('\n')[-1])

            self.writeCtaLog(u'从sina下载{0}数据 {1}'.format(full_Leg1Symbol, url))

            datevalue = datetime.now().strftime('%Y-%m-%d')

            for j, day_item in enumerate(responses[str(full_Leg1Symbol).upper()]):
                for i, item in enumerate(day_item):

                    bar = CtaBarData()
                    bar.vtSymbol = self.vtSymbol
                    bar.symbol = self.vtSymbol

                    if len(item) >= 6:
                        datevalue = item[6]

                    bar.date = datevalue
                    bar.time = item[4]+u':00'
                    bar.datetime = datetime.strptime(bar.date+' '+bar.time, '%Y-%m-%d %H:%M:%S')

                    d1LastPrice = float(item[0])
                    bar.volume = int(item[2])

                    if bar.date+' '+bar.time in D2:
                        tick = D2[bar.date+' '+bar.time]
                        d2LastPrice = tick.lastPrice

                        ratio_bar = copy.copy(bar)
                        mean_bar = copy.copy(bar)

                        bar.open = d1LastPrice - d2LastPrice
                        bar.high = d1LastPrice - d2LastPrice
                        bar.low = d1LastPrice - d2LastPrice
                        bar.close = d1LastPrice - d2LastPrice
                        self.lineDiff.addBar(bar)

                        # 添加Ratio Bar
                        ratio_bar.open = d1LastPrice / d2LastPrice
                        ratio_bar.high = d1LastPrice / d2LastPrice
                        ratio_bar.low = d1LastPrice / d2LastPrice
                        ratio_bar.close = d1LastPrice / d2LastPrice
                        m5_ratio_bar = copy.copy(ratio_bar)
                        self.lineRatio.addBar(ratio_bar)
                        self.lineM5.addBar(m5_ratio_bar)

                        ratio = ratio_bar.close
                        if len(self.lineRatio.lineStateMean) > 0:
                            ratio = self.lineRatio.lineStateMean[-1]

                        # 添加Mean-Diff Bar
                        mean_bar.open = d1LastPrice / ratio - d2LastPrice
                        mean_bar.high = d1LastPrice / ratio - d2LastPrice
                        mean_bar.low = d1LastPrice / ratio - d2LastPrice
                        mean_bar.close = d1LastPrice / ratio - d2LastPrice
                        self.lineMD.addBar(mean_bar)
            D2.clear()
            return True

        except Exception as e:
            self.writeCtaError(u'策略初始化加载历史数据失败：'+str(e))
            return False

    def __InitZJDataFromSina(self):
        """从sina获取中金所初始化数据"""
        # 从sina加载最新的M1数据
        try:
            sleep(0.5)
            # 获取D2的分时数据
            D2 = {}
            requests.adapters.DEFAULT_RETRIES = 5
            s = requests.session()
            s.keep_alive = False

            url = u'http://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20t5nf_{0}=/InnerFuturesNewService.getFourDaysLine?symbol={0}'.format(self.Leg2Symbol)
            self.writeCtaLog(u'从sina下载{0}数据 {1}'.format(self.Leg2Symbol, url))
            response_data = s.get(url).content
            response_data = response_data.decode('gbk').split('=')[-1]
            response_data = response_data.replace('(', '')
            response_data = response_data.replace(');', '')
            responses = execjs.eval(response_data)
            datevalue = datetime.now().strftime('%Y-%m-%d')

            for j, day_item in enumerate(responses):
                for i, item in enumerate(day_item):
                    tick = CtaTickData()
                    tick.vtSymbol = self.vtSymbol
                    tick.symbol = self.vtSymbol

                    if len(item) >= 6:
                        datevalue = item[6]

                    tick.date = datevalue
                    tick.time = item[0] + u':00'
                    tick.datetime = datetime.strptime(tick.date + ' ' + tick.time, '%Y-%m-%d %H:%M:%S')

                    tick.lastPrice = float(item[1])
                    tick.volume = int(item[3])

                    if type(item[4]) == type(None):
                        tick.openInterest = 0
                    else:
                        tick.openInterest = int(item[4])

                    D2[tick.date+' '+tick.time] = tick

            sleep(0.5)

            url = u'http://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20t5nf_{0}=/InnerFuturesNewService.getFourDaysLine?symbol={0}'.format(self.Leg1Symbol)

            self.writeCtaLog(u'从sina下载{0}数据 {1}'.format(self.Leg1Symbol, url))
            response_data = s.get(url).content
            response_data = response_data.decode('gbk').split('=')[-1]
            response_data = response_data.replace('(', '')
            response_data = response_data.replace(');', '')
            responses = execjs.eval(response_data)
            datevalue = datetime.now().strftime('%Y-%m-%d')
            for j, day_item in enumerate(responses):
                for i, item in enumerate(day_item):
                    bar = CtaBarData()
                    bar.vtSymbol = self.vtSymbol
                    bar.symbol = self.vtSymbol

                    if len(item) >= 6:
                        datevalue = item[6]

                    bar.date = datevalue
                    bar.time = item[0]+u':00'
                    bar.datetime = datetime.strptime(bar.date+' '+bar.time, '%Y-%m-%d %H:%M:%S')

                    d1LastPrice = float(item[1])
                    bar.volume = int(item[3])

                    if bar.date+' '+bar.time in D2:
                        tick = D2[bar.date+' '+bar.time]
                        d2LastPrice = tick.lastPrice

                        ratio_bar = copy.copy(bar)
                        mean_bar = copy.copy(bar)

                        bar.open = d1LastPrice - d2LastPrice
                        bar.high = d1LastPrice - d2LastPrice
                        bar.low = d1LastPrice - d2LastPrice
                        bar.close = d1LastPrice - d2LastPrice
                        self.lineDiff.addBar(bar)

                        # 添加Ratio Bar
                        ratio_bar.open = d1LastPrice / d2LastPrice
                        ratio_bar.high = d1LastPrice / d2LastPrice
                        ratio_bar.low = d1LastPrice / d2LastPrice
                        ratio_bar.close = d1LastPrice / d2LastPrice
                        self.lineRatio.addBar(ratio_bar)
                        self.lineM5.addBar(ratio_bar)

                        ratio = ratio_bar.close
                        if len(self.lineRatio.lineStateMean) > 0:
                            ratio = self.lineRatio.lineStateMean[-1]

                        # 添加Mean-Diff Bar
                        mean_bar.open = d1LastPrice / ratio - d2LastPrice
                        mean_bar.high = d1LastPrice / ratio - d2LastPrice
                        mean_bar.low = d1LastPrice / ratio - d2LastPrice
                        mean_bar.close = d1LastPrice / ratio - d2LastPrice
                        self.lineMD.addBar(mean_bar)

            D2.clear()
            return True

        except Exception as e:
            self.writeCtaError(u'策略初始化加载历史数据失败：'+str(e))
            return False

    # ----------------------------------------------------------------------
    def __timeWindow(self, tick):
        """交易与平仓窗口"""
        # 交易窗口 避开早盘和夜盘的前5分钟，防止隔夜跳空。
        self.closeWindow = False
        self.tradeWindow = False
        self.openWindow = False

        # 初始化当日的首次交易
        #if (tick.datetime.hour == 9 or tick.datetime.hour == 21) and tick.datetime.minute == 0 and tick.datetime.second ==0:
        #  self.firstTrade = True

        # 开市期，波动较大，用于判断止损止盈，或开仓
        if (tick.datetime.hour == 9 or tick.datetime.hour == 21) and tick.datetime.minute < 10:
            self.openWindow = True

        # 日盘
        if tick.datetime.hour == 9 and ((tick.datetime.minute >= 0 and self.shortSymbol not in MARKET_ZJ) or tick.datetime.minute >= 15):
            self.tradeWindow = True
            return

        if tick.datetime.hour == 10:
            if (tick.datetime.minute <= 15 or tick.datetime.minute >= 30) or self.shortSymbol in MARKET_ZJ:
                self.tradeWindow = True
                return

        if tick.datetime.hour == 11 and tick.datetime.minute <= 30:
            self.tradeWindow = True
            return

        # 中金所是13:00开盘，大连、郑商、上期所，是13:30开盘
        if tick.datetime.hour == 13 and tick.datetime.minute >= 00:
            self.tradeWindow = True
            return

        # 大连、郑商、上期所，是15:00  收盘
        if tick.datetime.hour == 14:
            if tick.datetime.minute < 59 or self.shortSymbol in MARKET_ZJ:
                self.tradeWindow = True
                return

            if tick.datetime.minute == 59:                 # 日盘平仓
                self.closeWindow = True
                return

        # 中金所是15:15收盘
        if tick.datetime.hour == 15 and self.shortSymbol in MARKET_ZJ:
            if tick.datetime.minute < 14:
                self.tradeWindow = True
                return

            if tick.datetime.minute >= 14:                 # 日盘平仓
                self.closeWindow = True
                return

        # 夜盘
        if tick.datetime.hour == 21 and tick.datetime.minute >= 0:
            self.tradeWindow = True
            return

        # 上期 贵金属， 次日凌晨2:30
        if self.shortSymbol in NIGHT_MARKET_SQ1:
            if tick.datetime.hour == 22 or tick.datetime.hour == 23 or tick.datetime.hour == 0 or tick.datetime.hour ==1:
                self.tradeWindow = True
                return

            if tick.datetime.hour == 2:
                if tick.datetime.minute < 29:                 # 收市前29分钟
                    self.tradeWindow = True
                    return
                if tick.datetime.minute == 29:                 # 夜盘平仓
                    self.closeWindow = True
                    return
            return

        # 上期 有色金属，黑色金属，沥青 次日01:00
        if self.shortSymbol in NIGHT_MARKET_SQ2:
            if tick.datetime.hour == 22 or tick.datetime.hour == 23:
                self.tradeWindow = True
                return

            if tick.datetime.hour == 0:
                if tick.datetime.minute < 59:              # 收市前29分钟
                    self.tradeWindow = True
                    return

                if tick.datetime.minute == 59:                 # 夜盘平仓
                    self.closeWindow = True
                    return

            return

        # 上期 天然橡胶  23:00
        if self.shortSymbol in NIGHT_MARKET_SQ3:

            if tick.datetime.hour == 22:
                if tick.datetime.minute < 59:              # 收市前1分钟
                    self.tradeWindow = True
                    return

                if tick.datetime.minute == 59:                 # 夜盘平仓
                        self.closeWindow = True
                        return

        # 郑商、大连 23:30
        if self.shortSymbol in NIGHT_MARKET_ZZ or self.shortSymbol in NIGHT_MARKET_DL:
            if tick.datetime.hour == 22:
                self.tradeWindow = True
                return

            if tick.datetime.hour == 23:
                if tick.datetime.minute < 29:                 # 收市前1分钟
                    self.tradeWindow = True
                    return
                if tick.datetime.minute == 29 and tick.datetime.second > 30:                 # 夜盘平仓
                    self.closeWindow = True
                    return
            return

    def __resubmitFirstGrid(self, direction, lastVolume):
        """修改第一个网格的平仓价格"""

        if direction == DIRECTION_SHORT:
            grid = self.gt.upGrids[0]
            if not grid.openStatus or grid.orderRef != EMPTY_STRING:
                self.writeCtaLog(u'网格[open={0},close={1} 不满足状态'.format(grid.openPrice,grid.closePrice))
                return

            oldPrice = grid.closePrice
            if lastVolume > (grid.volume-grid.tradedVolume):
                grid.closePrice = grid.closePrice + self.gt.gridHeight
            else:
                grid.closePrice = grid.closePrice + self.minDiff

        if direction == DIRECTION_LONG:
            grid = self.gt.dnGrids[0]
            if not grid.openStatus  or grid.orderRef != EMPTY_STRING:
                self.writeCtaLog(u'网格[open={0},close={1} 不满足状态'.format(grid.openPrice,grid.closePrice))
                return

            oldPrice = grid.closePrice

            if lastVolume > grid.volume:
                grid.closePrice = grid.closePrice - self.gt.gridHeight
            else:
                grid.closePrice = grid.closePrice - self.minDiff

    def __checkAccountLimit(self):
        """主动检查是否超过总体资金占用比例"""
        c, a, p, pl = self.ctaEngine.getAccountInfo()
        if p > pl:
            return False

        return True

    def __recheckPositions(self):
        """重新计算持仓"""
        self.writeCtaLog(u'扫描网格，重新计算持仓')
        # 重置position
        self.position.clear()
        checks = EMPTY_INT

        # 扫描上网格
        for x in self.gt.upGrids[:]:
            # 已发送订单，已开仓，未平仓
            if x.openStatus and not x.closeStatus:
                closePrice = min(x.closePrice, self.curTick.lastPrice)
                x.orderRef = EMPTY_STRING
                x.orderStatus = False
                # 未平仓的volume=网格的volume-已交易的volume，
                # 更新仓位
                self.position.openPos(direction=DIRECTION_SHORT, vol=x.volume - x.tradedVolume,
                                           price=x.openPrice)

                checks = checks + 1
                self.writeCtaLog(u'增加空仓{0},V:{1}'.format(x.openPrice,x.volume - x.tradedVolume))

            elif x.orderStatus and not x.openStatus:
                self.writeCtaLog(u'重置网格[{0}]的开仓单委托'.format(x.openPrice))
                x.orderStatus = False
                x.orderRef = EMPTY_STRING

        if checks == EMPTY_INT:
            self.writeCtaLog(u'上网格没空单')

        checks = EMPTY_INT
        # 扫描下网格
        for x in self.gt.dnGrids[:]:
            # 已发送订单，已开仓，未平仓
            if x.openStatus and not x.closeStatus:
                closePrice = max(x.closePrice, self.curTick.lastPrice)
                x.orderStatus = False
                x.orderRef = EMPTY_STRING
                # 未平仓的volume=网格的volume-已交易的volume，
                # 更新仓位
                self.position.openPos(direction=DIRECTION_LONG, vol=x.volume - x.tradedVolume,
                                           price=x.openPrice)

                checks = checks + 1
                self.writeCtaLog(u'增加多仓{0},V:{1}'.format(x.openPrice, x.volume - x.tradedVolume))

            elif x.orderStatus and not x.openStatus:
                self.writeCtaLog(u'重置网格[{0}]的开仓单委托'.format(x.openPrice))
                x.orderStatus = False
                x.orderRef = EMPTY_STRING

        if checks == EMPTY_INT:
            self.writeCtaLog(u'下网格没有多单')

        self.gridpos = self.position.pos
        # 重置为已执行
        self.recheckPositions = False

    def __cancelLogic(self, dt, force=False):
        "撤单逻辑"""
        if len(self.uncompletedOrders) < 1:
            return

        # 实盘时不需要执行后续逻辑
        if not self.backtesting:
            return

        canceled_keys = []

        #if ((dt - self.lastOrderTime).seconds > self.cancelSeconds / i ) \
        #        or force:  # 超过设置的时间还未成交
        """
        {'SYMBOL': self.Leg1Symbol, 'DIRECTION': DIRECTION_SHORT,
         'OFFSET': OFFSET_OPEN, 'Volume': grid.volume,
         'Price': shortPrice, 'TradedVolume':0 ,
         'OrderTime': self.curDateTime,
         'Grid': grid}
         """

        order_keys = self.uncompletedOrders.keys()

        for order_key in order_keys:
            if order_key not in self.uncompletedOrders:
                self.writeCtaLog(u'{0}不在未完成的委托单中。'.format(order_key))
                continue
            order = self.uncompletedOrders[order_key]
            order_time = order['OrderTime']
            order_symbol = copy.copy(order['SYMBOL'])
            order_volume = order['Volume'] - order['TradedVolume']
            order_price = order['Price']

            if (dt - order_time).seconds > self.cancelSeconds:
                self.writeCtaWarning(u'{}超时{}秒未成交，取消委托单：{},{},{}'.format(order_symbol, (dt - order_time).seconds, order_key,order_volume,order_price))

                # 获得对应的网格,检查网格是否两个lge的order都未成交
                grid = order['Grid']
                orders_in_grid = grid.orderRef.split(';')
                if len(orders_in_grid) > 1:
                    self.writeCtaLog(u'{0}=>{1}网格两腿超时未成交，均撤单'.format(grid.openPrice,grid.closePrice))
                    for order_in_grid in orders_in_grid:
                        # 分别撤销委托单
                        self.cancelOrder(str(order_in_grid))
                        self.writeCtaLog(u'删除orderID:{0}'.format(order_in_grid))
                        try:
                            del self.uncompletedOrders[order_in_grid]
                        except Exception as ex:
                            self.writeCtaError(u'撤单时，uncompletedOrders找不到{0}'.format(order_in_grid))

                    grid.orderStatus = False
                    grid.orderRef = EMPTY_STRING
                    grid.orderDatetime = None
                    self.entrust = 0
                    continue

                # 撤销该委托单
                self.cancelOrder(str(order_key))

                # 撤销的委托单，属于平仓类，需要追平
                if order['OFFSET'] == OFFSET_CLOSE:
                    # 属于平多委托单
                    if order['DIRECTION'] == DIRECTION_SHORT:

                        if order_symbol == self.Leg1Symbol:
                            sellPrice = min(self.lastLeg1Tick.bidPrice1, self.lastLeg1Tick.lastPrice) - self.minDiff
                        else:
                            sellPrice = min(self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.lastPrice) - self.minDiff

                        orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_SELL, sellPrice, order_volume, self)

                        if orderID is None:
                            self.writeCtaError(u'重新提交{0} {1}手平多单{2}失败'.format(order_symbol,order_volume,sellPrice))
                            continue

                        # 添加到待删除的清单
                        canceled_keys.append(order_key)
                        # 更新网格的委托单
                        grid = order['Grid']
                        grid.orderRef = grid.orderRef.replace(order_key, orderID)
                        # 重新添加平多委托单
                        self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_SHORT,
                                                           'OFFSET': OFFSET_CLOSE, 'Volume': order_volume,'TradedVolume': EMPTY_INT,
                                                           'Price': sellPrice, 'OrderTime': self.curDateTime,
                                                           'Grid': grid}

                    # 属于平空委托单
                    else:
                        # 获取对价
                        if order_symbol == self.Leg1Symbol:
                            coverPrice = max(self.lastLeg1Tick.askPrice1, self.lastLeg1Tick.lastPrice) + self.minDiff
                        else:
                            coverPrice = max(self.lastLeg2Tick.askPrice1, self.lastLeg2Tick.lastPrice) + self.minDiff

                        orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_COVER, coverPrice, order_volume, self)
                        if orderID is None:
                            self.writeCtaError(u'重新提交{0} {1}手平空单{2}失败'.format(order_symbol, order_volume, coverPrice))
                            continue

                        # 添加到待删除的清单
                        canceled_keys.append(order_key)
                        # 更新网格的委托单
                        grid = order['Grid']
                        grid.orderRef = grid.orderRef.replace(order_key, orderID)
                        # 重新添加平空委托单
                        self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_LONG,
                                                           'OFFSET': OFFSET_CLOSE, 'Volume': order_volume,'TradedVolume': EMPTY_INT,
                                                           'Price': coverPrice, 'OrderTime': self.curDateTime,
                                                           'Grid': grid}

                # 撤销的委托单，属于开仓类，需要追开
                else:
                    # 属于开空委托单
                    if order['DIRECTION'] == DIRECTION_SHORT:
                        if order_symbol == self.Leg1Symbol:
                            shortPrice = min(self.lastLeg1Tick.bidPrice1, self.lastLeg1Tick.lastPrice) - self.minDiff
                        else:
                            shortPrice = min(self.lastLeg2Tick.bidPrice1, self.lastLeg2Tick.lastPrice) - self.minDiff

                        # 发送委托
                        orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_SHORT, shortPrice, order_volume, self)
                        if orderID is None or len(orderID) == 0:
                            self.writeCtaError(u'重新提交{0} {1}手开空单{2}失败'.format(order_symbol, order_volume, shortPrice))
                            continue

                        # 添加到待删除的清单
                        canceled_keys.append(order_key)
                        # 更新网格的委托单
                        grid = order['Grid']
                        grid.orderRef = grid.orderRef.replace(order_key, orderID)
                        if shortPrice < order_price:
                            # 修正止盈点位
                            if grid.direction == DIRECTION_SHORT:
                                grid.closePrice -= (order_price-shortPrice)
                            else:
                                grid.closePrice += (order_price-shortPrice)
                        # 重新添加开空委托单
                        self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_SHORT,
                                                           'OFFSET': OFFSET_OPEN, 'Volume': order_volume,
                                                           'Price': shortPrice, 'TradedVolume': EMPTY_INT,
                                                           'OrderTime': self.curDateTime,
                                                           'Grid': grid}
                    # 属于开多委托单
                    else:
                        if order_symbol == self.Leg1Symbol:
                            buyPrice = max(self.lastLeg1Tick.askPrice1, self.lastLeg1Tick.lastPrice) + self.minDiff
                        else:
                            buyPrice = max(self.lastLeg2Tick.askPrice1, self.lastLeg2Tick.lastPrice) + self.minDiff

                        # 发送委托
                        orderID = self.ctaEngine.sendOrder(order_symbol, CTAORDER_BUY, buyPrice, order_volume, self)
                        if orderID is None or len(orderID) == 0:
                            self.writeCtaLog(u'重新提交{0} {1}手开多单{2}失败'.format(order_symbol, order_volume, buyPrice))
                            continue

                        # 添加到待删除的清单
                        canceled_keys.append(order_key)
                        # 更新网格的委托单
                        grid = order['Grid']
                        grid.orderRef = grid.orderRef.replace(order_key, orderID)
                        if buyPrice > order_price:
                            # 修正止盈点位
                            if grid.direction == DIRECTION_SHORT:
                                grid.closePrice -= (buyPrice - order_price)
                            else:
                                grid.closePrice += (buyPrice - order_price)

                        # 重新添加开多委托单
                        self.uncompletedOrders[orderID] = {'SYMBOL': order_symbol, 'DIRECTION': DIRECTION_LONG,
                                                           'OFFSET': OFFSET_OPEN, 'Volume': order_volume,
                                                           'Price': buyPrice, 'TradedVolume': EMPTY_INT,
                                                           'OrderTime': self.curDateTime,
                                                           'Grid': grid}

        # 删除撤单的订单
        for key in canceled_keys:
            if key in self.uncompletedOrders:
                self.writeCtaLog(u'删除orderID:{0}'.format(key))
                del self.uncompletedOrders[key]


    # ----------------------------------------------------------------------
    def saveData(self):
        """保存过程数据"""
        # 保存Orders
        if not self.backtesting:
            return

        if not self.save_orders:
            return

        csvOutputFile = os.path.abspath(os.path.join(cta_engine_path, 'TestLogs',
                                                     'Orders_{0}.csv'.format(
                                                         datetime.now().strftime('%Y%m%d_%H%M'))))

        import csv
        csvWriteFile = file(csvOutputFile, 'wb')
        fieldnames = ['datetime', 'direction', 'offset', 'price', 'volume', 'type', 'force']
        writer = csv.DictWriter(f=csvWriteFile, fieldnames=fieldnames, dialect='excel')
        writer.writeheader()

        for row in self.save_orders:
            writer.writerow(row)

        signalOutputFile = os.path.abspath(os.path.join(cta_engine_path, 'TestLogs',
                                                     'Signals_{0}.csv'.format(
                                                         datetime.now().strftime('%Y%m%d_%H%M'))))

        signalWriteFile = file(signalOutputFile, 'wb')
        fieldnames2 = ['datetime', 'direction', 'price', 'M5_pre', 'M5', 'M1_pre','M1','cond1','cond2']
        writer2 = csv.DictWriter(f=signalWriteFile, fieldnames=fieldnames2, dialect='excel')
        writer2.writeheader()

        for row in self.save_signals.values():
            writer2.writerow(row)

def testRb(leg1_symbol, leg2_symbol, start_date, end_date, useMongoDB=False):

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)

    # 设置回测用的数据结束日期
    engine.setEndDate(end_date)

    # engine.connectMysql()
    engine.setDatabase(dbName='ticks', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小
    engine.setMarginRate(0.12)  # 合约的保证金比率

    settings = {}
    settings['vtSymbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['symbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['shortSymbol'] = 'RB'
    settings['minDiff'] = 1
    settings['inputSS'] = 1
    settings['name'] = 'S28_v11_{0}_{1}'.format(leg1_symbol, leg2_symbol)
    settings['mode'] = 'tick'
    settings['Leg1Symbol'] = leg1_symbol
    settings['Leg2Symbol'] = leg2_symbol
    settings['backtesting'] = True
    settings['baseUpLine'] = 150
    settings['baseMidLine'] = 0
    settings['baseDnLine'] = -150
    settings['height'] = 6
    settings['win'] = 6
    settings['volumeList'] = [1, 1, 2, 2, 2, 1, 1, 1, 1, 1]
    settings['maxPos'] = 54
    settings['maxLots'] = 1
    settings['autoLock'] = True

    settings['deadLine'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)).strftime(
        '%Y-%m-%d')  # '2016-02-01'
    settings['forceClose'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=5)).strftime(
        '%Y-%m-%d')  # '2016-02-01'

    # 删除本地json文件
    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_upGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_dnGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_DemoSpread, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 1000000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 3  # 固定交易费用（每次开平仓收费）

    if useMongoDB:
        engine.runBackTestingWithNonStrArbTickFromMongoDB(leg1Symbol=leg1_symbol,
                                          leg2Symbol=leg2_symbol)
    else:

        # 开始跑回测
        import platform
        p = str(platform.system())
        if p == 'Windows':
            leg1path = 'E:\\Ticks\\SQ'
            leg2path = 'E:\\Ticks\\SQ'
        else:
            leg1path = '/home/ubuntu/Ticks/SQ'
            leg2path = '/home/ubuntu/Ticks/SQ'

        engine.runBackTestingWithNonStrArbTickFile2(leg1MainPath=leg1path,
                                                    leg2MainPath=leg2path,
                                                    leg1Symbol=leg1_symbol,
                                                    leg2Symbol=leg2_symbol)

    # 显示回测结果
    engine.showBacktestingResult()
    # 保存策略的Order数据到excel
    engine.saveStrategyData()

def testRbs():

    test_list = []
    #d = {'leg1_symbol': 'RB1601', 'leg2_symbol': 'RB1605', 'start_date': '20150901', 'end_date': '20151228'}
    #test_list.append(d)

    #d = {'leg1_symbol': 'RB1605', 'leg2_symbol': 'RB1610', 'start_date': '20151201', 'end_date': '20160428'}
    #test_list.append(d)

    #d = {'leg1_symbol': 'RB1610', 'leg2_symbol': 'RB1701', 'start_date': '20160401', 'end_date': '20160928'}
    #test_list.append(d)

    #d = {'leg1_symbol': 'RB1701', 'leg2_symbol': 'RB1705', 'start_date': '20160730', 'end_date': '20161228'}
    #test_list.append(d)

    d = {'leg1_symbol': 'RB1705', 'leg2_symbol': 'RB1710', 'start_date': '20161130', 'end_date': '20170130'}
    test_list.append(d)

    for t in test_list:
        testRb(leg1_symbol=t['leg1_symbol'], leg2_symbol=t['leg2_symbol'], start_date=t['start_date'], end_date=t['end_date'], useMongoDB=True)

def testHcRb():

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20141201')

    # 设置回测用的数据结束日期
    engine.setEndDate('20150415')

    # engine.connectMysql()
    engine.setDatabase(dbName='ticks', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['vtSymbol'] = 'hc1505;rb1505'
    settings['symbol'] = 'hc1505;rb1505'
    settings['shortSymbol'] = 'HCRB'
    settings['minDiff'] = 1
    settings['inputSS'] = 1
    settings['name'] = 'HCRB'
    settings['mode'] = 'tick'
    settings['Leg1Symbol'] = 'hc1505'
    settings['Leg2Symbol'] = 'rb1505'
    settings['backtesting'] = True
    settings['baseUpLine'] = 237
    settings['baseMidLine'] = 190
    settings['baseDnLine'] = 80
    settings['height'] = 2
    settings['win'] = 4
    settings['maxPos'] = 40
    settings['maxLots'] = 5
    settings['deadLine'] = '2015-3-30'

    # 删除本地json文件
    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_upGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_dnGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_DemoSpread, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 300000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）
    # 开始跑回测
    #engine.runBackTestingWithNonStrArbTickFile(leg1MainPath='SHFE',
    #                                           leg2MainPath='SHFE',
    #                                           leg1Symbol='rb1610',
    #                                           leg2Symbol='rb1701')
    engine.runBackTestingWithNonStrArbTickFile2(leg1MainPath = 'SQ',
                                                leg2MainPath = 'SQ',
                                                leg1Symbol = 'hc1505',
                                                leg2Symbol = 'rb1505')

    # 显示回测结果
    engine.showBacktestingResult()
    # 保存策略的Order数据到excel
    engine.saveStrategyData()

def testTFT():
    """
    leg1_symbol = 'TF1603'
    leg2_symbol = 'T1603'
    start_date = '20151101'
    end_date = '20160228'


    leg1_symbol = 'TF1606'
    leg2_symbol = 'T1606'
    start_date = '20160201'
    end_date = '20160520'

    """
    leg1_symbol = 'TF1609'
    leg2_symbol = 'T1609'
    start_date = '20160501'
    end_date = '20160830'

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)

    # 设置回测用的数据结束日期
    engine.setEndDate(end_date)

    # engine.connectMysql()
    engine.setDatabase(dbName='ticks', symbol='TFT')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10000)  # 合约大小
    engine.setMarginRate(0.02) # 国债合约的保证金比率

    settings = {}
    settings['vtSymbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['symbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['shortSymbol'] = 'TF'
    settings['minDiff'] = 0.005
    settings['inputSS'] = 1
    settings['name'] = 'ZJTFTV4'
    settings['mode'] = 'tick'
    settings['Leg1Symbol'] = leg1_symbol
    settings['Leg2Symbol'] = leg2_symbol
    settings['backtesting'] = True
    settings['baseUpLine'] = 0.71
    settings['baseMidLine'] = 1.25
    settings['baseDnLine'] = 2.17
    settings['volumeList'] = [1, 1, 2, 3, 4, 1, 1, 1, 1, 1]
    settings['height'] = 6
    settings['win'] = 4
    settings['maxPos'] = 22
    settings['maxLots'] = 5
    settings['deadLine'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)).strftime('%Y-%m-%d') # '2016-02-01'
    settings['forceClose'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=5)).strftime('%Y-%m-%d')  # '2016-02-01'

    # 删除本地json文件

    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_upGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_dnGrids.json'.format(settings['name'])))

    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_DemoSpread, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 1000000  # 设置期初资金
    engine.maxCapital = 1000000  # 设置期初资金
    engine.percentLimit = 60  # 设置资金使用上限比例(%)F
    engine.barTimeInterval = 60  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）
    # 开始跑回测
    engine.runBackTestingWithNonStrArbTickFile(leg1MainPath='E:\\Ticks\\ZJ',
                                               leg2MainPath='E:\\Ticks\\ZJ',
                                               leg1Symbol=leg1_symbol,
                                               leg2Symbol=leg2_symbol)
    #engine.runBackTestingWithNonStrArbTickFile2(leg1MainPath = 'SQ',
    #                                            leg2MainPath = 'SQ',F
    #                                            leg1Symbol = 'rb1505',
    #                                            leg2Symbol = 'rb1510')

    # 显示回测结果
    engine.showBacktestingResult()
    # 保存策略的Order数据到excel
    engine.saveStrategyData()


def testMRMs():

    test_list = []

    # 总盈亏：	7,240.0
    #d = {'leg1_symbol': 'M1601', 'leg2_symbol': 'RM1601', 'start_date': '20150801', 'end_date': '20151228'}
    #test_list.append(d)

    # 总盈亏：	2,640.0
    #d = {'leg1_symbol': 'M1605', 'leg2_symbol': 'RM1605', 'start_date': '20151201', 'end_date': '20160428'}
    #test_list.append(d)

    # 总盈亏：	4,700.0
    #d = {'leg1_symbol': 'M1609', 'leg2_symbol': 'RM1609', 'start_date': '20160401', 'end_date': '20160828'}
    #test_list.append(d)

    #总盈亏：	9,640.0
    #d = {'leg1_symbol': 'M1701', 'leg2_symbol': 'RM1701', 'start_date': '20160801', 'end_date': '20161228'}
    #test_list.append(d)

    d = {'leg1_symbol': 'M1705', 'leg2_symbol': 'RM1705', 'start_date': '20161201', 'end_date': '20170428'}
    test_list.append(d)

    for t in test_list:
        testM_RM(leg1_symbol=t['leg1_symbol'], leg2_symbol=t['leg2_symbol'], start_date=t['start_date'], end_date=t['end_date'], useMongoDB=True)

def testM_RM(leg1_symbol, leg2_symbol, start_date, end_date, useMongoDB=False):

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)

    # 设置回测用的数据结束日期
    engine.setEndDate(end_date)

    # engine.connectMysql()
    engine.setDatabase(dbName='ticks', symbol='m')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['vtSymbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['symbol'] = '{0};{1}'.format(leg1_symbol, leg2_symbol)
    settings['shortSymbol'] = 'M_RM'
    settings['minDiff'] = 1
    settings['inputSS'] = 2
    settings['name'] = 'M_RM'
    settings['mode'] = 'tick'
    settings['Leg1Symbol'] = leg1_symbol
    settings['Leg2Symbol'] = leg2_symbol
    settings['backtesting'] = True
    settings['baseUpLine'] = 800
    settings['baseMidLine'] = 550
    settings['baseDnLine'] = 300
    settings['height'] = 6
    settings['win'] = 6
    settings['volumeList'] = [1, 1, 2, 2, 2, 1, 1, 1, 1, 1]
    settings['maxPos'] = 54
    settings['maxLots'] = 15
    settings['autoLock'] = True

    settings['deadLine'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)).strftime(
        '%Y-%m-%d')  # '2016-02-01'
    settings['forceClose'] = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=5)).strftime(
        '%Y-%m-%d')  # '2016-02-01'

    # 删除本地json文件
    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_upGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    filename = os.path.abspath(os.path.join(cta_engine_path, 'data', '{0}_dnGrids.json'.format(settings['name'])))
    if os.path.isfile(filename):
        print(u'{0}文件存在，先执行删除'.format(filename))
        try:
            os.remove(filename)
        except Exception as ex:
            print(u'{0}：{1}'.format(Exception, ex))

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_DemoSpread, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 1000000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）

    if useMongoDB:
        engine.runBackTestingWithNonStrArbTickFromMongoDB(leg1Symbol=leg1_symbol,
                                          leg2Symbol=leg2_symbol)
    else:

        # 开始跑回测
        import platform
        p = str(platform.system())
        if p == 'Windows':
            leg1path = 'E:\\Ticks\\DL'
            leg2path = 'E:\\Ticks\\ZZ'
        else:
            leg1path = '/home/ubuntu/Ticks/DL'
            leg2path = '/home/ubuntu/Ticks/ZZ'

        engine.runBackTestingWithNonStrArbTickFile2(leg1MainPath=leg1path,
                                                    leg2MainPath=leg2path,
                                                    leg1Symbol=leg1_symbol,
                                                    leg2Symbol=leg2_symbol)

    # 显示回测结果
    engine.showBacktestingResult()


# 从csv文件进行回测
if __name__ == '__main__':

    # 提供直接双击回测的功能

    from vnpy.trader.app.ctaStrategy.ctaBacktesting import *
    from vnpy.trader.setup_logger import setup_logger
    import os
    log_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    log_file_name = os.path.abspath(os.path.join(log_file_name, 'TestLogs',
                                                 '{0}_{1}.log'.format(Strategy_DemoSpread.className,
                                                                      datetime.now().strftime('%m%d_%H%M'))))
    setup_logger(
        filename=log_file_name,
        debug=False)
    # 回测螺纹
    testRbs()
    # 回测热卷螺纹
    # testHcRb()
    # 回测国债套利
    #testTFT()
    # 回测豆粕菜粕
    #testMRMs()



