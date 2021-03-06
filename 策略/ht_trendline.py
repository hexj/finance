# !/usr/bin/env python
# -*- coding: utf-8 -*-

# 策略代码总共分为三大部分，1)PARAMS变量 2)initialize函数 3)handle_data函数
# 请根据指示阅读。或者直接点击运行回测按钮，进行测试，查看策略效果。

# 策略名称：Hilbert Transform - Instantaneous Trendline指标策略
# 关键词：希尔伯特变换、均线。
# 方法：
# 1)改进的均线指标，降低延迟；
# 2)最新价格在均线之上时买入，在均线之下时卖出


import numpy as np
import talib

# 阅读1，首次阅读可跳过:
# PARAMS用于设定程序参数，回测的起始时间、结束时间、滑点误差、初始资金和持仓。
# 可以仿照格式修改，基本都能运行。如果想了解详情请参考新手学堂的API文档。
PARAMS = {
    "start_time": "2017-06-01 00:00:00",
    "end_time": "2017-08-20 00:00:00",
    "commission": 0.002,  # 手续费
    "slippage": 0.001,  # 交易滑点
    "account_initial": {"huobi_cny_cash": 10000,
                        "huobi_cny_btc": 0},
}


# 阅读2，遇到不明白的变量可以跳过，需要的时候回来查阅:
# initialize函数是两大核心函数之一（另一个是handle_data），用于初始化策略变量。
# 策略变量包含：必填变量，以及非必填（用户自己方便使用）的变量
def initialize(context):
    # 设置回测频率, 可选："1m", "5m", "15m", "30m", "60m", "4h", "1d", "1w"
    context.frequency = "4h"
    # 设置回测基准, 比特币："huobi_cny_btc", 莱特币："huobi_cny_ltc", 以太坊："huobi_cny_eth"
    # context.benchmark = "huobi_cny_btc"
    context.benchmark = "huobi_cny_eth"
    # 设置回测标的, 比特币："huobi_cny_btc", 莱特币："huobi_cny_ltc", 以太坊："huobi_cny_eth"
    # context.security = "huobi_cny_btc"
    context.security = "huobi_cny_eth"
    # 获取历史数据的长度
    context.user_data.ht_window = 100
    context.user_data.upper = 0.01
    context.user_data.lower = 0.01
    context.user_data.stop_loss = 0.1
    context.user_data.max_net = None
    # 至此initialize函数定义完毕。


# 阅读3，策略核心逻辑：
# handle_data函数定义了策略的执行逻辑，按照frequency生成的bar依次读取并执行策略逻辑，直至程序结束。
# handle_data和bar的详细说明，请参考新手学堂的解释文档。
def handle_data(context):
    # 获取历史数据, 取后window根bar
    hist = context.data.get_price(context.security, count=context.user_data.ht_window,
                                  frequency='60m')
    if len(hist.index) < context.user_data.ht_window:
        context.log.warn("bar的数量不足, 等待下一根bar...")
        return

    # 历史收盘价
    hist_close = np.array(hist["close"])
    # 初始化买入/卖出信号
    long_signal_triggered = False
    short_signal_triggered = False
    # 计算指标值
    ht_line = talib.HT_TRENDLINE(hist_close)

    current_price = context.data.get_current_price(context.security)
    current_drawdown = 0

    if context.account.huobi_cny_eth > HUOBI_CNY_ETH_MIN_ORDER_QUANTITY:
        if context.user_data.max_net is None:
            context.user_data.max_net = context.account.huobi_cny_net
        else:
            if context.account.huobi_cny_net > context.user_data.max_net:
                context.user_data.max_net = context.account.huobi_cny_net
        current_drawdown = (context.account.huobi_cny_net - context.user_data.max_net) / context.user_data.max_net
    else:
        context.user_data.max_net = None
    context.log.info('dd = %s'%current_drawdown)
    if -current_drawdown >= context.user_data.stop_loss:
        context.log.info("触发止损信号")
        short_signal_triggered = True
    else:
        #  产生买入/卖出信号
        if current_price > ht_line[-1]*(1+context.user_data.upper):
            long_signal_triggered = True
        elif current_price < ht_line[-1]*(1-context.user_data.lower):
            short_signal_triggered = True

    # 有卖出信号，且持有仓位，则全仓卖出
    if short_signal_triggered:
        if context.account.huobi_cny_eth >= HUOBI_CNY_ETH_MIN_ORDER_QUANTITY:
            context.log.info("正在卖出 %s" % context.security)
            context.log.info("卖出数量为 %s" % context.account.huobi_cny_eth)
            context.order.sell_limit(context.security, quantity=str(context.account.huobi_cny_eth),
                                     price=str(hist_close[-1] * 0.999))
        else:
            context.log.info("仓位不足，无法卖出")
    # 有买入信号，且持有现金，则全仓买入
    elif long_signal_triggered:
        if context.account.huobi_cny_cash >= HUOBI_CNY_ETH_MIN_ORDER_CASH_AMOUNT:
            context.log.info("正在买入 %s" % context.security)
            context.log.info("下单金额为 %s 元" % context.account.huobi_cny_cash)
            context.order.buy_limit(context.security,
                                    quantity=str(context.account.huobi_cny_cash / hist_close[-1] * 0.999),
                                    price=str(hist_close[-1] * 1.001))
        else:
            context.log.info("现金不足，无法下单")
    else:
        context.log.info("无交易信号，进入下一根bar")