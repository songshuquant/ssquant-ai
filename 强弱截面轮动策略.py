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
    api.log("强弱轮动策略初始化...")
    api.log("所有交易将使用下一根K线开盘价执行 (order_type='next_bar_open')")
    api.log("本策略通过比较不同品种的相对强弱进行轮动交易")
    
    # 获取策略参数
    lookback_period = api.get_param('lookback_period', 20)  # 回溯期
    
    api.log(f"参数设置 - 回溯期: {lookback_period}")

def calculate_relative_strength(price_series_list, lookback_period=20):
    """
    计算相对强弱指标
    
    Args:
        price_series_list: 价格序列列表
        lookback_period: 回溯期
        
    Returns:
        相对强弱指标列表
    """
    # 计算每个品种的相对强弱
    rs_list = []
    
    # 首先计算每个品种的回报率
    returns_list = [price_series.pct_change(periods=lookback_period) for price_series in price_series_list]
    
    # 计算相对强弱值（归一化）
    for i in range(len(returns_list)):
        rs_list.append(returns_list[i])
    
    return rs_list

def rank_instruments(rs_list, current_idx):
    """
    对品种进行排名
    
    Args:
        rs_list: 相对强弱指标列表
        current_idx: 当前索引
        
    Returns:
        排名结果，从强到弱排序的索引列表
    """
    # 获取当前的相对强弱值
    current_rs_values = [rs.iloc[current_idx] if not pd.isna(rs.iloc[current_idx]) else -np.inf for rs in rs_list]
    
    # 对索引按相对强弱值排序（从大到小）
    ranked_indices = np.argsort(current_rs_values)[::-1]
    
    return ranked_indices

def relative_strength_strategy(api: StrategyAPI):
    """
    强弱轮动策略
    
    该策略通过比较不同品种的相对强弱来选择交易品种。
    具体实现为：计算每个品种的相对强弱指标，
    选择最强的品种做多，最弱的品种做空。
    
    策略逻辑：
    1. 计算所有品种的相对强弱指标
    2. 根据相对强弱指标对品种进行排名
    3. 选择排名最强的品种做多
    4. 选择排名最弱的品种做空
    5. 定期重新评估排名并轮动持仓
    """
    # 确保至少有2个数据源
    if not api.require_data_sources(2):
        return
    
    # 获取策略参数
    lookback_period = api.get_param('lookback_period', 20)  # 回溯期
    rebalance_period = api.get_param('rebalance_period', 5)  # 再平衡周期（每隔多少个bar重新评估）
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)
    bar_datetime = api.get_datetime(0)
    
    # 获取数据源数量
    data_sources_count = api.get_data_sources_count()
    
    # 打印当前处理的数据
    if bar_idx % 100 == 0:
        api.log(f"当前Bar索引: {bar_idx}, 日期时间: {bar_datetime}")
    
    # 确保有足够的数据
    if bar_idx < lookback_period:
        return
    
    # 只在再平衡周期调整仓位
    if bar_idx % rebalance_period != 0:
        return
    
    # 获取所有价格序列
    price_series_list = []
    symbol_list = []
    
    for i in range(data_sources_count):
        klines = api.get_klines(i)
        price_series_list.append(klines['close'])
        
        # 获取品种名称
        data_source = api.get_data_source(i)
        symbol_list.append(f"{data_source.symbol}_{data_source.kline_period}")
    
    # 计算相对强弱指标
    rs_list = calculate_relative_strength(price_series_list, lookback_period)
    
    # 对品种进行排名
    ranked_indices = rank_instruments(rs_list, bar_idx)
    
    # 获取最强和最弱的品种索引
    strongest_idx = ranked_indices[0]
    weakest_idx = ranked_indices[-1]
    
    # 获取当前价格
    prices = [price_series_list[i].iloc[bar_idx] for i in range(data_sources_count)]
    
    # 打印排名信息
    api.log(f"品种相对强弱排名:")
    for rank, idx in enumerate(ranked_indices):
        api.log(f"第{rank+1}名: {symbol_list[idx]}, 价格: {prices[idx]:.2f}, 强弱值: {rs_list[idx].iloc[bar_idx]:.4f}")
    
    # 获取当前持仓
    positions = [api.get_pos(i) for i in range(data_sources_count)]
    
    # 交易单位
    unit = 1
    
    # 关闭所有品种的持仓
    for i in range(data_sources_count):
        if positions[i] != 0:
            api.log(f"平仓 {symbol_list[i]}")
            api.close_all(order_type='next_bar_open', index=i)
    
    # 做多最强品种
    api.log(f"做多最强品种: {symbol_list[strongest_idx]}")
    api.buy(volume=unit, order_type='next_bar_open', index=strongest_idx)
    
    # 做空最弱品种
    api.log(f"做空最弱品种: {symbol_list[weakest_idx]}")
    api.sellshort(volume=unit, order_type='next_bar_open', index=weakest_idx)

