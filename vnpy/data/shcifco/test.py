# encoding: UTF-8

from __future__ import print_function
from __future__ import absolute_import
from vnpy.data.shcifco.vnshcifco import ShcifcoApi, PERIOD_1MIN, PERIOD_60MIN


if __name__ == "__main__":
    ip = 'dsdx.shcifco.com'
    port  = '10083'
    token = '50404935ba9cb370de2ac22474966163'
    # symbol = 'rb1901,ru1901,m1901,i1901,cu1901,ni1901,hc1901,y1901,jm1901,cf1901,zn1901,sr1901'
    symbol = 'cu1901'
    # 创建API对象
    api = ShcifcoApi(ip, port, token)
    
    # 获取最新tick
    # print(api.getLastTick(symbol))
    #
    # # 获取最新价格
    # print(api.getLastPrice(symbol))
    #
    # # 获取最新分钟线
    # print(api.getLastBar(symbol))
    
    # 获取历史分钟线
    print(api.getHisBar(symbol, 50, period='1h'))
    
    