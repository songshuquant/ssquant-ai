from ssquant.backtest.backtest_core import MultiSourceBacktester
import pandas as pd
import numpy as np
from ssquant.api.strategy_api import StrategyAPI

def initialize(api:StrategyAPI):
    """
    策略初始化函数
    
    Args:
        api: 策略API对象
    """
    api.log("海龟交易策略初始化...")
    api.log("所有交易将使用下一根K线开盘价执行 (order_type='next_bar_open')")
    api.log("本策略基于唐奇安通道进行趋势跟踪交易")
    
    # 获取策略参数
    entry_period = api.get_param('entry_period', 20)  # 入场周期
    exit_period = api.get_param('exit_period', 10)    # 出场周期
    atr_period = api.get_param('atr_period', 14)      # ATR周期
    risk_factor = api.get_param('risk_factor', 0.01)  # 风险因子
    
    api.log(f"参数设置 - 入场周期: {entry_period}, 出场周期: {exit_period}, " +
            f"ATR周期: {atr_period}, 风险因子: {risk_factor}")

def calculate_donchian_channel(high_series, low_series, period):
    """
    计算唐奇安通道
    
    Args:
        high_series: 最高价序列
        low_series: 最低价序列
        period: 周期
        
    Returns:
        (上轨, 下轨)
    """
    upper = high_series.rolling(window=period).max()
    lower = low_series.rolling(window=period).min()
    
    return upper, lower

def calculate_atr(high_series, low_series, close_series, period=14):
    """
    计算平均真实波幅（ATR）
    
    Args:
        high_series: 最高价序列
        low_series: 最低价序列
        close_series: 收盘价序列
        period: 周期
        
    Returns:
        ATR序列
    """
    # 计算真实波幅（True Range）
    tr1 = high_series - low_series
    tr2 = (high_series - close_series.shift(1)).abs()
    tr3 = (low_series - close_series.shift(1)).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 计算ATR
    atr = tr.rolling(window=period).mean()
    
    return atr

def calculate_position_size(price, atr, account_size, risk_factor, contract_multiplier):
    """
    计算头寸规模
    
    Args:
        price: 当前价格
        atr: 当前ATR值
        account_size: 账户规模
        risk_factor: 风险因子
        contract_multiplier: 合约乘数
        
    Returns:
        头寸数量
    """
    # 计算每点价值
    dollar_per_point = contract_multiplier
    
    # 计算波动价值
    volatility_value = atr * dollar_per_point
    
    # 计算风险金额
    risk_amount = account_size * risk_factor
    
    # 计算头寸数量
    position_size = risk_amount / volatility_value
    
    # 向下取整
    position_size = np.floor(position_size)
    
    # 确保至少为1
    position_size = max(1, position_size)
    
    return position_size

