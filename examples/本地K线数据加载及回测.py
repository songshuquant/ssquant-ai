from ssquant.backtest.backtest_core import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI
from 双均线策略 import ma_cross_strategy, initialize

if __name__ == "__main__":
    # 创建多数据源回测器
    backtester = MultiSourceBacktester()

    # 设置基础配置（本地数据无需API认证）
    backtester.set_base_config({
        'use_cache': False,      # 本地数据无需API缓存
        'save_data': False,      # 本地数据无需API保存
        'align_data': False,     # 单品种可不对齐
        'debug': True
    })

    # 添加本地CSV数据源 - 单文件方式
    """
    backtester.add_symbol_config(
        symbol='au888',
        config={
            'file_path': 'data_cache/au888_1d.csv',  # 本地路径，使用'file_path'字段会自动屏蔽API数据接口的调用。
            'start_date': '2023-01-01',  # 缩短回测时间，减少数据量
            'end_date': '2024-03-31',    # 使用历史数据，避免未来数据
            'initial_capital': 100000,
            'commission': 0.0001,
            'margin_rate': 0.1,
            'contract_multiplier': 100,
            'slippage': 0,
            'periods': [{'kline_period': '1d', 'adjust_type': '1'}],
        }
    )
    """
    
    # 添加本地CSV数据源 - 多文件方式（按年份分割的数据）
    backtester.add_symbol_config(
        symbol='au888',
        config={
            'file_path': [
                'data_cache/au888_2023.csv',  # 2023年数据
                'data_cache/au888_2024_q1.csv',  # 2024年第一季度数据
            ],  # 多个文件会按顺序加载并合并
            'start_date': '2023-01-01',  # 缩短回测时间
            'end_date': '2024-1-31',    # 使用历史数据
            'initial_capital': 100000,
            'commission': 0.0001,
            'margin_rate': 0.1,
            'contract_multiplier': 100,
            'slippage': 0,
            'periods': [{'kline_period': '1d', 'adjust_type': '1'}],
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


