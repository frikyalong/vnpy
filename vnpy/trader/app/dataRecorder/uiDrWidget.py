# encoding: UTF-8

'''
行情记录模块相关的GUI控制组件
'''

import json

from vnpy.trader.uiBasicWidget import QtWidgets, QtGui, QtCore
from vnpy.trader.vtEvent import *


########################################################################
class TableCell(QtWidgets.QTableWidgetItem):
    """居中的单元格"""

    #----------------------------------------------------------------------
    def __init__(self, text=None, mainEngine=None):
        """Constructor"""
        super(TableCell, self).__init__()
        self.data = None
        self.setTextAlignment(QtCore.Qt.AlignCenter)
        if text:
            self.setContent(text)
    
    #----------------------------------------------------------------------
    def setContent(self, text):
        """设置内容"""
        if text == '0' or text == '0.0':
            self.setText('')
        else:
            self.setText(str(text))


########################################################################
class DrEngineManager(QtWidgets.QWidget):
    """行情数据记录引擎管理组件"""
    signal = QtCore.Signal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, drEngine, eventEngine, parent=None):
        """Constructor"""
        super(DrEngineManager, self).__init__(parent)
        
        self.drEngine = drEngine
        self.eventEngine = eventEngine
        
        self.initUi()
        self.updateSetting()
        self.registerEvent() 
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'行情数据记录工具')
        
        # 记录合约配置监控
        tickLabel = QtWidgets.QLabel(u'Tick记录')
        self.tickTable = QtWidgets.QTableWidget()
        self.tickTable.setColumnCount(2)
        self.tickTable.verticalHeader().setVisible(False)
        self.tickTable.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        #self.tickTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tickTable.setAlternatingRowColors(True)
        self.tickTable.setHorizontalHeaderLabels([u'合约代码', u'接口'])
        
        barLabel = QtWidgets.QLabel(u'Bar记录')
        self.barTable = QtWidgets.QTableWidget()
        self.barTable.setColumnCount(2)
        self.barTable.verticalHeader().setVisible(False)
        self.barTable.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        #self.barTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self.barTable.setAlternatingRowColors(True)        
        self.barTable.setHorizontalHeaderLabels([u'合约代码', u'接口'])

        renkoLabel = QtWidgets.QLabel(u'RenkoBar')
        self.renkoTable = QtWidgets.QTableWidget()
        self.renkoTable.setColumnCount(2)
        self.renkoTable.verticalHeader().setVisible(False)
        self.renkoTable.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        # self.renkoTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self.renkoTable.setAlternatingRowColors(True)
        self.renkoTable.setHorizontalHeaderLabels([u'合约代码', u'高度'])

        activeLabel = QtWidgets.QLabel(u'主力合约')
        self.activeTable = QtWidgets.QTableWidget()
        self.activeTable.setColumnCount(2)
        self.activeTable.verticalHeader().setVisible(False)
        self.activeTable.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        #self.activeTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self.activeTable.setAlternatingRowColors(True)        
        self.activeTable.setHorizontalHeaderLabels([u'主力代码', u'合约代码'])

        # 日志监控
        self.logMonitor = QtWidgets.QTextEdit()
        self.logMonitor.setReadOnly(True)
        self.logMonitor.setMinimumHeight(600)
        
        # 设置布局
        grid = QtWidgets.QGridLayout()
        
        grid.addWidget(tickLabel, 0, 0)
        grid.addWidget(barLabel, 0, 1)
        grid.addWidget(renkoLabel, 0, 2)
        grid.addWidget(activeLabel, 0, 3)

        grid.addWidget(self.tickTable, 1, 0)
        grid.addWidget(self.barTable, 1, 1)
        grid.addWidget(self.renkoTable, 1, 2)
        grid.addWidget(self.activeTable, 1, 3)
        
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(self.logMonitor)
        self.setLayout(vbox)

    #----------------------------------------------------------------------
    def updateLog(self, event):
        """更新日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.logMonitor.append(content)
    
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateLog)
        self.eventEngine.register(EVENT_DATARECORDER_LOG, self.signal.emit)
        
    #----------------------------------------------------------------------
    def updateSetting(self):
        """显示引擎行情记录配置"""
        with open(self.drEngine.settingFilePath) as f:
            drSetting = json.load(f)
    
            if 'tick' in drSetting:
                l = drSetting['tick']
    
                for setting in l:
                    self.tickTable.insertRow(0)
                    self.tickTable.setItem(0, 0, TableCell(setting[0]))
                    self.tickTable.setItem(0, 1, TableCell(setting[1]))
    
            if 'bar' in drSetting:
                l = drSetting['bar']
    
                for setting in l:
                    self.barTable.insertRow(0)
                    self.barTable.setItem(0, 0, TableCell(setting[0]))
                    self.barTable.setItem(0, 1, TableCell(setting[1]))

            if 'renko' in drSetting:
                l = drSetting['renko']

                for setting in l:
                    self.renkoTable.insertRow(0)
                    self.renkoTable.setItem(0, 0, TableCell(setting.get('vtSymbol','')))
                    self.renkoTable.setItem(0, 1, TableCell(setting.get('height',0)))
            if 'active' in drSetting:
                d = drSetting['active']
    
                for activeSymbol, symbol in d.items():
                    self.activeTable.insertRow(0)
                    self.activeTable.setItem(0, 0, TableCell(activeSymbol))
                    self.activeTable.setItem(0, 1, TableCell(symbol))
    
    
    
    



    
    