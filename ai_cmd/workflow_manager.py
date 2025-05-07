from typing import Dict, Any, Optional, Callable
import json
import os
from datetime import datetime

# 使用显式相对导入
from .gpt_client import GPTClient
from .backtest_engine import BacktestEngine
from .code_parser import CodeParser
from . import config

class WorkflowManager:
    """
    工作流管理类，负责协调GPT和回测系统的交互
    """
    
    def __init__(self):
        """初始化工作流管理器"""
        self.gpt_client = GPTClient()
        self.backtest_engine = BacktestEngine()
        self.current_strategy_code = None
        self.backtest_results = None
        self.iteration_count = 0
        self.symbol = "AAPL"  # 默认交易标的
        self.start_date = "2020-01-01"  # 默认开始日期
        self.end_date = "2022-12-31"  # 默认结束日期
        
    def set_trading_parameters(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        设置交易参数
        
        Args:
            symbol: 交易标的代码
            start_date: 开始日期，格式: YYYY-MM-DD
            end_date: 结束日期，格式: YYYY-MM-DD
            
        Returns:
            bool: 是否成功加载数据
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        return self.backtest_engine.load_data(symbol, start_date, end_date)
    
    def handle_user_message(self, user_message: str, stream: bool = False, stream_callback: Callable[[str], None] = None) -> str:
        """
        处理用户消息
        
        Args:
            user_message: 用户输入的消息
            stream: 是否使用流式响应
            stream_callback: 流式响应的回调函数
            
        Returns:
            str: 处理结果
        """
        # 向GPT发送用户消息
        self.gpt_client.add_message("user", user_message)
        
        # 获取GPT响应，支持流式输出
        if stream and stream_callback:
            response = self.gpt_client.get_stream_response(stream_callback)
        else:
            response = self.gpt_client.get_response()
        
        # 从GPT响应中提取代码
        code = CodeParser.extract_code(response)
        
        if code:
            # 如果找到代码，尝试运行回测
            self.current_strategy_code = code
            return self._run_backtest_and_report(stream, stream_callback)
        else:
            # 如果没有找到代码，只返回GPT的回复
            return response
    
    def _run_backtest_and_report(self, stream: bool = False, stream_callback: Callable[[str], None] = None) -> str:
        """
        运行回测并生成报告
        
        Args:
            stream: 是否使用流式响应
            stream_callback: 流式响应的回调函数
            
        Returns:
            str: 回测结果报告
        """
        # 重置迭代计数
        self.iteration_count = 0
        
        # 确保数据已加载
        if not self.backtest_engine.data_loaded:
            success = self.backtest_engine.load_data(self.symbol, self.start_date, self.end_date)
            if not success:
                return f"无法加载交易数据。请确保数据可用或尝试更改交易参数。"
        
        # 更新回调函数的进度消息
        if stream and stream_callback:
            stream_callback("\n\n正在执行回测...\n\n")
        
        # 尝试运行策略，如果出错则反馈给GPT修复
        while self.iteration_count < config.MAX_ITERATIONS:
            success, message, results = self.backtest_engine.run_strategy_code(self.current_strategy_code)
            
            if success:
                # 回测成功
                self.backtest_results = results
                results_summary = self._format_results(results)
                
                if stream and stream_callback:
                    stream_callback(f"\n策略回测成功！\n\n{message}\n\n{results_summary}\n\n分析中...\n\n")
                
                # 向GPT报告回测结果并获取分析
                if stream and stream_callback:
                    gpt_analysis = self.gpt_client.report_results(results_summary, stream=True, callback=stream_callback)
                    return f"策略回测成功！\n\n{message}\n\n{results_summary}\n\n分析：\n{gpt_analysis}"
                else:
                    gpt_analysis = self.gpt_client.report_results(results_summary)
                    return f"策略回测成功！\n\n{message}\n\n{results_summary}\n\n分析：\n{gpt_analysis}"
            else:
                # 回测失败，请求GPT修复
                self.iteration_count += 1
                
                if self.iteration_count >= config.MAX_ITERATIONS:
                    return f"达到最大尝试次数。最后一次错误：\n{message}"
                
                if stream and stream_callback:
                    stream_callback(f"\n回测出错，尝试修复 (第{self.iteration_count}次)...\n错误信息：\n{message}\n\n")
                
                # 获取GPT对错误的修复
                if stream and stream_callback:
                    fixed_response = self.gpt_client.report_error(message, stream=True, callback=stream_callback)
                else:
                    fixed_response = self.gpt_client.report_error(message)
                    
                fixed_code = CodeParser.extract_code(fixed_response)
                
                if fixed_code:
                    self.current_strategy_code = fixed_code
                    
                    if stream and stream_callback:
                        stream_callback("\n\n已获取修复代码，正在重新尝试回测...\n\n")
                        
                    continue  # 尝试运行修复后的代码
                else:
                    return f"GPT无法提供有效的代码修复。错误信息：\n{message}\n\nGPT响应：\n{fixed_response}"
        
        return "达到最大尝试次数，无法成功运行策略。"
    
    def _format_results(self, results: Dict[str, Any]) -> str:
        """
        格式化回测结果为可读文本
        
        Args:
            results: 回测结果字典
            
        Returns:
            str: 格式化的结果文本
        """
        formatted = "回测结果摘要:\n"
        formatted += f"- 初始资金: ¥{results['initial_capital']:,.2f}\n"
        formatted += f"- 最终价值: ¥{results['final_portfolio_value']:,.2f}\n"
        formatted += f"- 总回报率: {results['returns_pct']:.2f}%\n"
        formatted += f"- 回测图表保存至: {results['figure_path']}\n\n"
        
        # 添加其他分析器结果（如果有的话）
        other_metrics = {k: v for k, v in results.items() 
                         if k not in ['initial_capital', 'final_portfolio_value', 
                                     'returns_pct', 'figure_path', 'log_output']}
        
        if other_metrics:
            formatted += "详细指标:\n"
            for name, value in other_metrics.items():
                if isinstance(value, dict):
                    formatted += f"- {name}:\n"
                    for metric_name, metric_value in value.items():
                        formatted += f"  - {metric_name}: {metric_value}\n"
                else:
                    formatted += f"- {name}: {value}\n"
        
        # 添加日志输出（如果有的话）
        if results.get('log_output'):
            log_excerpt = results['log_output'].split('\n')[:20]  # 只显示前20行
            formatted += "\n日志输出 (前20行):\n"
            formatted += '\n'.join(log_excerpt)
            if len(results['log_output'].split('\n')) > 20:
                formatted += "\n... (更多日志已省略)"
        
        return formatted
    
    def save_strategy(self, filename: Optional[str] = None) -> str:
        """
        保存当前策略到文件
        
        Args:
            filename: 可选的文件名
            
        Returns:
            str: 保存结果消息
        """
        if not self.current_strategy_code:
            return "没有可保存的策略代码。"
        
        # 检查回测结果中是否已包含策略文件路径
        if self.backtest_results and 'strategy_file' in self.backtest_results:
            # 策略已经保存，只需要复制到新位置（如果提供了新文件名）
            source_path = self.backtest_results['strategy_file']
            
            if not filename:
                return f"策略已保存在: {source_path}"
            
            # 确保有.py扩展名
            if not filename.endswith('.py'):
                filename += '.py'
            
            try:
                import shutil
                shutil.copy2(source_path, filename)
                return f"策略已复制并保存到: {filename} (原始文件: {source_path})"
            except Exception as e:
                return f"复制策略文件时出错: {str(e)}"
        
        # 如果没有在回测结果中找到，使用原来的保存逻辑
        if not filename:
            # 尝试从代码中提取策略名称
            strategy_name = "策略"  # 默认名称
            try:
                import re
                # 搜索"def strategy_function"或"def initialize"模式
                func_match = re.search(r'def\s+strategy_function|def\s+initialize', self.current_strategy_code)
                if func_match:
                    # 尝试从注释或函数名中提取策略名称
                    strategy_desc_match = re.search(r'\"\"\"(.*?)\"\"\"', self.current_strategy_code, re.DOTALL)
                    if strategy_desc_match:
                        desc_text = strategy_desc_match.group(1)
                        # 从描述中提取可能的策略名称
                        name_match = re.search(r'(.*?)策略', desc_text)
                        if name_match:
                            extracted_name = name_match.group(0).strip()
                            if extracted_name:
                                strategy_name = extracted_name
                                print(f"从策略描述中提取到策略名称: {strategy_name}")
                    
                    # 如果没有从描述提取到名称，使用默认名称
                    if strategy_name == "策略":
                        strategy_name = "期货策略"
                        print(f"未提取到具体策略名称，使用默认名称: {strategy_name}")
            except Exception as name_err:
                print(f"提取策略名称时出错: {name_err}")
                strategy_name = "期货策略"  # 确保有默认值
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{strategy_name}_{timestamp}.py"
        
        # 确保有.py扩展名
        if not filename.endswith('.py'):
            filename += '.py'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.current_strategy_code)
            return f"策略已保存到文件: {filename}"
        except Exception as e:
            return f"保存策略时出错: {str(e)}"
    
    def reset_conversation(self) -> str:
        """
        重置对话，开始新的会话
        
        Returns:
            str: 重置结果消息
        """
        self.gpt_client.clear_conversation()
        self.current_strategy_code = None
        self.backtest_results = None
        self.iteration_count = 0
        return "会话已重置，可以开始新的策略讨论。" 