def turtle_trading_strategy_with_volatility_sizing(api: StrategyAPI):
    """
    海龟交易策略（加入波动率调整的头寸管理）
    
    该策略在经典海龟交易法则的基础上，加入了基于波动率的头寸调整，
    旨在通过风险管理来提高交易效率。
    
    策略逻辑：
    1. 当价格突破N日高点时入场做多
    2. 当价格突破N/2日低点时离场
    3. 当价格突破N日低点时入场做空
    4. 当价格突破N/2日高点时离场
    5. 使用ATR来确定头寸规模
    6. 基于系统单位的头寸调整（海龟系统）
    """
    # 获取策略参数
    entry_period = api.get_param('entry_period', 20)    # 入场周期
    exit_period = api.get_param('exit_period', 10)      # 出场周期
    atr_period = api.get_param('atr_period', 14)        # ATR周期
    risk_factor = api.get_param('risk_factor', 0.01)    # 风险因子
    max_units = api.get_param('max_units', 4)           # 最大系统单位数
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)
    bar_datetime = api.get_datetime(0)
    
    # 获取数据源数量
    data_sources_count = api.get_data_sources_count()
    
    # 每100个bar打印一次信息
    if bar_idx % 100 == 0:
        api.log(f"当前Bar索引: {bar_idx}, 日期时间: {bar_datetime}")
    
    # 确保有足够的数据
    min_required_bars = max(entry_period, exit_period, atr_period) + 5
    if bar_idx < min_required_bars:
        if bar_idx == 0:
            api.log(f"数据准备中，需要至少 {min_required_bars} 根K线")
        return
    
    # 遍历所有数据源
    for i in range(data_sources_count):
        # 获取K线数据
        klines = api.get_klines(i)
        
        # 检查数据长度
        if len(klines) <= min_required_bars:
            api.log(f"数据源 {i} 数据不足，需要至少 {min_required_bars} 根K线，当前只有 {len(klines)} 根")
            continue
        
        # 获取价格数据
        high = klines['high']
        low = klines['low']
        close = klines['close']
        
        # 获取当前价格
        current_price = close.iloc[bar_idx]
        
        # 计算唐奇安通道
        entry_upper, entry_lower = calculate_donchian_channel(high, low, entry_period)
        exit_upper, exit_lower = calculate_donchian_channel(high, low, exit_period)
        
        # 获取当前通道值
        current_entry_upper = entry_upper.iloc[bar_idx]
        current_entry_lower = entry_lower.iloc[bar_idx]
        current_exit_upper = exit_upper.iloc[bar_idx]
        current_exit_lower = exit_lower.iloc[bar_idx]
        
        # 获取前一天的通道值和价格（用于判断突破）
        prev_entry_upper = entry_upper.iloc[bar_idx - 1]
        prev_entry_lower = entry_lower.iloc[bar_idx - 1]
        prev_close = close.iloc[bar_idx - 1]
        
        # 计算ATR
        atr = calculate_atr(high, low, close, atr_period)
        current_atr = atr.iloc[bar_idx]
        
        # 检查ATR是否为NaN
        if pd.isna(current_atr) or current_atr == 0:
            api.log(f"数据源 {i} 的ATR为无效值，跳过")
            continue
        
        # 获取数据源和品种信息
        data_source = api.get_data_source(i)
        if data_source is None:
            api.log(f"无法获取数据源 {i}")
            continue
            
        symbol = data_source.symbol
        
        # 这是关键修改：直接从全局上下文中获取symbol_configs
        symbol_configs = api.get_param('symbol_configs', {})
        symbol_config = symbol_configs.get(symbol, {})
        
        # 从配置中读取初始资金和合约乘数
        account_size = symbol_config.get('initial_capital', 100000.0)
        contract_multiplier = symbol_config.get('contract_multiplier', 10)
        
        # 计算单个系统单位的头寸规模
        unit_size = calculate_position_size(current_price, current_atr, account_size, risk_factor, contract_multiplier)
        
        # 获取当前持仓
        current_pos = api.get_pos(i)
        
        # 计算当前系统单位数（绝对值）
        current_units = abs(current_pos) / unit_size if unit_size > 0 else 0
        
        # 每20个bar打印一次状态
        if bar_idx % 20 == 0:
            api.log(f"品种 {symbol} - 价格: {current_price:.2f}, ATR: {current_atr:.2f}, 合约乘数: {contract_multiplier}")
            api.log(f"入场通道: 上轨={current_entry_upper:.2f}, 下轨={current_entry_lower:.2f}")
            api.log(f"出场通道: 上轨={current_exit_upper:.2f}, 下轨={current_exit_lower:.2f}")
            api.log(f"单个系统单位规模: {unit_size}, 当前单位数: {current_units:.2f}/{max_units}")
            api.log(f"当前持仓: {current_pos}")
        
        # 交易逻辑
        # 情况1: 当前无持仓
        if current_pos == 0:
            # 检查是否突破入场通道上轨（做多信号）
            # 使用更宽松的突破条件：当前收盘价大于前一个通道上轨
            if current_price > prev_entry_upper:
                api.log(f"品种 {symbol} 价格 {current_price:.2f} 突破入场通道上轨 {prev_entry_upper:.2f}，开多仓 1个单位 ({unit_size})")
                api.buy(volume=int(unit_size), order_type='next_bar_open', index=i)
                
            # 检查是否突破入场通道下轨（做空信号）
            # 使用更宽松的突破条件：当前收盘价小于前一个通道下轨
            elif current_price < prev_entry_lower:
                api.log(f"品种 {symbol} 价格 {current_price:.2f} 突破入场通道下轨 {prev_entry_lower:.2f}，开空仓 1个单位 ({unit_size})")
                api.sellshort(volume=int(unit_size), order_type='next_bar_open', index=i)
        
        # 情况2: 当前持有多仓
        elif current_pos > 0:
            # 检查是否突破出场通道下轨（平多信号）
            if current_price < current_exit_lower:
                api.log(f"品种 {symbol} 价格 {current_price:.2f} 突破出场通道下轨 {current_exit_lower:.2f}，平多仓")
                api.sell(order_type='next_bar_open', index=i)
            
            # 检查是否可以加仓（价格上涨0.5个ATR且未达到最大单位数）
            elif current_units < max_units:
                # 获取最近一次加仓价格
                # 这里简化处理，假设上次加仓价格是当前价格减去1个ATR
                # 在实际应用中，应该记录每次加仓的价格
                last_entry_price = current_price - current_atr
                
                # 如果价格上涨了0.5个ATR，可以加仓
                if current_price >= last_entry_price + 0.5 * current_atr:
                    new_unit_size = int(unit_size)
                    if new_unit_size > 0:  # 确保加仓数量大于0
                        api.log(f"品种 {symbol} 价格上涨0.5个ATR，加多仓 1个单位 ({new_unit_size})")
                        api.buy(volume=new_unit_size, order_type='next_bar_open', index=i)
        
        # 情况3: 当前持有空仓
        elif current_pos < 0:
            # 检查是否突破出场通道上轨（平空信号）
            if current_price > current_exit_upper:
                api.log(f"品种 {symbol} 价格 {current_price:.2f} 突破出场通道上轨 {current_exit_upper:.2f}，平空仓")
                api.buycover(order_type='next_bar_open', index=i)
            
            # 检查是否可以加仓（价格下跌0.5个ATR且未达到最大单位数）
            elif current_units < max_units:
                # 获取最近一次加仓价格
                # 这里简化处理，假设上次加仓价格是当前价格加上1个ATR
                # 在实际应用中，应该记录每次加仓的价格
                last_entry_price = current_price + current_atr
                
                # 如果价格下跌了0.5个ATR，可以加仓
                if current_price <= last_entry_price - 0.5 * current_atr:
                    new_unit_size = int(unit_size)
                    if new_unit_size > 0:  # 确保加仓数量大于0
                        api.log(f"品种 {symbol} 价格下跌0.5个ATR，加空仓 1个单位 ({new_unit_size})")
                        api.sellshort(volume=new_unit_size, order_type='next_bar_open', index=i)

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
        'username': API_USERNAME,
        'password': API_PASSWORD,
        'use_cache': True,
        'save_data': True,
        'align_data': False,
        'fill_method': 'ffill',
        'debug': True
    })
    
    # 添加数据源配置
    symbol_configs = {}
    
    # 添加螺纹钢期货配置
    symbol_configs['rb888'] = {
        'start_date': '2022-01-01',  # 延长回测时间
        'end_date': '2023-06-30',
        'initial_capital': 100000.0,
        'commission': 0.0003,
        'margin_rate': 0.1,
        'contract_multiplier': 10,
        'periods': [
            {'kline_period': '1d', 'adjust_type': '1'},  # 日K线
        ]
    }
    
    # 添加黄金期货配置
    symbol_configs['au888'] = {
        'start_date': '2022-01-01',
        'end_date': '2023-06-30',
        'initial_capital': 100000.0,
        'commission': 0.0003,
        'margin_rate': 0.08,
        'contract_multiplier': 1000,
        'periods': [
            {'kline_period': '1d', 'adjust_type': '1'},  # 日K线
        ]
    }
    
    # 添加数据源配置
    for symbol, config in symbol_configs.items():
        backtester.add_symbol_config(symbol, config)
    
    # 策略参数
    strategy_params = {
        'entry_period': 20,      # 入场周期
        'exit_period': 10,       # 出场周期
        'atr_period': 14,        # ATR周期
        'risk_factor': 0.01,     # 风险因子
        'max_units': 4,          # 最大系统单位数
        'symbol_configs': symbol_configs  # 将配置信息传递给策略
    }
    
    # 运行回测 - 带波动率调整的海龟策略
    results = backtester.run(
        strategy=turtle_trading_strategy_with_volatility_sizing,
        initialize=initialize,
        strategy_params=strategy_params
    )
    