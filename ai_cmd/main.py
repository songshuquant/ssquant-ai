"""
AI量化交易助手 - 主程序

集成AI助手与期货回测框架，提供用户界面与交互功能
"""

import os
import sys
import re
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print
from rich.prompt import Prompt, Confirm

# 导入集成模块
# 使用显式相对导入
from integration_module import IntegrationManager

console = Console()

def parse_symbol_date_command(command: str):
    """从命令中解析交易标的和日期范围"""
    symbol_match = re.search(r'标的(?:是|为)?[\s:：]*([A-Za-z0-9\.]+)', command)
    start_date_match = re.search(r'开始(?:日期|时间)(?:是|为)?[\s:：]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', command)
    end_date_match = re.search(r'(?:结束|截止)(?:日期|时间)(?:是|为)?[\s:：]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', command)
    period_match = re.search(r'(?:周期|K线)(?:是|为)?[\s:：]*([0-9]+[mhdwMy]|[1]?[0-9]?[dhwMy])', command)
    
    symbol = symbol_match.group(1) if symbol_match else None
    
    start_date = None
    if start_date_match:
        start_date = start_date_match.group(1).replace('/', '-')
    
    end_date = None
    if end_date_match:
        end_date = end_date_match.group(1).replace('/', '-')
    
    period = period_match.group(1) if period_match else None
    
    return symbol, start_date, end_date, period

