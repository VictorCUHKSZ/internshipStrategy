import talib as ta
import numpy as np
import pandas as pd

class sarSignal():

    def __init__(self):
        self.author = 'victor'
    
    def sar(self, am, paraDict):
        accelerate = paraDict['acceleration']
        rangePeriod = paraDict['rangePeriod']
        
        # pastHigh = ta.MAX(am.high, rangePeriod) + 1*ta.STDDEV(am.high, rangePeriod)
        # pastLow = ta.MIN(am.low, rangePeriod) - 1*ta.STDDEV(am.low, rangePeriod)
        # sar = ta.SAR(pastHigh, pastLow, accelerate, 10*accelerate)

        emaHigh = ta.EMA(am.high, rangePeriod)
        emaLow = ta.EMA(am.low, rangePeriod)
        
        sar = ta.SAR(emaHigh, emaLow, accelerate, 10*accelerate)
        # sar = ta.SAR(am.high, am.low, accelerate, 10*accelerate)
        
        # print('sar:', sar[-5:])
        return sar

    def fliterVol(self, am, paraDict):
        nDay = paraDict['nDay']
        nFilter = paraDict['nFilter']
        minPct = paraDict['minPct']
        returns = am.close[-1]/am.close[0] - 1
        
        if am.volume<ta.SMA(am.volume, nDay)-nFilter*ta.STDDEV(am.volume, nDay) or returns<minPct:
            filterCanTrade = -1
        else:
            filterCanTrade = 1
        return filterCanTrade
    
    def bigVolWeight(self, am, paraDict):
        bigVolPeriod = paraDict['bigVolPeriod']
        bigVolThreshold = paraDict['bigVolThreshold']
        bigMultiplier = paraDict['bigMultiplier']

        rangeHL = ta.MAX(am.high, bigVolPeriod)-ta.MIN(am.low, bigVolPeriod)
        bigVolRange = am.close[-1]*bigVolThreshold
        bigVol = 1 if (rangeHL[-1] >= bigVolRange) else 0

        lotMultiplier = 1
        if bigVol:
            lotMultiplier = bigMultiplier
        return lotMultiplier


        