def relative_strength_momentum_strategy(api: StrategyAPI):
    """
    强弱动量策略变种
    
    该策略基于相对强弱指标，但增加了动量判断：
    只有当最强品种具有正动量时做多，
    只有当最弱品种具有负动量时做空。
    
    策略逻辑：
    1. 计算所有品种的相对强弱指标和动量指标
    2. 根据相对强弱指标对品种进行排名
    3. 如果最强品种具有正动量，做多
    4. 如果最弱品种具有负动量，做空
    5. 定期重新评估并轮动持仓
    """
    # 确保至少有2个数据源
    if not api.require_data_sources(2):
        return
    
    # 获取策略参数
    lookback_period = api.get_param('lookback_period', 20)  # 回溯期
    rebalance_period = api.get_param('rebalance_period', 5)  # 再平衡周期
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)
    bar_datetime = api.get_datetime(0)
    
    # 获取数据源数量
    data_sources_count = api.get_data_sources_count()
    
    # 打印当前处理的数据
    if bar_idx % 100 == 0:
        api.log(f"当前Bar索引: {bar_idx}, 日期时间: {bar_datetime}")
    
    # 确保有足够的数据
    if bar_idx < lookback_period:
        return
    
    # 只在再平衡周期调整仓位
    if bar_idx % rebalance_period != 0:
        return
    
    # 获取所有价格序列
    price_series_list = []
    symbol_list = []
    
    for i in range(data_sources_count):
        klines = api.get_klines(i)
        price_series_list.append(klines['close'])
        
        # 获取品种名称
        data_source = api.get_data_source(i)
        symbol_list.append(f"{data_source.symbol}_{data_source.kline_period}")
    
    # 计算相对强弱指标
    rs_list = calculate_relative_strength(price_series_list, lookback_period)
    
    # 对品种进行排名
    ranked_indices = rank_instruments(rs_list, bar_idx)
    
    # 获取最强和最弱的品种索引
    strongest_idx = ranked_indices[0]
    weakest_idx = ranked_indices[-1]
    
    # 计算动量（这里简单用回报率表示动量，正回报率表示正动量，负回报率表示负动量）
    momentum_list = [price_series.pct_change(periods=lookback_period).iloc[bar_idx] for price_series in price_series_list]
    
    # 判断最强和最弱品种的动量方向
    strongest_momentum = momentum_list[strongest_idx]
    weakest_momentum = momentum_list[weakest_idx]
    
    # 获取当前价格
    prices = [price_series_list[i].iloc[bar_idx] for i in range(data_sources_count)]
    
    # 打印排名和动量信息
    api.log(f"品种相对强弱排名和动量:")
    for rank, idx in enumerate(ranked_indices):
        api.log(f"第{rank+1}名: {symbol_list[idx]}, 价格: {prices[idx]:.2f}, " +
                f"强弱值: {rs_list[idx].iloc[bar_idx]:.4f}, 动量: {momentum_list[idx]:.4f}")
    
    # 获取当前持仓
    positions = [api.get_pos(i) for i in range(data_sources_count)]
    
    # 交易单位
    unit = 1
    
    # 关闭所有品种的持仓
    for i in range(data_sources_count):
        if positions[i] != 0:
            api.log(f"平仓 {symbol_list[i]}")
            api.close_all(order_type='next_bar_open', index=i)
    
    # 做多最强品种（如果具有正动量）
    if strongest_momentum > 0:
        api.log(f"做多最强品种 {symbol_list[strongest_idx]}，具有正动量 {strongest_momentum:.4f}")
        api.buy(volume=unit, order_type='next_bar_open', index=strongest_idx)
    else:
        api.log(f"最强品种 {symbol_list[strongest_idx]} 动量为负 {strongest_momentum:.4f}，不做多")
    
    # 做空最弱品种（如果具有负动量）
    if weakest_momentum < 0:
        api.log(f"做空最弱品种 {symbol_list[weakest_idx]}，具有负动量 {weakest_momentum:.4f}")
        api.sellshort(volume=unit, order_type='next_bar_open', index=weakest_idx)
    else:
        api.log(f"最弱品种 {symbol_list[weakest_idx]} 动量为正 {weakest_momentum:.4f}，不做空")

if __name__ == "__main__":
    # 导入API认证信息
    try:
        from ssquant.config.auth_config import get_api_auth
        API_USERNAME, API_PASSWORD = get_api_auth()
    except ImportError:
        print("警告：未找到 API_USERNAME, API_PASSWORD账户密码，请在上方get_api_auth()里面填写松鼠Quant俱乐部的账户密码")

    # 创建多数据源回测器
    backtester = MultiSourceBacktester()
    
    # 设置基础配置
    backtester.set_base_config({
        'username': API_USERNAME,
        'password': API_PASSWORD,
        'use_cache': True,
        'save_data': True,
        'align_data': True,
        'fill_method': 'ffill',
        'debug': True
    })
    
    # 添加多个品种配置
    # 黑色系品种：螺纹钢(rb)、热卷(hc)、铁矿石(i)、焦炭(j)、焦煤(jm)
    symbols = ['rb888', 'hc888', 'i888', 'j888', 'jm888']
    
    for symbol in symbols:
        backtester.add_symbol_config(
            symbol=symbol, 
            config={
                'start_date': '2023-01-01',
                'end_date': '2023-06-30',
                'initial_capital': 100000.0,
                'commission': 0.0003,
                'margin_rate': 0.1,
                'contract_multiplier': 10,
                'periods': [
                    {'kline_period': '1h', 'adjust_type': '1'},  # 日K线
                ]
        })
    
    # 策略参数
    strategy_params = {
        'lookback_period': 20,   # 回溯期
        'rebalance_period': 5    # 再平衡周期
    }
    
    # 运行回测 - 使用基础强弱轮动策略
    # results = backtester.run(
    #     strategy=relative_strength_strategy,
    #     initialize=initialize,
    #     strategy_params=strategy_params
    # )
    
    # 运行回测 - 使用动量增强版强弱轮动策略
    results = backtester.run(
        strategy=relative_strength_momentum_strategy,
        initialize=initialize,
        strategy_params=strategy_params
    )
    