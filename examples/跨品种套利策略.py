from ssquant.backtest.backtest_core import MultiSourceBacktester
import pandas as pd
import numpy as np

from ssquant.api.strategy_api import StrategyAPI
import statsmodels.api as sm

def initialize(api: StrategyAPI):
    """
    策略初始化函数
    此函数用于初始化策略并输出日志信息。
    
    Args:
        api: 策略API对象，用于访问策略参数和日志功能
    """
    api.log("跨品种套利策略初始化...")  # 输出初始化日志
    api.log("本策略利用焦炭(J)和焦煤(JM)之间的价差关系进行套利")  # 描述策略的核心逻辑

def calculate_spread(price1, price2, hedge_ratio=None):
    """
    计算两个价格序列之间的价差
    如果提供hedge_ratio，则使用该比率调整价差计算；否则直接相减。
    
    Args:
        price1: 第一个品种的价格序列（例如焦炭）
        price2: 第二个品种的价格序列（例如焦煤）
        hedge_ratio: 套期保值比率，如果为None则不使用
    
    Returns:
        价差序列，表示两个价格序列的差值
    """
    if hedge_ratio is None:
        return price1 - price2  # 如果没有hedge_ratio，直接计算差值
    else:
        return price1 - price2 * hedge_ratio  # 使用hedge_ratio调整后计算价差

def calculate_hedge_ratio(price1, price2, window=60, current_idx=None):
    """
    计算套期保值比率（基于OLS回归）
    使用指定窗口的历史数据进行线性回归，获取动态对冲比率。
    
    Args:
        price1: 第一个品种的价格序列
        price2: 第二个品种的价格序列
        window: 滚动窗口大小，用于选取历史数据
        current_idx: 当前位置索引，如果为None则使用序列末尾
    
    Returns:
        当前位置的对冲比率
    """
    if current_idx is None:
        current_idx = len(price1) - 1  # 默认使用序列末尾作为当前索引
    if current_idx < window - 1:
        return np.nan  # 如果数据不足，返回NaN
    start_idx = max(0, current_idx - window + 1)  # 计算窗口起始索引
    y = price1.iloc[start_idx:current_idx+1]  # 选取y变量数据
    X = price2.iloc[start_idx:current_idx+1]  # 选取X变量数据
    X = sm.add_constant(X)  # 添加常数项以包含截距
    model = sm.OLS(y, X)  # 创建OLS模型
    results = model.fit()  # 拟合模型
    hedge_ratio = results.params[1]  # 获取斜率系数作为对冲比率
    return hedge_ratio

def calculate_zscore(spread, window=20):
    """
    计算价差的Z分数
    Z分数用于衡量价差偏离均值的程度，基于移动窗口计算。
    
    Args:
        spread: 价差序列
        window: 窗口大小，用于计算移动均值和标准差
    
    Returns:
        Z分数序列
    """
    mean = spread.rolling(window=window).mean()  # 计算移动平均值
    std = spread.rolling(window=window).std()  # 计算移动标准差
    zscore = (spread - mean) / std  # 计算Z分数
    return zscore

