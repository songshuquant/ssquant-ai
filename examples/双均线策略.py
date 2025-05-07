"""
双均线交易策略 - 多数据源版本

使用移动平均线交叉判断交易信号:
- 短期均线上穿长期均线: 买入信号
- 短期均线下穿长期均线: 卖出信号

该策略支持多个品种同时交易
"""

# 导入回测器
from ssquant.backtest.backtest_core import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI


def initialize(api: StrategyAPI):
    """
    策略初始化函数
    
    Args:
        api: 策略API对象
    """
    api.log("双均线交叉策略初始化")
    fast_ma = api.get_param('fast_ma', 5)
    slow_ma = api.get_param('slow_ma', 10)
    api.log(f"参数设置 - 快线周期: {fast_ma}, 慢线周期: {slow_ma}")

def ma_cross_strategy(api: StrategyAPI):
    """
    双均线交叉策略
    
    Args:
        api: 策略API对象
    """
    # 获取参数
    fast_ma = api.get_param('fast_ma', 5)
    slow_ma = api.get_param('slow_ma', 10)
    
    # 获取当前索引
    current_idx = api.get_idx()
    if current_idx < slow_ma:
        return
    
    # 获取收盘价和计算均线
    close = api.get_close()
    kine= api.get_klines()
    fast_ma_values = close.rolling(fast_ma).mean()
    slow_ma_values = close.rolling(slow_ma).mean()
    
    # 获取当前和前一个时刻的均线值
    current_fast = fast_ma_values.iloc[current_idx]
    prev_fast = fast_ma_values.iloc[current_idx - 1]
    current_slow = slow_ma_values.iloc[current_idx]
    prev_slow = slow_ma_values.iloc[current_idx - 1]
    
    # 获取当前持仓
    current_pos = api.get_pos()
    
    # 均线金叉：快线上穿慢线
    if prev_fast <= prev_slow and current_fast > current_slow:
        if current_pos <= 0:
            # 如果没有持仓或者空头持仓，买入开仓
            api.buytocover(order_type='next_bar_open')
            api.buy(volume=1, order_type='next_bar_open')
            api.log(f"均线金叉：快线({current_fast:.2f})上穿慢线({current_slow:.2f})，买入")
    
    # 均线死叉：快线下穿慢线
    elif prev_fast >= prev_slow and current_fast < current_slow:
        if current_pos >= 0:
            # 如果没有持仓或者多头持仓，卖出开仓
            api.sell(order_type='next_bar_open')
            api.sellshort(volume=1, order_type='next_bar_open')
            api.log(f"均线死叉：快线({current_fast:.2f})下穿慢线({current_slow:.2f})，卖出")
    
    # 记录当前价格和日期时间
    current_price = api.get_price()
    current_datetime = api.get_datetime()
    api.log(f"当前时间: {current_datetime}, 价格: {current_price:.2f}, 快线: {current_fast:.2f}, 慢线: {current_slow:.2f}, 持仓: {current_pos}")


# 多数据源回测配置
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
        'align_data': False,            # 改为False，避免数据对齐问题
        'fill_method': 'ffill',         # 填充方法
        'debug': True                   # 启用调试模式-日志输出
    })
     
    # 添加单一数据源
    # 焦炭主力 - 日线
    backtester.add_symbol_config(
        symbol='rb888',
        config={
            'start_date': '2021-01-01',  # 缩短回测时间，减少数据量
            'end_date': '2025-04-16',    # 使用历史数据，避免未来数据
            'initial_capital': 100000,
            'commission': 0.0001,
            'margin_rate': 0.1,
            'contract_multiplier': 100,
            'slippage': 0,
            'periods': [
                {'kline_period': '1h', 'adjust_type': '1'},  # 只用日K线
            ]  
        }
    )
    # 设置策略参数
    strategy_params = {
        'fast_ma': 5,
        'slow_ma': 20,
    }
    

    # 运行回测
    results = backtester.run(
        strategy=ma_cross_strategy,
        initialize=initialize,
        strategy_params=strategy_params,
    )
    