from ssquant.backtest.backtest_core import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI

def initialize(api: StrategyAPI):
    """
    策略初始化函数
    """
    api.log("tick级盘口+成交量策略初始化")
    vol_threshold = api.get_param('vol_threshold', 50)
    api.log(f"参数设置 - 成交量阈值: {vol_threshold}")

def tick_strategy(api: StrategyAPI):
    """
    tick级盘口+成交量策略
    """
    vol_threshold = api.get_param('vol_threshold', 100)  # 用传入参数
    ticks = api.get_ticks(window=2)
    if len(ticks) < 2:
        return

    last_tick = ticks.iloc[-2]
    curr_tick = ticks.iloc[-1]
    delta_vol = curr_tick['volume'] - last_tick['volume']
    api.log(f"DEBUG: delta_vol={delta_vol}, bid1变化={curr_tick['bid1'] - last_tick['bid1']}, ask1变化={curr_tick['ask1'] - last_tick['ask1']}")

    if (curr_tick['bid1'] > last_tick['bid1'] and delta_vol >= vol_threshold):
        api.log("触发做多条件")
        if api.get_pos() <= 0:
            api.close_all(reason="盘口+量做多")
            api.buy(volume=1, reason="盘口+量做多")
    elif (curr_tick['ask1'] < last_tick['ask1'] and delta_vol >= vol_threshold):
        api.log("触发做空条件")
        if api.get_pos() >= 0:
            api.close_all(reason="盘口+量做空")
            api.sellshort(volume=1, reason="盘口+量做空")

    # 记录当前tick信息
    api.log(f"时间: {curr_tick['datetime']}, 买一: {curr_tick['bid1']}, 卖一: {curr_tick['ask1']}, 成交量: {curr_tick['volume']}")

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

    # 添加tick数据源（本地CSV）- 单文件方式
    """
    backtester.add_symbol_config(
        symbol='rb888',
        config={
            'file_path': 'data_cache/tick_data.csv',   # 本地tick数据,使用'file_path'字段会自动屏蔽API数据接口的调用。
            'start_date': '2023-01-01',       # start_date现已生效，用于筛选数据的日期范围
            'end_date': '2023-12-31',         # end_date现已生效，用于筛选数据的日期范围
            'initial_capital': 100000,
            'commission': 0.0001,
            'margin_rate': 0.1,
            'contract_multiplier': 10,
            'slippage': 0,
            'periods': [
                {'kline_period': 'tick', 'adjust_type': '0'},  # 指定tick数据
            ]
        }
    )
    """

    # 添加tick数据源（本地CSV）- 多文件列表方式
    backtester.add_symbol_config(
        symbol='rb888',
        config={
            'file_path': [
                'data_cache/tick_data_part1.csv',   # 第一个时间段数据
                'data_cache/tick_data_part2.csv',   # 第二个时间段数据
                'data_cache/tick_data_part3.csv',   # 第三个时间段数据
            ],   # 本地tick数据列表,将按顺序加载并合并
            'start_date': '2023-01-01',       # start_date现已生效，用于筛选数据的日期范围
            'end_date': '2023-01-4',         # end_date现已生效，用于筛选数据的日期范围
            'initial_capital': 100000,
            'commission': 0.0001,
            'margin_rate': 0.1,
            'contract_multiplier': 10,
            'slippage': 0,
            'periods': [
                {'kline_period': 'tick', 'adjust_type': '0'},  # 指定tick数据
            ]
        }
    )

    # 策略参数
    strategy_params = {
        'vol_threshold': 50,
    }

    # 运行回测
    results = backtester.run(
        strategy=tick_strategy,
        initialize=initialize,
        strategy_params=strategy_params,
    )
