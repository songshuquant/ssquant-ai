from ssquant.backtest.backtest_core import MultiSourceBacktester
import pandas as pd
import numpy as np
from ssquant.api.strategy_api import StrategyAPI

def initialize(api: StrategyAPI):
    """
    策略初始化函数
    
    Args:
        api: 策略API对象
    """
    api.log("多数据源策略初始化...")
    api.log("所有交易将使用下一根K线开盘价执行 (order_type='next_bar_open')")
    api.log("本版本使用自定义函数计算指标，不依赖API提供的指标计算功能")

# 自定义指标函数
def calculate_ma(price_series, period):
    """计算移动平均线"""
    return price_series.rolling(period).mean()

def is_crossover(fast_ma, slow_ma, idx):
    """判断上穿"""
    if idx < 1:
        return False
    return (fast_ma.iloc[idx-1] <= slow_ma.iloc[idx-1] and 
            fast_ma.iloc[idx] > slow_ma.iloc[idx])

def is_crossunder(fast_ma, slow_ma, idx):
    """判断下穿"""
    if idx < 1:
        return False
    return (fast_ma.iloc[idx-1] >= slow_ma.iloc[idx-1] and 
            fast_ma.iloc[idx] < slow_ma.iloc[idx])

def multi_source_strategy(api: StrategyAPI):
    """
    多数据源策略示例（无指标API版）
    
    使用多个数据源：
    - 数据源0: j888 5分钟K线
    - 数据源1: j888 15分钟K线
    - 数据源2: jm888 5分钟K线
    - 数据源3: jm888 15分钟K线
    
    策略逻辑：
    1. 每个数据源都单独交易，根据自身的均线交叉产生信号
    2. 5分钟和15分钟周期各自独立交易，不互相影响
    3. 当短期均线上穿长期均线时，开多仓
    4. 当短期均线下穿长期均线时，开空仓
    
    参数:
        fast_ma: 短期均线周期，默认5
        slow_ma: 长期均线周期，默认20
    
    注意：本版本使用自定义函数计算指标，不依赖API提供的指标计算功能
    """
    # 获取参数，如果未提供则使用默认值
    fast_ma = api.get_param('fast_ma', 5)  # 短期均线周期
    slow_ma = api.get_param('slow_ma', 20) # 长期均线周期
    
    # 确保至少有4个数据源
    if not api.require_data_sources(4):
        return
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)
    bar_datetime = api.get_datetime(0)
    
    # 打印各数据源的信息
    if bar_idx % 100 == 0:  # 每处理100条数据打印一次信息
        api.log(f"当前Bar索引: {bar_idx}, 日期时间: {bar_datetime}")
        api.log(f"策略参数 - 快线周期: {fast_ma}, 慢线周期: {slow_ma}")
        for i in range(4):
            ds = api.get_data_source(i)
            if ds:
                api.log(f"数据源{i}: {ds.symbol}_{ds.kline_period}, 当前价格: {ds.current_price}, 持仓: {ds.current_pos}")
    
    # 获取K线数据
    j888_5m_klines = api.get_klines(0)    # j888 5分钟K线
    j888_15m_klines = api.get_klines(1)   # j888 15分钟K线
    jm888_5m_klines = api.get_klines(2)   # jm888 5分钟K线
    jm888_15m_klines = api.get_klines(3)  # jm888 15分钟K线
    
    # 确保有足够的数据
    min_data_len = max(fast_ma, slow_ma) + 5  # 需要的最小数据长度
    if (len(j888_5m_klines) < min_data_len or len(j888_15m_klines) < min_data_len or 
        len(jm888_5m_klines) < min_data_len or len(jm888_15m_klines) < min_data_len):
        return
    
    # 获取收盘价
    j888_5m_close = j888_5m_klines['close']
    j888_15m_close = j888_15m_klines['close']
    jm888_5m_close = jm888_5m_klines['close']
    jm888_15m_close = jm888_15m_klines['close']
    
    # 计算均线 - 使用自定义函数和参数化的均线周期
    j888_5m_ma_fast = calculate_ma(j888_5m_close, fast_ma)
    j888_5m_ma_slow = calculate_ma(j888_5m_close, slow_ma)
    j888_15m_ma_fast = calculate_ma(j888_15m_close, fast_ma)
    j888_15m_ma_slow = calculate_ma(j888_15m_close, slow_ma)
    jm888_5m_ma_fast = calculate_ma(jm888_5m_close, fast_ma)
    jm888_5m_ma_slow = calculate_ma(jm888_5m_close, slow_ma)
    jm888_15m_ma_fast = calculate_ma(jm888_15m_close, fast_ma)
    jm888_15m_ma_slow = calculate_ma(jm888_15m_close, slow_ma)
    
    # 如果数据不足，直接返回
    if (pd.isna(j888_5m_ma_slow.iloc[bar_idx]) or pd.isna(j888_15m_ma_slow.iloc[bar_idx]) or
        pd.isna(jm888_5m_ma_slow.iloc[bar_idx]) or pd.isna(jm888_15m_ma_slow.iloc[bar_idx])):
        return
    
    # 获取当前持仓
    j888_5m_pos = api.get_pos(0)   # 数据源0持仓
    j888_15m_pos = api.get_pos(1)  # 数据源1持仓
    jm888_5m_pos = api.get_pos(2)  # 数据源2持仓
    jm888_15m_pos = api.get_pos(3) # 数据源3持仓
    
    # 获取当前价格
    j888_5m_price = j888_5m_close.iloc[bar_idx]
    jm888_5m_price = jm888_5m_close.iloc[bar_idx]
    j888_15m_price = j888_15m_close.iloc[bar_idx]
    jm888_15m_price = jm888_15m_close.iloc[bar_idx]
    
    # 计算交易信号 - 使用自定义函数
    if bar_idx < 2:
        return
        
    # 判断均线交叉
    j888_5m_long_signal = is_crossover(j888_5m_ma_fast, j888_5m_ma_slow, bar_idx)
    j888_5m_short_signal = is_crossunder(j888_5m_ma_fast, j888_5m_ma_slow, bar_idx)
    j888_15m_long_signal = is_crossover(j888_15m_ma_fast, j888_15m_ma_slow, bar_idx)
    j888_15m_short_signal = is_crossunder(j888_15m_ma_fast, j888_15m_ma_slow, bar_idx)
    jm888_5m_long_signal = is_crossover(jm888_5m_ma_fast, jm888_5m_ma_slow, bar_idx)
    jm888_5m_short_signal = is_crossunder(jm888_5m_ma_fast, jm888_5m_ma_slow, bar_idx)
    jm888_15m_long_signal = is_crossover(jm888_15m_ma_fast, jm888_15m_ma_slow, bar_idx)
    jm888_15m_short_signal = is_crossunder(jm888_15m_ma_fast, jm888_15m_ma_slow, bar_idx)
    
    # 交易单位
    unit = 1
    
    # 数据源0: j888 5分钟K线交易逻辑
    if j888_5m_pos > 0:  # 当前持多仓
        if j888_5m_short_signal:  # 平多信号
            api.log(f"J888 5分钟K线短期均线下穿长期均线，平多仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sell(volume=unit, order_type='next_bar_open', index=0)
            
            # 同时开空
            api.log(f"J888 5分钟K线短期均线下穿长期均线，开空仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=0)
            
    elif j888_5m_pos < 0:  # 当前持空仓
        if j888_5m_long_signal:  # 平空信号
            api.log(f"J888 5分钟K线短期均线上穿长期均线，平空仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buycover(volume=unit, order_type='next_bar_open', index=0)
            
            # 同时开多
            api.log(f"J888 5分钟K线短期均线上穿长期均线，开多仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=0)
            
    else:  # 当前无持仓
        if j888_5m_long_signal:  # 开多信号
            api.log(f"J888 5分钟K线短期均线上穿长期均线，开多仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=0)
        elif j888_5m_short_signal:  # 开空信号
            api.log(f"J888 5分钟K线短期均线下穿长期均线，开空仓，价格：{j888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=0)
    
    # 数据源1: j888 15分钟K线交易逻辑
    if j888_15m_pos > 0:  # 当前持多仓
        if j888_15m_short_signal:  # 平多信号
            api.log(f"J888 15分钟K线短期均线下穿长期均线，平多仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sell(volume=unit, order_type='next_bar_open', index=1)
            
            # 同时开空
            api.log(f"J888 15分钟K线短期均线下穿长期均线，开空仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=1)
            
    elif j888_15m_pos < 0:  # 当前持空仓
        if j888_15m_long_signal:  # 平空信号
            api.log(f"J888 15分钟K线短期均线上穿长期均线，平空仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buycover(volume=unit, order_type='next_bar_open', index=1)
            
            # 同时开多
            api.log(f"J888 15分钟K线短期均线上穿长期均线，开多仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=1)
            
    else:  # 当前无持仓
        if j888_15m_long_signal:  # 开多信号
            api.log(f"J888 15分钟K线短期均线上穿长期均线，开多仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=1)
        elif j888_15m_short_signal:  # 开空信号
            api.log(f"J888 15分钟K线短期均线下穿长期均线，开空仓，价格：{j888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=1)
    
    # 数据源2: jm888 5分钟K线交易逻辑
    if jm888_5m_pos > 0:  # 当前持多仓
        if jm888_5m_short_signal:  # 平多信号
            api.log(f"JM888 5分钟K线短期均线下穿长期均线，平多仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sell(volume=unit, order_type='next_bar_open', index=2)
            
            # 同时开空
            api.log(f"JM888 5分钟K线短期均线下穿长期均线，开空仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=2)
            
    elif jm888_5m_pos < 0:  # 当前持空仓
        if jm888_5m_long_signal:  # 平空信号
            api.log(f"JM888 5分钟K线短期均线上穿长期均线，平空仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buycover(volume=unit, order_type='next_bar_open', index=2)
            
            # 同时开多
            api.log(f"JM888 5分钟K线短期均线上穿长期均线，开多仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=2)
            
    else:  # 当前无持仓
        if jm888_5m_long_signal:  # 开多信号
            api.log(f"JM888 5分钟K线短期均线上穿长期均线，开多仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=2)
        elif jm888_5m_short_signal:  # 开空信号
            api.log(f"JM888 5分钟K线短期均线下穿长期均线，开空仓，价格：{jm888_5m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=2)
    
    # 数据源3: jm888 15分钟K线交易逻辑
    if jm888_15m_pos > 0:  # 当前持多仓
        if jm888_15m_short_signal:  # 平多信号
            api.log(f"JM888 15分钟K线短期均线下穿长期均线，平多仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sell(volume=unit, order_type='next_bar_open', index=3)
            
            # 同时开空
            api.log(f"JM888 15分钟K线短期均线下穿长期均线，开空仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=3)
            
    elif jm888_15m_pos < 0:  # 当前持空仓
        if jm888_15m_long_signal:  # 平空信号
            api.log(f"JM888 15分钟K线短期均线上穿长期均线，平空仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buycover(volume=unit, order_type='next_bar_open', index=3)
            
            # 同时开多
            api.log(f"JM888 15分钟K线短期均线上穿长期均线，开多仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=3)
            
    else:  # 当前无持仓
        if jm888_15m_long_signal:  # 开多信号
            api.log(f"JM888 15分钟K线短期均线上穿长期均线，开多仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.buy(volume=unit, order_type='next_bar_open', index=3)
        elif jm888_15m_short_signal:  # 开空信号
            api.log(f"JM888 15分钟K线短期均线下穿长期均线，开空仓，价格：{jm888_15m_price:.2f}，将在下一根K线开盘价执行")
            api.sellshort(volume=unit, order_type='next_bar_open', index=3)

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
        'align_data': False,             # 是否对齐数据
        'fill_method': 'ffill',         # 填充方法
        'debug': False                   # 启用调试模式
    })
    
    # 添加数据源0配置 - J888焦炭主力，添加两个不同周期，它们会被分别作为独立的数据源处理
    backtester.add_symbol_config(
        symbol='i888', 
        config={  # 焦炭配置
            'start_date': '2025-01-01',      # 回测开始日期
            'end_date': '2025-02-27',        # 回测结束日期（缩短回测周期，便于调试）
            'initial_capital': 100000.0,     # 初始资金，单位：元
            'commission': 0.0003,            # 手续费率，例如：0.0003表示万分之3
            'margin_rate': 0.1,              # 保证金率，例如：0.1表示10%
            'contract_multiplier': 10,       # 合约乘数，例如：螺纹钢期货每点10元
            'periods': [                     # 周期配置
                {'kline_period': '5m', 'adjust_type': '1'},  # 5分钟周期，后复权
                {'kline_period': '15m', 'adjust_type': '1'}, # 15分钟周期，后复权
            ]
    })
    
    # 添加数据源1配置 - JM888焦煤主力，添加两个不同周期
    backtester.add_symbol_config(
        symbol='jm888', 
        config={  # 焦煤配置
            'start_date': '2025-01-01',      # 回测开始日期
            'end_date': '2025-02-20',        # 回测结束日期（缩短回测周期，便于调试）
            'initial_capital': 100000.0,     # 初始资金，单位：元
            'commission': 0.0003,            # 手续费率
            'margin_rate': 0.1,              # 保证金率
            'contract_multiplier': 10,       # 合约乘数
            'periods': [                     # 周期配置
                {'kline_period': '5m', 'adjust_type': '1'},  # 5分钟周期，后复权
                {'kline_period': '15m', 'adjust_type': '1'}, # 15分钟周期，后复权
            ]
    })
    
    # 运行回测，数据源索引将按照如下顺序：
    # 0: j888_5m
    # 1: j888_15m
    # 2: jm888_5m
    # 3: jm888_15m
    results = backtester.run(
        strategy=multi_source_strategy,
        initialize=initialize,
        strategy_params=None
    )
