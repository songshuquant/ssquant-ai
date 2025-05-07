import os
import sys
import io
import traceback
import tempfile
import signal
from typing import Dict, Any, Tuple
import importlib.util
import pandas as pd
# import backtrader as bt # 已移除
import matplotlib
# matplotlib.use('Agg') # 不再需要
import matplotlib.pyplot as plt
from datetime import datetime
# 改为使用绝对导入
import config
import time
import uuid  # 用于生成唯一文件名

# 超时处理函数
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("操作超时")

class BacktestEngine:
    """
    回测引擎类，负责执行策略的回测
    # 注意：使用ssquant框架进行回测
    """

    def __init__(self):
        """初始化回测引擎"""
        self.data_loaded = False
        self.last_data_info = {
            "symbol": None,
            "start_date": None,
            "end_date": None,
            "data_path": None,
            "encoding": "utf-8",
            "data_df": None # 仍然可以保留加载的原始数据DataFrame
        }
        self.results_dir = config.RESULTS_DIR # 使用配置中的结果目录

        # 创建必要的目录
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True) # 使用 self.results_dir

    def load_data(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        加载回测数据
        # 注意：此实现基于Pandas加载CSV，可能需要调整以适应 src 框架
        """
        try:
            data_path = os.path.join(config.DATA_DIR, f"{symbol}.csv")
            if not os.path.exists(data_path):
                print(f"未找到数据文件 {data_path}，将创建示例数据")
                self._create_sample_data(data_path)

            print(f"正在加载数据文件: {os.path.abspath(data_path)}")
            encoding = 'utf-8'
            data_df = None
            try:
                data_df = pd.read_csv(data_path, encoding='utf-8')
                print("成功使用UTF-8编码读取数据")
            except UnicodeDecodeError:
                try:
                    data_df = pd.read_csv(data_path, encoding='gbk')
                    print("成功使用GBK编码读取数据")
                    encoding = 'gbk'
                except:
                    data_df = pd.read_csv(data_path, encoding='latin1')
                    print("成功使用latin1编码读取数据")
                    encoding = 'latin1'

            # 数据预处理和验证（保留这部分逻辑可能有用）
            if len(data_df) > 1000:
                 print(f"数据量较大 ({len(data_df)}行)，为提高性能将采样至1000行")
                 data_df = data_df.iloc[::max(1, len(data_df)//1000)].reset_index(drop=True)

            if 'Date' in data_df.columns:
                data_df = data_df.rename(columns={'Date': 'datetime'})
            column_mapping = {'open': 'Open','high': 'High','low': 'Low', 'close': 'Close','volume': 'Volume','adj close': 'Adj Close','adj_close': 'Adj Close'}
            data_df.rename(columns={k: v for k, v in column_mapping.items() if k in data_df.columns}, inplace=True)

            if 'datetime' in data_df.columns:
                if isinstance(data_df['datetime'].iloc[0], str):
                    data_df['datetime'] = pd.to_datetime(data_df['datetime'])
                elif not isinstance(data_df['datetime'].iloc[0], pd.Timestamp):
                     data_df['datetime'] = pd.to_datetime(data_df['datetime'])

            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in data_df.columns:
                     print(f"警告: 缺少必要的列 '{col}'，尝试修复")
                     possible_matches = [c for c in data_df.columns if c.lower() == col.lower()]
                     if possible_matches:
                         data_df[col] = data_df[possible_matches[0]]
                     else:
                         if col in ['Open', 'High', 'Low', 'Close']:
                             if 'Close' in data_df.columns: data_df[col] = data_df['Close']
                             else: data_df[col] = 100.0
                         elif col == 'Volume': data_df[col] = 1000

            print(f"数据预览: \n{data_df.head()}")
            print(f"数据列: {data_df.columns.tolist()}")

            # 保存数据信息，框架可能需要
            self.last_data_info = {
                "symbol": symbol, "start_date": start_date, "end_date": end_date,
                "data_path": data_path, "encoding": encoding,
                "data_df": data_df.copy() if data_df is not None else None
            }
            self.data_loaded = True
            print("数据信息已加载和预处理")
            return True
        except Exception as e:
            print(f"加载数据失败: {e}")
            print(traceback.format_exc())
            self.data_loaded = False
            return False

    def _create_sample_data(self, data_path: str) -> None:
        """创建示例数据文件，仅用于演示"""
        # (这部分逻辑可以保留，用于在没有真实数据时提供示例)
        dates = pd.date_range(start='2020-01-01', end='2022-12-31')
        import numpy as np
        np.random.seed(42)
        price = 100.0
        prices = []
        for _ in range(len(dates)):
            price = price * (1 + np.random.normal(0.0001, 0.02))
            prices.append(price)
        df = pd.DataFrame({
            'Date': dates.strftime('%Y-%m-%d'),
            'Open': prices,
            'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'Close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'Volume': [np.random.randint(1000000, 10000000) for _ in prices],
            'Adj Close': [p * (1 + np.random.normal(0, 0.005)) for p in prices]
        })
        df.to_csv(data_path, index=False)
        print(f"已创建示例数据文件: {data_path}")

    def _reload_data(self) -> bool:
        """
        根据上次加载的信息重新加载数据
        # 注意：此实现仅重新加载DataFrame，可能需要调整以适应 src 框架
        """
        if self.last_data_info["symbol"] and self.last_data_info["data_df"] is not None:
            print("尝试重新加载上次的数据信息...")
            self.data_loaded = True
            print("数据信息已重新加载")
            return True
        else:
            print("没有可重新加载的数据信息")
            return False

    def run_strategy_code(self, strategy_code: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        执行策略代码进行回测
        # 注意：这是主要需要重写的部分，以调用 src 中的框架
        """
        # 检查数据是否加载
        if not self.data_loaded:
            if not self._reload_data():
                return False, "数据未加载，无法运行策略", {}

        print("\n开始执行策略代码...")
        # 创建临时文件保存策略代码
        temp_file_path = None
        log_output = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        results = {}
        figure_path = None

        # 设置超时 (例如 5 分钟)
        timeout_seconds = 300
        # signal.signal(signal.SIGALRM, timeout_handler) # 在windows下可能不支持
        # signal.alarm(timeout_seconds) # 在windows下可能不支持

        try:
            # ======== 占位符：需要替换为调用 src 框架的逻辑 ========            
            print("需要实现 src 框架调用 !!!")
            print("假设执行成功，返回示例结果...")
            # 模拟执行成功
            success = True
            message = "策略执行完成 (占位符)"
            # 模拟返回结果
            results = {
                'initial_capital': config.DEFAULT_CASH,
                'final_portfolio_value': config.DEFAULT_CASH * 1.1, # 示例：10% 收益
                'returns_pct': 10.0,
                'sharpe': 1.5, # 示例
                'drawdown': 5.0, # 示例
                'figure_path': self._get_placeholder_plot(), # 返回占位符图表
                'log_output': "策略执行日志 (占位符)"
            }
            # ======== 占位符结束 ========           
            # signal.alarm(0) # 取消超时

            # 返回执行结果
            return success, message, results

        except TimeoutException:
            # signal.alarm(0) # 取消超时
            error_msg = "回测执行超时"
            print(f"[ERROR] {error_msg}")
            return False, error_msg, {}
        except Exception as e:
            # signal.alarm(0) # 取消超时
            # 捕获并格式化错误信息
            error_type = type(e).__name__
            error_msg = str(e)
            tb_lines = traceback.format_exc().splitlines()
            # 提取与临时策略文件相关的错误行
            strategy_error_lines = [line for line in tb_lines if temp_file_path and os.path.basename(temp_file_path) in line]
            if not strategy_error_lines:
                 # 如果没找到策略文件的错误，取最后几行
                 strategy_error_lines = tb_lines[-5:]

            formatted_error = f"策略执行失败: {error_type}: {error_msg}\nRelevant Traceback:\n" + "\n".join(strategy_error_lines)
            print(f"[ERROR] {formatted_error}")
            return False, formatted_error, {}
        finally:
            # signal.alarm(0) # 确保在任何情况下都取消超时
            # 恢复标准输出和错误
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"警告：无法删除临时文件 {temp_file_path}: {e}")
            # 关闭StringIO
            log_output_str = log_output.getvalue()
            log_output.close()
            # 将日志添加到结果中（如果需要）
            if 'log_output' not in results and log_output_str:
                 results['log_output'] = log_output_str

    def _get_placeholder_plot(self) -> str:
         """生成一个占位符图表"""
         try:
             plt.figure(figsize=(10, 6))
             plt.plot([1, 2, 3], [1, 2, 1], label='Placeholder Data')
             plt.title('Placeholder Backtest Plot')
             plt.xlabel('Time')
             plt.ylabel('Value')
             plt.legend()
             plt.grid(True)
             # 使用唯一文件名保存图表
             figure_filename = f"placeholder_plot_{uuid.uuid4()}.png"
             figure_path = os.path.join(self.results_dir, figure_filename)
             plt.savefig(figure_path)
             plt.close() # 关闭图形，释放内存
             print(f"已生成占位符图表: {figure_path}")
             return figure_path
         except Exception as e:
             print(f"生成占位符图表失败: {e}")
             return ""

    def _get_price_data_for_backup_plot(self):
         """获取用于备用绘图的价格数据 (可以保留)"""
         if self.last_data_info["data_df"] is not None:
             df = self.last_data_info["data_df"].copy()
             if 'datetime' in df.columns:
                 df.set_index('datetime', inplace=True)
             return df
         return None 