def pairs_trading_strategy(api: StrategyAPI):
    """
    跨品种套利策略主函数
    基于价差的Z分数进行交易决策，包括开仓和平仓逻辑。
    """
    if not api.require_data_sources(2):  # 检查是否至少有2个数据源
        return  # 如果不足，返回
    
    min_samples = api.get_param('min_samples', 200)  # 获取最小样本数参数
    zscore_threshold = api.get_param('zscore_threshold', 2.0)  # 获取Z分数阈值
    rolling_window = api.get_param('rolling_window', 20)  # 获取滚动窗口大小
    hedge_ratio_window = api.get_param('hedge_ratio_window', 30)  # 获取对冲比率窗口
    use_dynamic_hedge_ratio = api.get_param('use_dynamic_hedge_ratio', True)  # 是否使用动态对冲比率
    
    bar_idx = api.get_idx(0)  # 获取当前K线索引
    j_klines = api.get_klines(0)  # 获取焦炭K线数据
    jm_klines = api.get_klines(1)  # 获取焦煤K线数据
    
    if len(j_klines) < min_samples or len(jm_klines) < min_samples:  # 检查数据量是否足够
        return  # 如果不足，返回
    
    j_close = j_klines['close']  # 提取焦炭收盘价
    jm_close = jm_klines['close']  # 提取焦煤收盘价
    
    hedge_ratio = None
    if use_dynamic_hedge_ratio:  # 如果使用动态对冲比率
        if bar_idx >= hedge_ratio_window:
            hedge_ratio = calculate_hedge_ratio(j_close, jm_close, window=hedge_ratio_window, current_idx=bar_idx)
        if pd.isna(hedge_ratio):  # 如果计算结果为NaN
            hedge_ratio = 1.5  # 使用默认值
    else:
        hedge_ratio = 1.5  # 使用静态对冲比率
    
    spread = calculate_spread(j_close, jm_close, hedge_ratio)  # 计算价差
    if bar_idx < rolling_window:  # 如果数据不足以计算Z分数
        return
    
    zscore = calculate_zscore(spread, window=rolling_window)  # 计算Z分数序列
    current_zscore = zscore.iloc[bar_idx]  # 获取当前Z分数
    if pd.isna(current_zscore):  # 如果Z分数为NaN
        return
    
    j_pos = api.get_pos(0)  # 获取焦炭持仓
    jm_pos = api.get_pos(1)  # 获取焦煤持仓
    j_unit = 1  # 焦炭交易单位
    jm_unit = max(1, round(j_unit * hedge_ratio))  # 计算焦煤交易单位
    
    if j_pos == 0 and jm_pos == 0:  # 无持仓情况
        if current_zscore > zscore_threshold:  # Z分数过高，做空价差
            api.sellshort(volume=j_unit, order_type='next_bar_open', index=0)
            api.buy(volume=jm_unit, order_type='next_bar_open', index=1)
        elif current_zscore < -zscore_threshold:  # Z分数过低，做多价差
            api.buy(volume=j_unit, order_type='next_bar_open', index=0)
            api.sellshort(volume=jm_unit, order_type='next_bar_open', index=1)
    elif j_pos < 0 and jm_pos > 0:  # 持有空焦炭多焦煤
        if current_zscore < 0.5:  # Z分数回归，平仓
            api.buycover(order_type='next_bar_open', index=0)
            api.sell(order_type='next_bar_open', index=1)
    elif j_pos > 0 and jm_pos < 0:  # 持有多焦炭空焦煤
        if current_zscore > -0.5:  # Z分数回归，平仓
            api.sell(order_type='next_bar_open', index=0)
            api.buycover(order_type='next_bar_open', index=1)

if __name__ == "__main__":
    try:
        from ssquant.config.auth_config import get_api_auth
        API_USERNAME, API_PASSWORD = get_api_auth()
    except ImportError:
        print("警告：未找到 auth_config.py 文件，请在下方填写您的认证信息：API_USERNAME和API_PASSWORD")
        API_USERNAME = ""
        API_PASSWORD = ""
    
    backtester = MultiSourceBacktester()
    backtester.set_base_config({
        'username': API_USERNAME,
        'password': API_PASSWORD,
        'use_cache': True,  # 使用缓存数据以提高回测效率
        'save_data': True,  # 保存数据以便后续分析
        'align_data': True,  # 确保数据源时间戳对齐
        'fill_method': 'ffill',  # 使用前向填充处理缺失数据
        'debug': True  # 关闭调试模式，减少输出日志
    })
    
    backtester.add_symbol_config(
        symbol='j888', 
        config={
            'start_date': '2024-01-01',  # 回测起始日期
            'end_date': '2025-02-28',    # 回测结束日期
            'initial_capital': 100000.0, # 初始资金金额
            'commission': 0.0003,        # 交易手续费率
            'margin_rate': 0.1,          # 保证金比率
            'contract_multiplier': 100,  # 合约乘数
            'periods': [{'kline_period': '15m', 'adjust_type': '1'}]  # K线周期设置
    })
    
    backtester.add_symbol_config(
        symbol='jm888', 
        config={
            'start_date': '2024-01-01',
            'end_date': '2025-02-28',
            'initial_capital': 100000.0,
            'commission': 0.0003,
            'margin_rate': 0.1,
            'contract_multiplier': 60,
            'periods': [{'kline_period': '15m', 'adjust_type': '1'}]
    })
    
    strategy_params = {
        'min_samples': 50,
        'zscore_threshold': 1.5,
        'rolling_window': 20,
        'hedge_ratio_window': 30,
        'use_dynamic_hedge_ratio': True
    }
    
    results = backtester.run(
        strategy=pairs_trading_strategy,
        initialize=initialize,
        strategy_params=strategy_params
    )