def main():
    """主程序入口"""
    console.print(Panel.fit(
        "[bold green]松鼠QuantAI策略开发助手[/bold green]\n"
        "使用自然语言描述您的交易策略，系统将自动编写代码并执行回测。",
        title="欢迎使用",
        border_style="green"
    ))
    console.print("- 直接输入您的策略需求开始对话\n")
    # 初始化集成管理器
    manager = IntegrationManager()
    
    # 设置默认参数（内部使用，不再显示给用户）
    symbol = 'rb888'
    start_date = '2024-01-01'
    end_date = '2025-12-31'
    period = '1d'
    
    # 默认启用流式输出
    use_stream = True
    console.print("[green]已默认启用流式输出，可使用/nostream关闭[/green]")
    
    # 主交互循环
    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]>>[/bold blue]")
            
            # 处理特殊命令
            if user_input.lower() == '/quit':
                if Confirm.ask("确定要退出程序吗?"):
                    break
                else:
                    continue
            
            elif user_input.lower() == '/reset':
                manager.reset_conversation()
                console.print("[green]已重置对话上下文，但保留了当前策略[/green]")
                continue
            
            elif user_input.lower() == '/save':
                filename = Prompt.ask("请输入保存的文件名 (默认使用时间戳)")
                result = manager.save_strategy(filename if filename else None)
                console.print(f"[green]{result}[/green]")
                continue
            
            elif user_input.lower() == '/run':
                if not manager.current_strategy_code:
                    console.print("[yellow]没有可运行的策略，请先生成策略[/yellow]")
                    continue
                
                console.print("[green]正在运行回测...[/green]")
                
                # 创建流式输出回调函数
                def stream_output(text_chunk):
                    # 直接打印文本块，不带换行符
                    console.print(text_chunk, end="")
                
                # 设置流式输出
                if use_stream:
                    # 使用流式输出运行回测
                    success, message, results = manager.run_backtest(
                        stream=True,
                        stream_callback=stream_output
                    )
                    # 打印换行符，确保后续输出不在同一行
                    console.print("")
                else:
                    # 使用非流式输出运行回测
                    success, message, results = manager.run_backtest()
                
                if success:
                    console.print("[green]回测成功完成[/green]")
                else:
                    console.print(f"[red]回测失败: {message}[/red]")
                
                continue
            
            elif user_input.lower() == '/results':
                result = manager.show_results()
                console.print(f"[green]{result}[/green]")
                continue
                
            elif user_input.lower() == '/stream':
                use_stream = True
                console.print("[green]已启用流式输出[/green]")
                continue
                
            elif user_input.lower() == '/nostream':
                use_stream = False
                console.print("[yellow]已关闭流式输出[/yellow]")
                continue
            
            elif user_input.lower() == '/debug':
                console.print("[green]已启用调试模式，将显示详细日志[/green]")
                continue
                
            elif user_input.lower() == '/nodebug':
                console.print("[yellow]已关闭调试模式[/yellow]")
                continue
            
            elif user_input.lower().startswith('/modify'):
                # 提取修改请求
                if len(user_input) > 7:  # 如果命令后面有内容
                    modification_request = user_input[7:].strip()
                    if not modification_request:
                        modification_request = Prompt.ask("请输入策略修改要求")
                else:
                    modification_request = Prompt.ask("请输入策略修改要求")
                
                if not manager.current_strategy_code:
                    console.print("[yellow]没有可修改的策略，请先生成策略[/yellow]")
                    continue
                
                console.print("\n[dim]正在修改策略...[/dim]")
                
                # 创建流式输出回调函数
                def stream_output(text_chunk):
                    # 直接打印文本块，不带换行符
                    console.print(text_chunk, end="")
                
                # 修改策略代码
                if use_stream:
                    # 使用流式输出
                    success, message, modified_code = manager.modify_strategy(
                        modification_request,
                        stream=True, 
                        stream_callback=stream_output
                    )
                    # 打印换行符，确保后续输出不在同一行
                    console.print("")
                else:
                    # 使用非流式输出
                    success, message, modified_code = manager.modify_strategy(
                        modification_request
                    )
                
                if success:
                    # 显示修改后的策略代码
                    console.print("[green]成功修改策略代码:[/green]")
                    console.print(Panel(modified_code, title="修改后的策略代码", border_style="green"))
                    
                    # 询问是否运行回测
                    if Confirm.ask("是否立即运行回测?"):
                        console.print("[green]正在运行回测...[/green]")
                        
                        if use_stream:
                            # 使用流式输出运行回测
                            success, message, results = manager.run_backtest(
                                stream=True,
                                stream_callback=stream_output
                            )
                            # 打印换行符，确保后续输出不在同一行
                            console.print("")
                        else:
                            # 使用非流式输出运行回测
                            success, message, results = manager.run_backtest()
                        
                        if success:
                            console.print("[green]回测成功完成[/green]")
                        else:
                            console.print(f"[red]回测失败: {message}[/red]")
                else:
                    console.print(f"[red]修改策略失败: {message}[/red]")
                
                continue
            
            elif user_input.lower().startswith('/set'):
                symbol_new, start_date_new, end_date_new, period_new = parse_symbol_date_command(user_input)
                
                if not any([symbol_new, start_date_new, end_date_new, period_new]):
                    console.print("[yellow]无法识别参数。格式: /set 标的:rb888 开始日期:2024-01-01 结束日期:2025-12-31 周期:1d[/yellow]")
                    continue
                
                # 使用现有值作为默认值
                symbol = symbol_new or symbol
                start_date = start_date_new or start_date
                end_date = end_date_new or end_date
                period = period_new or period
                
                console.print(f"[green]交易参数已更新：标的={symbol}, 开始日期={start_date}, 结束日期={end_date}, 周期={period}[/green]")
                continue
            
            # 处理普通用户输入 - 根据当前状态判断是生成新策略还是修改现有策略
            if manager.current_strategy_code and not user_input.startswith(('生成', '创建', '开发', '设计', '使用', '写一个', '编写')):
                # 如果已有策略，且用户输入不是明确要求生成新策略，视为修改请求
                console.print("\n[dim]正在修改现有策略...[/dim]")
                
                # 创建流式输出回调函数
                def stream_output(text_chunk):
                    # 直接打印文本块，不带换行符
                    console.print(text_chunk, end="")
                
                # 修改策略代码
                if use_stream:
                    # 使用流式输出
                    success, message, modified_code = manager.modify_strategy(
                        user_input, 
                        stream=True, 
                        stream_callback=stream_output
                    )
                    # 打印换行符，确保后续输出不在同一行
                    console.print("")
                else:
                    # 使用非流式输出
                    success, message, modified_code = manager.modify_strategy(
                        user_input
                    )
                
                if success:
                    # 显示修改后的策略代码
                    console.print("[green]成功修改策略代码:[/green]")
                    console.print(Panel(modified_code, title="修改后的策略代码", border_style="green"))
                    
                    # 询问是否运行回测
                    if Confirm.ask("是否立即运行回测?"):
                        console.print("[green]正在运行回测...[/green]")
                        
                        if use_stream:
                            # 使用流式输出运行回测
                            success, message, results = manager.run_backtest(
                                stream=True,
                                stream_callback=stream_output
                            )
                            # 打印换行符，确保后续输出不在同一行
                            console.print("")
                        else:
                            # 使用非流式输出运行回测
                            success, message, results = manager.run_backtest()
                        
                        if success:
                            console.print("[green]回测成功完成[/green]")
                        else:
                            console.print(f"[red]回测失败: {message}[/red]")
                else:
                    console.print(f"[red]修改策略失败: {message}[/red]")
            else:
                # 生成新策略
                console.print("\n[dim]正在生成策略...[/dim]")
                
                # 创建流式输出回调函数
                def stream_output(text_chunk):
                    # 直接打印文本块，不带换行符
                    console.print(text_chunk, end="")
                
                # 生成策略代码
                if use_stream:
                    # 使用流式输出
                    success, message, strategy_code = manager.generate_strategy(
                        user_input,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        period=period,
                        stream=True, 
                        stream_callback=stream_output
                    )
                    # 打印换行符，确保后续输出不在同一行
                    console.print("")
                else:
                    # 使用非流式输出
                    success, message, strategy_code = manager.generate_strategy(
                        user_input,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        period=period
                    )
                
                if success:
                    # 显示策略代码
                    console.print("[green]成功生成策略代码:[/green]")
                    console.print(Panel(strategy_code, title="生成的策略代码", border_style="green"))
                    
                    # 自动保存策略
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"策略_{timestamp}.py"
                    save_result = manager.save_strategy(filename)
                    console.print(f"[green]{save_result}[/green]")
                    
                    # 询问是否运行回测
                    if Confirm.ask("是否立即运行回测?"):
                        console.print("[green]正在运行回测...[/green]")
                        
                        if use_stream:
                            # 使用流式输出运行回测
                            success, message, results = manager.run_backtest(
                                stream=True,
                                stream_callback=stream_output
                            )
                            # 打印换行符，确保后续输出不在同一行
                            console.print("")
                        else:
                            # 使用非流式输出运行回测
                            success, message, results = manager.run_backtest()
                        
                        if success:
                            console.print("[green]回测成功完成[/green]")
                        else:
                            console.print(f"[red]回测失败: {message}[/red]")
                else:
                    console.print(f"[red]生成策略失败: {message}[/red]")
                
        except KeyboardInterrupt:
            if Confirm.ask("\n检测到中断，是否退出程序?"):
                break

if __name__ == "__main__":
    main() 