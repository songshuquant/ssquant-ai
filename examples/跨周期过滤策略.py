"""
双均线跨周期过滤策略

策略描述:
1. 使用15分钟K线进行实际交易（短周期）
2. 使用60分钟K线作为趋势过滤（长周期）
3. 只有当60分钟K线趋势与15分钟K线信号一致时，才执行15分钟K线的交易信号
4. 趋势判断方法：通过60分钟K线的均线多空判断

交易规则:
- 多头条件：60分钟K线快速均线 > 慢速均线（多头趋势） + 15分钟K线快速均线上穿慢速均线
- 空头条件：60分钟K线快速均线 < 慢速均线（空头趋势） + 15分钟K线快速均线下穿慢速均线
"""

# 导入回测器
from ssquant.backtest.backtest_core import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI
import pandas as pd
import numpy as np

def initialize(api: StrategyAPI):
    """
    策略初始化函数
    
    Args:
        api: 策略API对象
    """
    api.log("双均线跨周期过滤策略初始化")
    
    # 获取参数
    fast_ma_15m = api.get_param('fast_ma_15m', 5)
    slow_ma_15m = api.get_param('slow_ma_15m', 20)
    fast_ma_60m = api.get_param('fast_ma_60m', 5)
    slow_ma_60m = api.get_param('slow_ma_60m', 20)
    
    api.log(f"参数设置 - 15分钟周期: 快线={fast_ma_15m}, 慢线={slow_ma_15m}")
    api.log(f"参数设置 - 60分钟周期: 快线={fast_ma_60m}, 慢线={slow_ma_60m}")

def cross_period_ma_strategy(api: StrategyAPI):
    """
    双均线跨周期过滤策略
    
    Args:
        api: 策略API对象
    """
    # 确保至少有2个数据源
    if not api.require_data_sources(2):
        return
    
    # 获取参数
    fast_ma_15m = api.get_param('fast_ma_15m', 5)
    slow_ma_15m = api.get_param('slow_ma_15m', 20)
    fast_ma_60m = api.get_param('fast_ma_60m', 5)
    slow_ma_60m = api.get_param('slow_ma_60m', 20)
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)  # 使用15分钟K线的索引
    bar_datetime = api.get_datetime(0)
    
    # 打印各数据源的信息
    if bar_idx % 20 == 0:  # 每处理20条数据打印一次信息
        api.log(f"当前Bar索引: {bar_idx}, 日期时间: {bar_datetime}")
        for i in range(2):
            ds = api.get_data_source(i)
            if ds:
                api.log(f"数据源{i}: {ds.symbol}_{ds.kline_period}, 当前价格: {ds.current_price}, 持仓: {ds.current_pos}")
    
    # 获取K线数据
    klines_15m = api.get_klines(0)  # 15分钟K线 (数据源0)
    klines_60m = api.get_klines(1)  # 60分钟K线 (数据源1)
    
    # 确保有足够的数据
    if len(klines_15m) < slow_ma_15m + 5 or len(klines_60m) < slow_ma_60m + 5:
        return
    
    # 获取收盘价
    close_15m = klines_15m['close']
    close_60m = klines_60m['close']
    
    # 计算均线
    ma_fast_15m = close_15m.rolling(fast_ma_15m).mean()
    ma_slow_15m = close_15m.rolling(slow_ma_15m).mean()
    ma_fast_60m = close_60m.rolling(fast_ma_60m).mean()
    ma_slow_60m = close_60m.rolling(slow_ma_60m).mean()
    
    # 如果数据不足，直接返回
    if (pd.isna(ma_slow_15m.iloc[bar_idx]) or pd.isna(ma_slow_60m.iloc[bar_idx])):
        return
    
    # 获取当前和前一个周期的均线值
    curr_fast_15m = ma_fast_15m.iloc[bar_idx]
    prev_fast_15m = ma_fast_15m.iloc[bar_idx - 1]
    curr_slow_15m = ma_slow_15m.iloc[bar_idx]
    prev_slow_15m = ma_slow_15m.iloc[bar_idx - 1]
    
    curr_fast_60m = ma_fast_60m.iloc[bar_idx]
    curr_slow_60m = ma_slow_60m.iloc[bar_idx]
    
    # 获取当前持仓和价格
    current_pos = api.get_pos(0)  # 只在15分钟周期上交易
    current_price = close_15m.iloc[bar_idx]
    
    # 判断60分钟周期的趋势
    trend_60m_bullish = curr_fast_60m > curr_slow_60m  # 60分钟周期多头趋势
    trend_60m_bearish = curr_fast_60m < curr_slow_60m  # 60分钟周期空头趋势
    
    # 判断15分钟周期的信号
    signal_15m_buy = prev_fast_15m <= prev_slow_15m and curr_fast_15m > curr_slow_15m  # 15分钟金叉
    signal_15m_sell = prev_fast_15m >= prev_slow_15m and curr_fast_15m < curr_slow_15m  # 15分钟死叉
    
    # 记录当前价格、均线和趋势
    api.log(f"当前时间: {bar_datetime}, 价格: {current_price:.2f}")
    api.log(f"15分钟周期 - 快线: {curr_fast_15m:.2f}, 慢线: {curr_slow_15m:.2f}")
    api.log(f"60分钟周期 - 快线: {curr_fast_60m:.2f}, 慢线: {curr_slow_60m:.2f}")
    api.log(f"60分钟趋势: {'多头' if trend_60m_bullish else '空头' if trend_60m_bearish else '中性'}")
    
    # 交易逻辑：只有当60分钟周期趋势和15分钟周期信号一致时，才执行交易
    
    # 多头条件：60分钟多头趋势 + 15分钟金叉
    if trend_60m_bullish and signal_15m_buy:
        if current_pos <= 0:  # 如果没有持仓或者空头持仓
            # 先平掉所有仓位，再开多仓
            api.close_all(order_type='next_bar_open', index=0)
            api.buy(volume=1, order_type='next_bar_open', index=0)
            api.log(f"满足多头条件：60分钟多头趋势 + 15分钟金叉，平仓并开多单")
    
    # 空头条件：60分钟空头趋势 + 15分钟死叉
    elif trend_60m_bearish and signal_15m_sell:
        if current_pos >= 0:  # 如果没有持仓或者多头持仓
            # 先平掉所有仓位，再开空仓
            api.close_all(order_type='next_bar_open', index=0)
            api.sellshort(volume=1, order_type='next_bar_open', index=0)
            api.log(f"满足空头条件：60分钟空头趋势 + 15分钟死叉，平仓并开空单")
    
    # 记录当前持仓
    api.log(f"当前持仓: {current_pos}")

