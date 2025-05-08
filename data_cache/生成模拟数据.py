import pandas as pd
import numpy as np
import os

# 可选：如需7z压缩，需先安装 py7zr
try:
    import py7zr
    has_py7zr = True
except ImportError:
    has_py7zr = False

# 1. 生成模拟行情数据
dates = pd.date_range('2023-01-01', periods=100, freq='D')
data = pd.DataFrame({
    'datetime': dates,
    'open': np.random.uniform(400, 500, size=100).round(2),
    'high': np.random.uniform(400, 500, size=100).round(2),
    'low': np.random.uniform(400, 500, size=100).round(2),
    'close': np.random.uniform(400, 500, size=100).round(2),
    'volume': np.random.randint(1000, 10000, size=100)
})
# 保证high/low合理
data['high'] = data[['open', 'close', 'low', 'high']].max(axis=1)
data['low'] = data[['open', 'close', 'low', 'high']].min(axis=1)

os.makedirs('data_cache', exist_ok=True)

# 2. 保存为CSV
csv_path = 'data_cache/au888_1d.csv'
data.to_csv(csv_path, index=False)
print(f'已生成CSV: {csv_path}')

# 3. 保存为HDF5
h5_path = 'data_cache/au888_1d.h5'
data.to_hdf(h5_path, key='au888_1d', mode='w')
print(f'已生成HDF5: {h5_path} (key=au888_1d)')

# 4. 保存为7z（需py7zr）
if has_py7zr:
    z_path = 'data_cache/au888_1d.7z'
    with py7zr.SevenZipFile(z_path, 'w') as archive:
        archive.write(csv_path, arcname='au888_1d.csv')
    print(f'已生成7z压缩包: {z_path}')
else:
    print('未安装py7zr，未生成7z压缩包。如需支持请 pip install py7zr')

print('模拟数据全部生成完毕！') 