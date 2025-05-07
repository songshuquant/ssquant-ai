"""
AI助手与期货回测框架集成模块

该模块负责将AI助手生成的策略代码与期货回测框架集成，
提供代码生成、策略运行和结果分析等功能。
"""

# 移除不存在的路径导入
# from src.config.path_config import setup_python_path

# 不再需要调用setup_python_path函数
# setup_python_path()

import os
import sys
import importlib.util
import traceback
from typing import Dict, Any, Tuple, Optional, Callable, List
import tempfile
import uuid
from datetime import datetime
import subprocess
import re
from string import Template

# 路径修复 - 删除旧路径，添加新路径
# 获取当前文件所在目录的上级目录(项目根目录)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 删除旧的回测框架路径
old_path = r"d:\回测框架"
if old_path in sys.path:
    sys.path.remove(old_path)
    print(f"已移除旧路径: {old_path}")

# 添加当前项目路径到sys.path的最前面
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"已添加新路径: {current_dir}")

# 将ai_assistant目录添加到路径中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入AI助手模块
# 使用绝对导入
from gpt_client import GPTClient
# 使用绝对导入
from code_parser import CodeParser
# 使用绝对导入
from config import prompter  # 使用提示词管理器而不是直接导入模板

class IntegrationManager:
    """
    集成管理器
    
    负责协调AI助手和期货回测框架的交互
    """
    
    def __init__(self):
        """初始化集成管理器"""
        # 初始化AI助手组件
        self.gpt_client = GPTClient()
        self.code_parser = CodeParser()
        
        # 状态存储
        self.current_strategy_code = ""
        self.current_strategy_name = ""
        self.current_strategy_path = ""
        self.backtest_results = {}
        
        # 对话状态
        self.conversation_history = []
        self.is_conversation_active = True
        
        # 创建策略目录
        self.strategies_dir = "ai_strategies"
        if not os.path.exists(self.strategies_dir):
            os.makedirs(self.strategies_dir)
    
    def reset_conversation(self):
        """重置对话历史，但保留当前策略"""
        # 只清除对话历史
        self.gpt_client.reset_messages()
        self.conversation_history = []
        self.is_conversation_active = True
        
        # 不清除当前策略
        # self.current_strategy_code = None
        # self.current_strategy_name = None
        # self.current_strategy_path = None
        # self.backtest_results = None
        
        print("对话历史已重置，但保留了当前策略")
    
    def generate_strategy(self, user_query: str, symbol: str = 'rb888', 
                         start_date: str = '2023-01-01', end_date: str = '2023-12-31',
                         period: str = '1d', stream: bool = False, 
                         stream_callback: Callable[[str], None] = None) -> Tuple[bool, str, str]:
        """
        生成交易策略代码
        
        Args:
            user_query: 用户的策略需求描述
            symbol: 交易品种代码
            start_date: 回测开始日期
            end_date: 回测结束日期
            period: 交易周期
            stream: 是否使用流式输出
            stream_callback: 流式输出的回调函数
            
        Returns:
            Tuple[bool, str, str]: (是否成功, 消息, 策略代码)
        """
        try:
            # 获取模板
            template_str = prompter.GENERATE_STRATEGY_TEMPLATE
            
            # 将模板中的占位符替换为Template格式
            template_str = template_str.replace("{user_query}", "$user_query")\
                                                   .replace("{symbol}", "$symbol")\
                                                   .replace("{start_date}", "$start_date")\
                                                   .replace("{end_date}", "$end_date")\
                                                   .replace("{period}", "$period")
            
            # 使用Template类进行安全的字符串格式化
            template = Template(template_str)
            prompt = template.safe_substitute(
                user_query=user_query,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                period=period
            )
            
            # 添加用户消息
            self.gpt_client.add_message("user", prompt)
            self.conversation_history.append({"role": "user", "content": user_query})
            
            # 获取GPT响应，支持流式输出
            if stream and stream_callback:
                print("使用流式响应模式获取策略...")
                response = self.gpt_client.get_stream_response(stream_callback)
            else:
                print("使用非流式响应模式获取策略...")
                response = self.gpt_client.get_response()
            
            # 记录AI响应到对话历史
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # 使用CodeParser提取代码
            strategy_code = self.code_parser.extract_code(response)
            
            if not strategy_code:
                return False, "无法从GPT响应中提取有效的策略代码", ""
            
            # 保存当前策略代码
            self.current_strategy_code = strategy_code
            
            return True, "成功生成策略代码", strategy_code
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"生成策略时出错: {str(e)}\n{error_info}")
            return False, f"生成策略时发生错误: {str(e)}\n{error_info}", ""
    
    def save_strategy(self, filename: Optional[str] = None) -> str:
        """
        保存当前策略到文件
        
        Args:
            filename: 文件名，如果为None则使用时间戳生成
            
        Returns:
            str: 保存结果消息
        """
        if not self.current_strategy_code:
            return "没有可保存的策略代码"
            
        try:
            # 生成文件名
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"策略_{timestamp}.py"
            elif not filename.endswith('.py'):
                filename = f"{filename}.py"
            
            # 保存路径
            save_path = os.path.join("ai_strategies", filename)
            
            # 写入文件
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.current_strategy_code)
            
            # 记录当前策略文件路径和名称
            self.current_strategy_name = filename
            self.current_strategy_path = save_path
            
            return f"策略已保存至: {save_path}"
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"保存策略时出错: {str(e)}\n{error_info}")
            return f"保存策略失败: {str(e)}"
            
    def run_backtest(self, strategy_code: Optional[str] = None, 
                    stream: bool = False, 
                    stream_callback: Callable[[str], None] = None) -> Tuple[bool, str, Dict]:
        """
        运行回测
        
        Args:
            strategy_code: 策略代码，如果为None则使用当前策略
            stream: 是否使用流式输出
            stream_callback: 流式输出的回调函数
            
        Returns:
            Tuple[bool, str, Dict]: (是否成功, 消息, 结果)
        """
        try:
            # 使用提供的代码或当前策略代码
            code_to_use = strategy_code if strategy_code else self.current_strategy_code
            
            # 如果没有策略代码
            if not code_to_use:
                return False, "没有可运行的策略代码", {}
            
            # 先保存策略
            if not self.current_strategy_path or strategy_code:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.current_strategy_name = f"策略_{timestamp}.py"
                self.current_strategy_path = os.path.join("ai_strategies", self.current_strategy_name)
                
                with open(self.current_strategy_path, 'w', encoding='utf-8') as f:
                    f.write(code_to_use)
            
            # 运行策略文件进行回测
            cmd = [sys.executable, self.current_strategy_path]
            print(f"执行命令: {' '.join(cmd)}")
            
            # 设置环境变量，确保使用UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            if stream and stream_callback:
                # 使用实时输出
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                    encoding='utf-8'
                )
                
                output = []
                for line in iter(process.stdout.readline, ''):
                    output.append(line)
                    if stream_callback:
                        stream_callback(line)
                
                process.stdout.close()
                return_code = process.wait()
                
                if return_code != 0:
                    print(f"回测进程返回错误码: {return_code}")
                    full_output = ''.join(output)
                    
                    # 自动修复策略代码
                    if stream_callback:
                        stream_callback("\n\n检测到回测错误，正在分析并修复...\n")
                    
                    success, message, fixed_code = self.fix_strategy(full_output, code_to_use, 
                                                                  stream=stream, 
                                                                  stream_callback=stream_callback)
                    if success and fixed_code:
                        # 保存修复后的代码
                        if stream_callback:
                            stream_callback("\n修复完成，正在重新运行回测...\n")
                        
                        # 递归调用自身重新运行回测
                        return self.run_backtest(fixed_code, stream, stream_callback)
                    
                    return False, f"回测执行失败，错误信息:\n{full_output}", {}
                
                full_output = ''.join(output)
                self.backtest_results = {'output': full_output}
                
                # 提取回测日志和图表路径
                log_path, chart_paths = self._extract_paths_from_output(full_output)
                if log_path or chart_paths:
                    self.backtest_results['log_path'] = log_path
                    self.backtest_results['chart_paths'] = chart_paths
                
                # 自动进行回测分析
                if stream_callback:
                    stream_callback("\n\n正在分析回测结果...\n")
                
                analysis = self.analyze_backtest_results(full_output, log_path, chart_paths, 
                                                        stream=stream, stream_callback=stream_callback)
                if analysis:
                    self.backtest_results['analysis'] = analysis
                
                return True, "回测执行完成", self.backtest_results
            else:
                # 不使用实时输出
                result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding='utf-8')
                if result.returncode != 0:
                    print(f"回测执行失败: {result.stderr}")
                    
                    # 自动修复策略代码
                    success, message, fixed_code = self.fix_strategy(
                        f"{result.stdout}\n{result.stderr}", 
                        code_to_use
                    )
                    if success and fixed_code:
                        # 递归调用自身重新运行回测
                        return self.run_backtest(fixed_code, stream, stream_callback)
                    
                    return False, f"回测执行失败: {result.stderr}", {}
                
                full_output = result.stdout
                self.backtest_results = {'output': full_output}
                
                # 提取回测日志和图表路径
                log_path, chart_paths = self._extract_paths_from_output(full_output)
                if log_path or chart_paths:
                    self.backtest_results['log_path'] = log_path
                    self.backtest_results['chart_paths'] = chart_paths
                
                # 自动进行回测分析
                analysis = self.analyze_backtest_results(full_output, log_path, chart_paths)
                if analysis:
                    self.backtest_results['analysis'] = analysis
                
                return True, "回测执行完成", self.backtest_results
        
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"运行回测时出错: {str(e)}\n{error_info}")
            return False, f"运行回测时出错: {str(e)}", {}
    
    def _extract_paths_from_output(self, output: str) -> Tuple[Optional[str], List[str]]:
        """
        从回测输出中提取日志和图表路径
        
        Args:
            output: 回测输出文本
            
        Returns:
            Tuple[Optional[str], List[str]]: (日志路径, 图表路径列表)
        """
        log_path = None
        chart_paths = []
        
        # 提取日志文件路径
        log_matches = re.findall(r'绩效报告已保存到: (backtest_logs\\[\w\\]+\.txt)', output)
        if log_matches:
            log_path = log_matches[0]
        
        # 提取图表路径
        chart_matches = re.findall(r'回测图表已保存到: (backtest_results\\[\w\\]+\.png)', output)
        chart_paths.extend(chart_matches)
        
        # 提取综合收益图表路径
        combined_chart_matches = re.findall(r'综合收益图表已保存到: (backtest_results\\[\w\\]+\.png)', output)
        chart_paths.extend(combined_chart_matches)
        
        return log_path, chart_paths
    
    def analyze_backtest_results(self, output: str, log_path: Optional[str] = None, 
                                chart_paths: List[str] = None, stream: bool = False,
                                stream_callback: Callable[[str], None] = None) -> str:
        """
        分析回测结果
        
        Args:
            output: 回测输出文本
            log_path: 日志文件路径
            chart_paths: 图表路径
            stream: 是否使用流式输出
            stream_callback: 流式输出回调
            
        Returns:
            str: 分析结果
        """
        try:
            # 准备分析提示
            prompt = self._prepare_analysis_prompt(output, log_path, chart_paths)
            
            # 不再清除对话历史，保持上下文连续性
            # self.gpt_client.clear_conversation()
            
            # 添加用户消息
            self.gpt_client.add_message("user", prompt)
            self.conversation_history.append({"role": "user", "content": "请分析回测结果"})
            
            # 获取分析结果
            if stream and stream_callback:
                analysis = self.gpt_client.get_stream_response(stream_callback)
            else:
                analysis = self.gpt_client.get_response()
            
            # 记录AI响应到对话历史
            self.conversation_history.append({"role": "assistant", "content": analysis})
            
            return analysis
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"分析回测结果时出错: {str(e)}\n{error_info}")
            return f"无法分析回测结果: {str(e)}"
    
    def _prepare_analysis_prompt(self, output: str, log_path: Optional[str] = None, 
                                chart_paths: List[str] = None) -> str:
        """
        准备回测分析提示
        
        Args:
            output: 回测输出文本
            log_path: 日志文件路径
            chart_paths: 图表路径
            
        Returns:
            str: 分析提示
        """
        # 提取回测摘要信息
        summary_match = re.search(r'回测结果摘要:(.*?)(?:\n\n|$)', output, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else "未找到回测摘要"
        
        # 提取交易明细
        trades_match = re.search(r'交易明细:(.*?)(?:\n\n|$)', output, re.DOTALL)
        trades = trades_match.group(1).strip() if trades_match else "未找到交易明细"
        
        # 提取关键指标
        indicators = {}
        key_indicators = [
            '总交易次数', '盈利交易', '亏损交易', '胜率', '初始权益', '期末权益', 
            '净值', '总点数盈亏', '总金额盈亏', '总手续费', '总净盈亏',
            '平均盈利', '平均亏损', '盈亏比', '最大回撤', '年化收益率', '夏普比率'
        ]
        
        for indicator in key_indicators:
            pattern = rf'\[.*?\] {indicator}: ([\d\.]+%?)'
            match = re.search(pattern, output)
            if match:
                indicators[indicator] = match.group(1)
        
        # 构建分析提示
        prompt = f"""
        请分析以下期货交易策略的回测结果，并给出改进建议。
        
        ## 回测摘要
        {summary}
        
        ## 关键指标
        """
        
        for key, value in indicators.items():
            prompt += f"- {key}: {value}\n"
        
        prompt += f"""
        ## 交易明细
        {trades}
        
        请提供以下分析：
        1. 策略总体表现评估（收益率、风险、夏普比率等）
        2. 策略优势和不足
        3. 交易模式分析（盈利/亏损模式）
        4. 具体改进建议（参数调整、条件优化、风险控制等）
        5. 如可能，提供特定市场环境下的策略调整建议
        
        请使用专业、简洁的语言进行分析。
        """
        
        return prompt

    def show_results(self) -> str:
        """
        显示回测结果
        
        Returns:
            str: 结果消息
        """
        if not self.backtest_results:
            return "没有可用的回测结果"
        
        if 'analysis' in self.backtest_results:
            return f"回测分析:\n{self.backtest_results['analysis']}"
        elif 'output' in self.backtest_results:
            return f"回测输出:\n{self.backtest_results['output']}"
        
        return "回测结果不完整或格式不正确"

    def fix_strategy(self, error_output: str, strategy_code: str,
                    stream: bool = False, 
                    stream_callback: Callable[[str], None] = None) -> Tuple[bool, str, Optional[str]]:
        """
        修复策略代码中的错误
        
        Args:
            error_output: 错误输出信息
            strategy_code: 当前策略代码
            stream: 是否使用流式输出
            stream_callback: 流式输出回调
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 消息, 修复后的代码)
        """
        try:
            # 从错误输出中提取关键错误信息
            error_lines = error_output.split('\n')
            # 搜索典型的错误模式
            error_info = ""
            for i, line in enumerate(error_lines):
                if "Error" in line or "Exception" in line or "Traceback" in line:
                    # 从这一行前50行开始收集错误信息，以捕获更多上下文
                    error_start = max(0, i-50)  # 增加到50行，捕获更多上下文
                    error_end = min(len(error_lines), i+50)  # 增加收集错误后的信息也到50行
                    error_info = "\n".join(error_lines[error_start:error_end])
                    break
            
            # 如果未找到明确错误模式，但存在数据相关的警告或错误
            if not error_info:
                # 搜索数据请求相关问题
                data_error_keywords = [
                    "未获取到", "服务器内部错误", "API请求", "数据请求开始", 
                    "未能获取任何数据", "警告", "没有数据", "数据为空", 
                    "min() arg is an empty sequence", "empty DataFrame", 
                    "index out of bounds", "IndexError", "没有找到", 
                    "无法获取", "数据不可用", "缺少数据", "empty data",
                    "zero-size array", "无效的日期范围", "期间没有交易数据",
                    "无法下载"
                ]
                data_error_lines = []
                data_error_start = -1
                
                for i, line in enumerate(error_lines):
                    if any(keyword in line for keyword in data_error_keywords):
                        if data_error_start == -1:
                            # 找到第一个数据错误相关的行
                            data_error_start = max(0, i-10)
                        # 持续记录至少到下面20行
                        data_error_lines = error_lines[data_error_start:min(len(error_lines), i+20)]
                
                if data_error_lines:
                    # 如果找到数据相关错误，与上面找到的标准错误合并
                    if error_info:
                        error_info = "\n".join(data_error_lines) + "\n\n" + error_info
                    else:
                        error_info = "\n".join(data_error_lines)
            
            # 如果仍未找到任何错误信息，则使用最后的输出行
            if not error_info:
                # 使用最后50行作为错误信息，以包含更多上下文
                error_info = "\n".join(error_lines[-50:])
            
            # 使用导入的模板并进行格式化
            prompt = prompter.FIX_STRATEGY_TEMPLATE.format(
                error_info=error_info,
                strategy_code=strategy_code
            )
            
            # 添加用户消息
            self.gpt_client.add_message("user", prompt)
            self.conversation_history.append({"role": "user", "content": "策略代码出现错误，请帮我修复"})
            
            # 获取修复方案
            if stream and stream_callback:
                response = self.gpt_client.get_stream_response(stream_callback)
            else:
                response = self.gpt_client.get_response()
            
            # 记录AI响应到对话历史
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # 提取修复后的代码
            fixed_code = self.code_parser.extract_code(response)
            
            if not fixed_code:
                return False, "无法从GPT响应中提取有效的修复代码", None
            
            # 更新当前策略代码
            self.current_strategy_code = fixed_code
            
            # 保存修复后的代码
            with open(self.current_strategy_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            return True, "策略代码已成功修复", fixed_code
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"修复策略时出错: {str(e)}\n{error_info}")
            return False, f"修复策略时出错: {str(e)}", None

    def modify_strategy(self, modification_request: str, 
                       stream: bool = False,
                       stream_callback: Callable[[str], None] = None) -> Tuple[bool, str, str]:
        """
        根据用户请求修改现有策略
        
        Args:
            modification_request: 用户的修改请求
            stream: 是否使用流式响应
            stream_callback: 流式响应的回调函数
            
        Returns:
            Tuple[bool, str, str]: (是否成功, 消息, 修改后的策略代码)
        """
        if not self.current_strategy_code:
            return False, "没有可修改的策略，请先生成一个策略", ""
        
        try:
            # 使用导入的模板并进行格式化
            prompt = prompter.MODIFY_STRATEGY_TEMPLATE.format(
                current_strategy_code=self.current_strategy_code,
                modification_request=modification_request
            )
            
            # 添加用户消息
            self.gpt_client.add_message("user", prompt)
            self.conversation_history.append({"role": "user", "content": f"请修改策略: {modification_request}"})
            
            # 获取GPT响应，支持流式输出
            if stream and stream_callback:
                print("使用流式响应模式修改策略...")
                response = self.gpt_client.get_stream_response(stream_callback)
            else:
                print("使用非流式响应模式修改策略...")
                response = self.gpt_client.get_response()
            
            # 记录AI响应到对话历史
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # 使用CodeParser提取代码
            modified_code = self.code_parser.extract_code(response)
            
            if not modified_code:
                return False, "无法从GPT响应中提取有效的修改后策略代码", ""
            
            # 保存修改后的策略代码
            self.current_strategy_code = modified_code
            
            # 保存修改后的策略文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_strategy_name = f"策略_修改_{timestamp}.py"
            self.current_strategy_path = os.path.join("ai_strategies", self.current_strategy_name)
            
            with open(self.current_strategy_path, 'w', encoding='utf-8') as f:
                f.write(modified_code)
            
            return True, "成功修改策略代码", modified_code
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"修改策略时出错: {str(e)}\n{error_info}")
            return False, f"修改策略时发生错误: {str(e)}\n{error_info}", "" 