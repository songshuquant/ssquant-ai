import pandas as pd
import numpy as np
import os
import datetime

# 创建数据目录
os.makedirs('data_cache', exist_ok=True)

def generate_tick_data(start_time, end_time, initial_price=450.0, initial_volume=0):
    """
    生成指定时间段的tick数据
    
    参数：
    - start_time: 开始时间
    - end_time: 结束时间
    - initial_price: 起始价格
    - initial_volume: 起始成交量
    
    返回：
    - 包含tick数据的DataFrame
    """
    # 创建时间序列，每秒一个tick
    times = pd.date_range(start=start_time, end=end_time, freq='S')
    n = len(times)
    
    # 价格随机游走，以initial_price为起点
    price = np.zeros(n)
    price[0] = initial_price
    
    # 使用小波动模拟tick级价格变化
    volatility = 0.0002  # tick级波动率
    returns = np.random.normal(0, volatility, n)
    for i in range(1, n):
        price[i] = price[i-1] * (1 + returns[i])
    
    # 确保价格在合理范围内
    price = np.clip(price, initial_price * 0.95, initial_price * 1.05)
    
    # 生成买一卖一价格
    spread = np.random.uniform(0.1, 0.5, n)  # 买卖价差
    bid1 = price - spread / 2
    ask1 = price + spread / 2
    
    # 生成成交量（累计）
    volume = np.zeros(n, dtype=int)
    volume[0] = initial_volume
    
    # 每个tick随机增加一定的成交量
    vol_increments = np.random.randint(0, 10, n)
    # 有10%的概率出现较大成交量
    large_vol_mask = np.random.random(n) < 0.1
    vol_increments[large_vol_mask] = np.random.randint(20, 100, np.sum(large_vol_mask))
    
    # 计算累计成交量
    for i in range(1, n):
        volume[i] = volume[i-1] + vol_increments[i]
    
    # 创建DataFrame
    df = pd.DataFrame({
        'datetime': times,
        'bid1': bid1.round(2),
        'ask1': ask1.round(2),
        'price': price.round(2),  # 中间价
        'volume': volume,         # 累计成交量
        # 添加其他可能需要的字段
        'bid1_volume': np.random.randint(10, 100, n),
        'ask1_volume': np.random.randint(10, 100, n),
    })
    
    return df

def main():
    print("开始生成模拟tick数据...")
    
    # 定义三个时间段
    periods = [
        # 第一部分：2023年1月前10天
        {
            'start': '2023-01-01 09:00:00',
            'end': '2023-01-10 15:00:00',
            'initial_price': 450.0,
            'initial_volume': 0,
            'file': 'data_cache/tick_data_part1.csv'
        },
        # 第二部分：2023年1月中旬10天
        {
            'start': '2023-01-11 09:00:00',
            'end': '2023-01-20 15:00:00',
            'initial_price': None,  # 将根据上一部分的最后价格设置
            'initial_volume': None,  # 将根据上一部分的最后成交量设置
            'file': 'data_cache/tick_data_part2.csv'
        },
        # 第三部分：2023年1月下旬10天
        {
            'start': '2023-01-21 09:00:00',
            'end': '2023-01-31 15:00:00',
            'initial_price': None,  # 将根据上一部分的最后价格设置
            'initial_volume': None,  # 将根据上一部分的最后成交量设置
            'file': 'data_cache/tick_data_part3.csv'
        }
    ]
    
    last_price = None
    last_volume = None
    
    # 生成并保存每个时间段的数据
    for i, period in enumerate(periods):
        # 如果未设置初始价格和成交量，则使用上一部分的最后值
        if i > 0:
            period['initial_price'] = last_price
            period['initial_volume'] = last_volume
        
        print(f"正在生成第 {i+1} 部分数据: {period['start']} 到 {period['end']}...")
        
        # 生成当前时间段的tick数据
        df = generate_tick_data(
            start_time=period['start'],
            end_time=period['end'],
            initial_price=period['initial_price'],
            initial_volume=period['initial_volume']
        )
        
        # 保存最后一个tick的价格和成交量，用于下一部分的初始值
        last_price = df.iloc[-1]['price']
        last_volume = df.iloc[-1]['volume']
        
        # 保存到CSV文件
        df.to_csv(period['file'], index=False)
        print(f"已保存到文件: {period['file']}, 记录数: {len(df)}")
    
    print("\n所有tick数据文件生成完毕，文件位置：")
    for period in periods:
        print(f"  - {period['file']}")
    
    # 生成合并数据作为参考
    print("\n生成合并参考数据...")
    dfs = []
    for period in periods:
        df = pd.read_csv(period['file'], parse_dates=['datetime'])
        dfs.append(df)
    
    combined_df = pd.concat(dfs)
    combined_csv = 'data_cache/tick_data_combined.csv'
    combined_df.to_csv(combined_csv, index=False)
    print(f"已保存合并数据作为参考: {combined_csv}, 总记录数: {len(combined_df)}")

if __name__ == "__main__":
    main() 