if __name__ == "__main__":
    # 导入API认证信息
    try:
        from ssquant.config.auth_config import get_api_auth
        API_USERNAME, API_PASSWORD = get_api_auth()
    except ImportError:
        print("警告：未找到 auth_config.py 文件，请在下方填写您的认证信息：API_USERNAME和API_PASSWORD")
        API_USERNAME = ""
        API_PASSWORD = ""

    # 创建多数据源回测器
    backtester = MultiSourceBacktester()
    
    # 设置基础配置
    backtester.set_base_config({
        'username': API_USERNAME,       # 使用配置文件中的用户名
        'password': API_PASSWORD,       # 使用配置文件中的密码
        'use_cache': True,              # 是否使用缓存数据
        'save_data': True,              # 是否保存数据
        'align_data': True,             # 是否对齐数据
        'fill_method': 'ffill',         # 填充方法
        'debug': False                   # 启用调试模式
    })
    
    # 添加数据源配置 - 焦炭J888主力合约
    backtester.add_symbol_config(
        symbol='j888',  # 焦炭主力连续
        config={
            'start_date': '2022-01-01',
            'end_date': '2025-02-01',
            'initial_capital': 100000.0,
            'commission': 0.0001,        # 手续费率
            'margin_rate': 0.1,          # 保证金率
            'contract_multiplier': 100,  # 合约乘数
            'slippage': 0,               # 滑点
            'periods': [
                {'kline_period': '15m', 'adjust_type': '1'},  # 15分钟交易周期
                {'kline_period': '60m', 'adjust_type': '1'},  # 60分钟过滤周期
            ]  
        }
    )
    
    # 设置策略参数
    strategy_params = {
        'fast_ma_15m': 5,   # 15分钟周期快速均线周期
        'slow_ma_15m': 20,  # 15分钟周期慢速均线周期
        'fast_ma_60m': 5,   # 60分钟周期快速均线周期
        'slow_ma_60m': 20,  # 60分钟周期慢速均线周期
    }
    
    # 运行回测
    results = backtester.run(
        strategy=cross_period_ma_strategy,
        initialize=initialize,
        strategy_params=strategy_params,
    )
    