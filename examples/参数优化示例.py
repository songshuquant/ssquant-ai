"""
参数优化示例 (优化版)

使用数据预加载功能优化参数，大幅提高效率
演示如何优化海龟交易策略的入场和离场周期参数
"""

from ssquant.backtest.backtest_core import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI
from 海龟交易策略 import turtle_trading_strategy_with_volatility_sizing, initialize
import time

if __name__ == "__main__":
    # 记录开始时间
    start_time = time.time()
    
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
        'debug': False,                 # 关闭调试模式提高速度
        'skip_module_check': True       # 跳过模块检查，提高速度
    })
    
    # 添加单一数据源
    backtester.add_symbol_config(
        symbol='rb888',
        config={
            'start_date': '2023-01-01',     # 回测开始日期
            'end_date': '2024-01-31',       # 回测结束日期（缩短回测周期，便于调试）
            'initial_capital': 100000.0,    # 初始资金，单位：元
            'commission': 0.0003,           # 手续费率，例如：0.0003表示万分之3
            'margin_rate': 0.1,             # 保证金率，例如：0.1表示10%
            'contract_multiplier': 10,      # 合约乘数，例如：螺纹钢期货每点10元
            'periods': [
                {'kline_period': '1d', 'adjust_type': '1'},  # 使用日线数据
            ]
        }
    )
    
    print("\n===== 参数优化示例 (优化版) =====")

    # 预加载数据，避免在每次参数评估时重复加载
    print("\n=== 数据预加载开始 ===")
    preload_start_time = time.time()
    backtester.preload_data()
    preload_end_time = time.time()
    preload_time = preload_end_time - preload_start_time
    print(f"数据预加载用时: {preload_time:.2f}秒")
    print("=== 数据预加载完成 ===\n")
    
    # 定义参数网格
    param_grid = {
        'entry_period': list(range(10, 100, 5)),    # 入场周期参数范围
        'exit_period': list(range(5, 100, 5)),      # 离场周期参数范围
    }
    
    # 计算参数组合数量
    total_combinations = 1
    for param_values in param_grid.values():
        total_combinations *= len(param_values)
    print(f"参数网格共有 {total_combinations} 种组合")
    
    # 1. 网格搜索优化
    print("\n=== 开始网格搜索优化 ===")
    grid_start_time = time.time()
    best_params_grid, best_results_grid = backtester.optimize_parameters(
        strategy=turtle_trading_strategy_with_volatility_sizing,
        initialize=initialize,
        param_grid=param_grid,
        method='grid',
        optimization_metric='sharpe_ratio',   # 优化夏普比率
        higher_is_better=True,                # 夏普比率越高越好
        parallel=True,                        # 使用并行计算
        n_jobs=-1,                            # -1是使用所有可用CPU核心
        strategy_name="Turtle_Strategy_Grid", # 策略名称
        skip_final_report=False,               # 跳过最终完整报告
        reuse_data=True                       # 复用预加载的数据，大幅提高效率
    )
    grid_end_time = time.time()
    grid_time = grid_end_time - grid_start_time
    
    if best_params_grid:
        print(f"\n最优参数 (网格搜索): {best_params_grid}")
        print(f"最优夏普比率: {best_results_grid['performance']['sharpe_ratio']:.4f}")
        print(f"总收益率: {best_results_grid['performance']['total_return']:.2f}%")
        print(f"最大回撤: {best_results_grid['performance']['max_drawdown']:.2f}%")
        print(f"胜率: {best_results_grid['performance'].get('win_rate', 0):.2f}%")
    
    # 2. 随机搜索优化
    print("\n=== 开始随机搜索优化 ===")
    random_start_time = time.time()
    best_params_random, best_results_random = backtester.optimize_parameters(
        strategy=turtle_trading_strategy_with_volatility_sizing,
        initialize=initialize,
        param_grid=param_grid,
        method='random',
        n_iter=10,                               # 随机搜索迭代次数
        optimization_metric='sharpe_ratio',      # 优化夏普比率
        higher_is_better=True,                   # 夏普比率越高越好
        parallel=True,                           # 使用并行计算
        n_jobs=-1,                               # -1是使用所有可用CPU核心
        strategy_name="Turtle_Strategy_Random",  # 策略名称
        skip_final_report=True,                  # 跳过最终完整报告
        reuse_data=True                          # 复用预加载的数据，大幅提高效率
    )
    random_end_time = time.time()
    random_time = random_end_time - random_start_time
    
    if best_params_random:
        print(f"\n最优参数 (随机搜索): {best_params_random}")
        print(f"最优夏普比率: {best_results_random['performance']['sharpe_ratio']:.4f}")
        print(f"总收益率: {best_results_random['performance']['total_return']:.2f}%")
        print(f"最大回撤: {best_results_random['performance']['max_drawdown']:.2f}%")
        print(f"胜率: {best_results_random['performance'].get('win_rate', 0):.2f}%")
    
    # 3. 贝叶斯优化
    print("\n=== 开始贝叶斯优化 ===")
    bayesian_start_time = time.time()
    best_params_bayes, best_results_bayes = backtester.optimize_parameters(
        strategy=turtle_trading_strategy_with_volatility_sizing,
        initialize=initialize,
        param_grid=param_grid,
        method='bayesian',
        n_iter=10,                               # 贝叶斯优化迭代次数
        optimization_metric='sharpe_ratio',      # 优化夏普比率
        higher_is_better=True,                   # 夏普比率越高越好
        strategy_name="Turtle_Strategy_Bayesian", # 策略名称
        skip_final_report=True,                  # 跳过最终完整报告
        reuse_data=True                          # 复用预加载的数据，大幅提高效率
    )
    bayesian_end_time = time.time()
    bayesian_time = bayesian_end_time - bayesian_start_time
    
    if best_params_bayes:
        print(f"\n最优参数 (贝叶斯优化): {best_params_bayes}")
        print(f"最优夏普比率: {best_results_bayes['performance']['sharpe_ratio']:.4f}")
        print(f"总收益率: {best_results_bayes['performance']['total_return']:.2f}%")
        print(f"最大回撤: {best_results_bayes['performance']['max_drawdown']:.2f}%")
        print(f"胜率: {best_results_bayes['performance'].get('win_rate', 0):.2f}%")
    
    # 记录结束时间
    end_time = time.time()
    total_time = end_time - start_time
    
    # 输出性能统计信息
    print("\n===== 性能统计 =====")
    print(f"数据预加载用时: {preload_time:.2f}秒")
    print(f"网格搜索用时: {grid_time:.2f}秒")
    print(f"随机搜索用时: {random_time:.2f}秒")
    print(f"贝叶斯优化用时: {bayesian_time:.2f}秒")
    print(f"总用时: {total_time:.2f}秒")
    print(f"平均每个参数组合评估用时 (网格搜索): {grid_time / total_combinations:.4f}秒")
    
    print("\n=============================================")
    print("=" * 45)
    print(f"优化完成！所有结果和图表已保存在 optimization/[策略名称]_[时间戳] 目录")
    print("参数组合详细结果可以在Excel文件中查看")
    print("=" * 45)
    print("=============================================") 