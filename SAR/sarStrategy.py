from vnpy.trader.vtConstant import *
import numpy as np
import talib as ta
from datetime import timedelta, datetime, time
from vnpy.trader.utils.templates.orderTemplate import * 
from vnpy.trader.app.ctaStrategy import ctaBase
from sarClass import sarSignal

########################################################################
class sarStrategy(OrderTemplate):
    className = 'sarStrategy'
    author = 'Victor'

    # 参数列表，保存了参数的名称
    paramList = [
                 # 时间周期
                 'timeframeMap', 'barPeriod',
                 #  总秒，间隔，下单次数
                 'totalSecond', 'stepSecond','orderTime',
                 # 分批进场手数
                 'lot',
                 # 品种列表
                 'symbolList',
                 # signalParameter 计算信号的参数
                 'acceleration', 'rangePeriod',
                 'trailingPct', 'nHour', 'lowVolThreshold',
                 'calTime', 'dailyPeriod',
                 'stopControlTime', 
                #  'trailingPct','tpTime'
                 # 低波动率过滤阈值
                #  'volPeriod', 'lowVolThreshold',
                 ]

    # 变量列表，保存了变量的名称
    varList = []

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['posDict', 'eveningDict']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        super().__init__(ctaEngine, setting)

        self.paraDict = setting
        self.symbol = self.symbolList[0]
        self.lastBarTimeDict = {frameStr: datetime(2010,1,1) for frameStr in list(set(self.timeframeMap.values()))}
        self.algorithm = sarSignal()
        self.sar = np.array([])
        # varialbes
        self.orderDict = {'orderLongSet':set(), 'orderShortSet': set()}
        self.lastOrderDict = {'nextExecuteTime': datetime(2000, 1, 1)}
        self.lotMultiplier=1

        # 打印全局信号的字典
        self.globalStatus = {}
        self.chartLog = {
                        'datetime':[],
                        'sar': []
                        }
    
    def prepare_data(self):
        for timeframe in list(set(self.timeframeMap.values())):
            self.registerOnBar(self.symbol, timeframe, None)

    def arrayPrepared(self, period):
        am = self.getArrayManager(self.symbol, period)
        if not am.inited:
            return False, None
        else:
            return True, am

    # ----------------------------------------------------------------------
    def onInit(self):
        self.setArrayManagerSize(self.barPeriod)
        self.prepare_data()
        self.mail("chushihuaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.putEvent()
    
    # ----------------------------------------------------------------------
    def onStart(self):
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        self.putEvent()

    # 定时清除已经出场的单
    def delOrderID(self, orderSet):
        for orderId in list(orderSet):
            op = self._orderPacks[orderId]
            # 检查是否完全平仓
            if self.orderClosed(op):
                # 在记录中删除
                orderSet.discard(orderId)
                self.lastOrderDict['nextExecuteTime'] = self.currentTime + timedelta(minutes=self.stopControlTime)
    
    def isStopControled(self):
        return self.currentTime < self.lastOrderDict['nextExecuteTime']

    # 获得执行价格
    def priceExecute(self, bar):
        if bar.vtSymbol in self._tickInstance:
            tick = self._tickInstance[bar.vtSymbol]
            if tick.datetime >= bar.datetime:
                return tick.upperLimit * 0.99, tick.lowerLimit*1.01
        return bar.close*1.02, bar.close*0.98

    # 获取当前的持有仓位
    def getHoldVolume(self, orderSet):
        pos = 0
        for orderID in orderSet:
            op = self._orderPacks[orderID]
            holdVolume = op.order.tradedVolume
            closedVolume = self.orderClosedVolume(op)
            pos+= (holdVolume-closedVolume)
        return pos
    
    # 实盘在5sBar中洗价
    def on5sBar(self, bar):
        engineType = self.getEngineType()  # 判断engine模式
        if engineType != 'backtesting':
            self.checkOnPeriodStart(bar)
            self.checkOnPeriodEnd(bar)
            for idSet in self.orderDict.values():
                self.delOrderID(idSet)

    def onBar(self, bar):
        # 必须继承父类方法
        super().onBar(bar)
        # on bar下触发回测洗价逻辑
        engineType = self.getEngineType()  # 判断engine模式
        if engineType == 'backtesting':
            # 定时控制，开始
            self.checkOnPeriodStart(bar)
            # 回测时的下单手数按此方法调整
            self.lot = int(200000 / bar.close)
        # 定时清除已出场的单
            self.checkOnPeriodStart(bar)
            self.checkOnPeriodEnd(bar)
            for idSet in self.orderDict.values():
                self.delOrderID(idSet)
            # 执行策略逻辑
            self.strategy(bar)

    def on5MinBar(self, bar):
        engineType = self.getEngineType()  # 判断engine模式
        if engineType != 'backtesting':
            self.writeCtaLog('globalStatus%s'%(self.globalStatus))
            self.writeCtaLog('firstVolume:%s, secondVolume:%s'%(self.getHoldVolume(self.orderDict['orderLongSet']), self.getHoldVolume(self.orderDict['orderShortSet'])))
        else:
            pass
    def strategy(self, bar):
        signalPeriod= self.timeframeMap["signalPeriod"]

        # 根据出场信号出场
        exitLong, exitShort = self.exitSignal(signalPeriod)
        self.exitOrder(exitLong, exitShort)

        # 根据进场信号进场
        longSignal, shortSignal = self.entrySignal(bar, signalPeriod)
        self.entryOrder(bar, longSignal, shortSignal)

    def exitSignal(self, signalPeriod):

        exitLong, exitShort = 0,0
        arrayPrepared, amSignal = self.arrayPrepared(signalPeriod)
        if arrayPrepared:
            if len(self.sar):
                if amSignal.close[-1]<self.sar[-1]:
                    exitLong = 1
                if amSignal.close[-1]>self.sar[-1]:
                    exitShort = 1
        return exitLong, exitShort

    def exitOrder(self, exitLong, exitShort):
        if exitLong:
            for orderID in (self.orderDict['orderLongSet']):
                op = self._orderPacks[orderID]
                self.composoryClose(op)
        if exitShort:
            for orderID in (self.orderDict['orderShortSet']):
                op = self._orderPacks[orderID]
                self.composoryClose(op)

    def entrySignal(self, bar, signalPeriod):
        longSignal, shortSignal = 0, 0
        arrayPrepared1, amSignal = self.arrayPrepared(signalPeriod)
        # arrayPrepared2, amTrade = self.arrayPrepared(tradePeriod)

        # amSignalDatetime = datetime.strptime(amSignal.datetime[-1], "%Y%m%d %H:%M:%S")
        if arrayPrepared1:
            self.sar = self.algorithm.sar(amSignal, self.paraDict)
            # upRevertDn, dnRevertUp, upBreak, dnBreak
            # if len(self.sar):
            filterCanTrade = self.algorithm.fliterVol(amSignal, self.paraDict)
                # if not self.isStopControled():
            if filterCanTrade:
                if amSignal.close[-2]<self.sar[-2] and amSignal.close[-1]>self.sar[-1]:
                    longSignal = 1
                if amSignal.close[-2]>self.sar[-2] and amSignal.close[-1]<self.sar[-1]:
                    shortSignal = 1
            #    self.lotMultiplier = self.algorithm.bigVolWeight(amTrade, self.paraDict)
            self.globalStatus['longSignal'] = longSignal
            self.globalStatus['shortSignal'] = shortSignal
            self.chartLog['datetime'].append(datetime.strptime(amSignal.datetime[-1], "%Y%m%d %H:%M:%S"))
            self.chartLog['sar'].append(self.sar[-1])
        return longSignal, shortSignal

    def entryOrder(self, bar, longSignal, shortSignal):
        buyExecute, shortExecute = self.priceExecute(bar)
        lotSize = int(self.lot*self.lotMultiplier)
        if longSignal:
            if not self.orderDict['orderLongSet']:
                # 如果回测直接下单，如果实盘就分批下单
                longPos = self.lot//self.orderTime
                    # for orderID in self.timeLimitOrder(ctaBase.CTAORDER_BUY, self.symbol, buyExecute, self.lot, 120).vtOrderIDs:
                stepOrder = self.makeStepOrder(ctaBase.CTAORDER_BUY, bar.vtSymbol, buyExecute, lotSize, longPos, self.totalSecond, self.stepSecond)
                orderID = stepOrder.parentID
                self.orderDict['orderLongSet'].add(orderID)
                # op = self._orderPacks[orderID]
                # self.setAutoExit(op, bar.close*(1-self.trailingPct))
                # self.setConditionalClose(op, self.nHour*60*60)

        elif shortSignal:
            if not self.orderDict['orderShortSet']:
                shortPos = self.lot//self.orderTime
                stepOrder = self.makeStepOrder(ctaBase.CTAORDER_SHORT, bar.vtSymbol, shortExecute, lotSize, shortPos, self.totalSecond, self.stepSecond)
                orderID = stepOrder.parentID                
                self.orderDict['orderShortSet'].add(orderID)
                # op = self._orderPacks[orderID]
                # self.setAutoExit(op, bar.close*(1+self.trailingPct))
                # self.setConditionalClose(op, self.nHour*60*60)

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        super().onOrder(order)
        pass

    # ----------------------------------------------------------------------
    # 成交后用成交价设置第一张止损止盈
    def onTrade(self, trade):
        pass

    def onStopOrder(self, so):
        pass