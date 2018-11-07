# encoding: UTF-8

# 从okex下载数据，导入本地mongo数据库
from datetime import datetime, timezone

from pymongo import MongoClient
import requests
import execjs

mongodb_host = 'localhost'
mongodb_port = 27017
mongodb_user = ''
mongodb_pwd = ''
BITCOIN_DB_NAME = 'bitcoin'               # 虚拟策略矩阵的数据库名称
period_list = ['1min','3min','5min','15min','30min','1day','1week','1hour','2hour','4hour','6hour','12hour']
symbol_list = ['ltc_btc','eth_btc','etc_btc','bch_btc','btc_usdt','eth_usdt','ltc_usdt','etc_usdt','bch_usdt',
              'etc_eth','bt1_btc','bt2_btc','btg_btc','qtum_btc','hsr_btc','neo_btc','gas_btc',
              'qtum_usdt','hsr_usdt','neo_usdt','gas_usdt']


class mongodb_client(object):
    def __init__(self):
        self.dbClient = None

    # ----------------------------------------------------------------------
    def writeLog(self, content):
        """日志"""
        print(content)

    # ----------------------------------------------------------------------
    def dbConnect(self):
        """连接MongoDB数据库"""
        if not self.dbClient:

            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbClient = MongoClient(mongodb_host, mongodb_port, serverSelectionTimeoutMS=500)

                # 这里使用了ticks这个库来验证用户账号和密码
                # self.dbClient.ticks.authenticate(mongodb_user, mongodb_pwd, mechanism='SCRAM-SHA-1')

                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbClient.server_info()

                self.writeLog(u'MongoDB连接成功')
            except Exception as ex:
                self.writeLog(u'MongoDB连接失败{0}'.format(ex))
                exit(1)

    # ----------------------------------------------------------------------
    def dbInsert(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insert_one(d)

    # ----------------------------------------------------------------------
    def dbInsertMany(self, dbName, collectionName, dataList):
        """向MongoDB中插入Multi数据，dataList是具体数据List"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insertMany(dataList)

    # ----------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            cursor = collection.find(d)
            if cursor:
                return cursor
            else:
                return None
        else:
            return None

    # ----------------------------------------------------------------------
    def dbQueryBySort(self, dbName, collectionName, d, sortName, sortType, limitNum=0):
        """从MongoDB中读取数据，d是查询要求，sortName是排序的字段,sortType是排序类型
          返回的是数据库查询的指针"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            if limitNum > 0:
                cursor = collection.find(d).sort(sortName, sortType).limit(limitNum)
            else:
                cursor = collection.find(d).sort(sortName, sortType)

            if cursor:
                return cursor
            else:
                return None
        else:
            return None

    # ----------------------------------------------------------------------
    def dbDropCollection(self, dbName, collectionName):
        """从MongoDB中读取删除整个表"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.drop()

    def dbUpdate(self, dbName, collectionName, d, flt, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.replace_one(flt, d, upsert)
        else:
            self.writeLog(u'update fail')

    def dbDelete(self, dbName, collectionName, flt):
        """
        向mongodb中，删除数据，flt是过滤条件
        :param dbName: 
        :param collectionName: 
        :param flt: 
        :return: 
        """
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.deleteMany(flt)
        else:
            self.writeLog('delete fail')


def import_bar(symbol, period):
    """
    导入k线数据
    symbol：合约
    period: 周期: 1min,3min,5min,15min,30min,1day,3day,1hour,2hour,4hour,6hour,12hour
    """
    print('{}开始导入:{} {}数据'.format(datetime.now(), symbol, period))
    requests.adapters.DEFAULT_RETRIES = 5
    session = requests.session()
    session.keep_alive = False

    url = u'https://www.okex.com/api/v1/kline.do?symbol={}&type={}'.format(symbol, period)
    content = None
    try:
        content = session.get(url).content.decode('gbk')
    except Exception as ex:
        print('exception in get:{}'.format(url))
        return

    # print (content)

    bars = execjs.eval(content)

    # print (len(bars))

    for bar in bars:

        if len(bar) < 5:
            print('error when import bar:{}'.format(bar))
            break

        d = {}
        try:
            d['symbol'] = symbol
            d['datetime'] = datetime.fromtimestamp(bar[0] / 1000)
            d['date'] = d['datetime'].strftime('%Y-%m-%d')
            d['open'] = float(bar[1])
            d['high'] = float(bar[2])
            d['low'] = float(bar[3])
            d['close'] = float(bar[4])
            d['volume'] = float(bar[5])
        except Exception as ex:
            print('error when convert bar:{}'.format(bar))
            break

        flt = {
            'symbol': symbol,
            'datetime': d['datetime']
        }

        mc.dbUpdate(BITCOIN_DB_NAME, period, d, flt, upsert=True)

    print(u'{}导入{} {}数据结束'.format(datetime.now(), symbol, period))


if __name__ == '__main__':

    mc=mongodb_client()
    mc.dbConnect()


    records = []
    for symbol in symbol_list:
        for period in period_list:
            d = {'symbol':symbol,'period':period}
            flt = {'symbol': symbol}
            res = mc.dbQuery(BITCOIN_DB_NAME, period, flt)
            d['before'] = res.count()
            import_bar(symbol, period)
            res = mc.dbQuery(BITCOIN_DB_NAME, period, flt)
            d['after'] = res.count()

            records.append(d)
    print(u'更新完成')
    for r in records:
        print(r)




