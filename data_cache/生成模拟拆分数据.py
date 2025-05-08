import pandas as pd
import numpy as np
import os

# 创建数据目录
os.makedirs('data_cache', exist_ok=True)

# 1. 生成2023年的模拟数据
def generate_2023_data():
    """生成2023年完整年度的K线数据"""
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    n = len(dates)
    
    # 构造价格走势，使用随机游走生成更真实的数据
    close = np.zeros(n)
    close[0] = 450.0  # 起始价格
    
    # 使用随机游走模拟价格走势
    volatility = 0.015  # 每日波动率
    returns = np.random.normal(0, volatility, n)
    for i in range(1, n):
        close[i] = close[i-1] * (1 + returns[i])
    
    # 确保价格在合理范围内
    close = np.clip(close, 400, 500)
    
    # 生成其他价格数据
    spread = np.random.uniform(5, 15, n)  # 日内价格波动
    open_price = close - np.random.uniform(-1, 1, n) * spread/2
    high = np.maximum(close, open_price) + np.random.uniform(0, 1, n) * spread/2
    low = np.minimum(close, open_price) - np.random.uniform(0, 1, n) * spread/2
    
    # 生成成交量数据，交易日成交量较大
    volume = np.random.randint(1000, 10000, n)
    # 周末成交量减少
    for i, date in enumerate(dates):
        if date.weekday() >= 5:  # 周六日
            volume[i] = volume[i] // 3
    
    # 创建DataFrame
    df = pd.DataFrame({
        'datetime': dates,
        'open': open_price.round(2),
        'high': high.round(2),
        'low': low.round(2),
        'close': close.round(2),
        'volume': volume
    })
    
    # 保证high/low合理性
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    return df

# 2. 生成2024年Q1的模拟数据
def generate_2024_q1_data(last_day_price):
    """生成2024年第一季度的K线数据，确保与2023年数据平滑衔接"""
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
    n = len(dates)
    
    # 构造价格走势，延续2023年的最后一个价格
    close = np.zeros(n)
    close[0] = last_day_price  # 起始价格使用2023年最后一天的收盘价
    
    # 使用随机游走模拟价格走势，给予一定的上涨趋势
    trend = 0.0003  # 微小的上涨趋势
    volatility = 0.012  # 每日波动率
    returns = np.random.normal(trend, volatility, n)
    for i in range(1, n):
        close[i] = close[i-1] * (1 + returns[i])
    
    # 确保价格在合理范围内
    close = np.clip(close, 410, 520)
    
    # 生成其他价格数据
    spread = np.random.uniform(5, 15, n)  # 日内价格波动
    open_price = close - np.random.uniform(-1, 1, n) * spread/2
    high = np.maximum(close, open_price) + np.random.uniform(0, 1, n) * spread/2
    low = np.minimum(close, open_price) - np.random.uniform(0, 1, n) * spread/2
    
    # 生成成交量数据
    volume = np.random.randint(1000, 10000, n)
    # 周末成交量减少
    for i, date in enumerate(dates):
        if date.weekday() >= 5:  # 周六日
            volume[i] = volume[i] // 3
    
    # 创建DataFrame
    df = pd.DataFrame({
        'datetime': dates,
        'open': open_price.round(2),
        'high': high.round(2),
        'low': low.round(2),
        'close': close.round(2),
        'volume': volume
    })
    
    # 保证high/low合理性
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    return df

# 3. 生成并保存数据文件
def main():
    print("开始生成模拟分割数据...")
    
    # 生成2023年数据
    df_2023 = generate_2023_data()
    print(f"已生成2023年数据，共 {len(df_2023)} 条记录")
    
    # 获取2023年最后一天的收盘价
    last_price_2023 = df_2023.iloc[-1]['close']
    
    # 生成2024年Q1数据
    df_2024_q1 = generate_2024_q1_data(last_price_2023)
    print(f"已生成2024年Q1数据，共 {len(df_2024_q1)} 条记录")
    
    # 保存文件
    csv_2023 = 'data_cache/au888_2023.csv'
    df_2023.to_csv(csv_2023, index=False)
    print(f"已保存2023年数据: {csv_2023}")
    
    csv_2024_q1 = 'data_cache/au888_2024_q1.csv'
    df_2024_q1.to_csv(csv_2024_q1, index=False)
    print(f"已保存2024年Q1数据: {csv_2024_q1}")
    
    # 生成合并数据作为参考
    df_combined = pd.concat([df_2023, df_2024_q1])
    combined_csv = 'data_cache/au888_combined.csv'
    df_combined.to_csv(combined_csv, index=False)
    print(f"已保存合并数据作为参考: {combined_csv}")
    
    print(f"\n所有数据文件生成完毕，文件位置：")
    print(f"  - 2023年数据: {csv_2023}")
    print(f"  - 2024年Q1数据: {csv_2024_q1}")
    print(f"  - 合并参考数据: {combined_csv}")

if __name__ == "__main__":
    main() 