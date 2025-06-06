import os
from dotenv import load_dotenv
import requests
import json
import pandas as pd
import numpy as np
from ssquant.backtest.multi_source_backtest import MultiSourceBacktester
from ssquant.api.strategy_api import StrategyAPI

# 加载环境变量
load_dotenv()

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")  # 添加API URL支持
GPT_MODEL = os.getenv("GPT_MODEL")  # 从环境变量读取模型

# 提示词服务器配置
PROMPT_SERVER_URL = os.getenv("PROMPT_SERVER_URL", "http://127.0.0.1:5000")
PROMPT_API_KEY = os.getenv("PROMPT_API_KEY", "sk-demo-key")  # 默认使用演示密钥

# Backtrader配置
DEFAULT_CASH = 100000  # 默认初始资金
DEFAULT_COMMISSION = 0.001  # 默认交易佣金
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")  # 数据存储目录的绝对路径

# 系统配置
MAX_ITERATIONS = 5  # 自动修复代码的最大尝试次数
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")  # 结果存储目录的绝对路径

# 提示词缓存
_prompt_cache = {}

def get_prompt(prompt_name):
    """
    从服务器获取提示词模板
    
    Args:
        prompt_name: 提示词名称（例如 SYSTEM_PROMPT, GENERATE_STRATEGY_TEMPLATE等）
        
    Returns:
        tuple: (bool, str) - (是否成功从服务器获取, 提示词内容)
    """
    # 检查缓存
    if prompt_name in _prompt_cache:
        return True, _prompt_cache[prompt_name]
    
    # 从服务器获取提示词
    try:
        response = requests.get(
            f"{PROMPT_SERVER_URL}/api/prompts/{prompt_name}",
            headers={"X-API-Key": PROMPT_API_KEY},
            timeout=5
        )
        
        if response.status_code == 200:
            content = response.json().get("content")
            # 添加到缓存并返回
            _prompt_cache[prompt_name] = content
            print(f"从服务器加载提示词: {prompt_name}-->成功!")
            return True, content
        else:
            error = response.json().get("error", "未知错误")
            print(f"获取提示词失败: {error} (状态码: {response.status_code})")
    except Exception as e:
        print(f"请求提示词服务器失败: {e}")
    
    # 使用备用提示词
    print(f"无法获取提示词 {prompt_name}，使用备用提示词")
    return False, _get_fallback_prompt(prompt_name)

def _get_fallback_prompt(prompt_name):
    """获取备用提示词（简化版本）"""
    fallbacks = {
        "SYSTEM_PROMPT": "你是一个专业的期货量化交易策略助手，帮助用户创建、改进和回测期货交易策略。",
        "GENERATE_STRATEGY_TEMPLATE": "请根据以下需求，创建一个适用于期货回测框架的交易策略：{user_query}",
        "MODIFY_STRATEGY_TEMPLATE": "请修改以下策略：{current_strategy_code}，满足需求：{modification_request}",
        "FIX_STRATEGY_TEMPLATE": "修复策略错误：{error_info}，当前代码：{strategy_code}",
        "RESULTS_PROMPT": "分析回测结果：{results}",
        "ERROR_PROMPT": "解决回测错误：{error}"
    }
    return fallbacks.get(prompt_name, "无法找到提示词")

# 通过属性访问的方式方便使用提示词
@property
def SYSTEM_PROMPT():
    success, content = get_prompt("SYSTEM_PROMPT")
    return content

@property
def GENERATE_STRATEGY_TEMPLATE():
    success, content = get_prompt("GENERATE_STRATEGY_TEMPLATE")
    return content

@property
def MODIFY_STRATEGY_TEMPLATE():
    success, content = get_prompt("MODIFY_STRATEGY_TEMPLATE")
    return content

@property
def FIX_STRATEGY_TEMPLATE():
    success, content = get_prompt("FIX_STRATEGY_TEMPLATE")
    return content

@property
def RESULTS_PROMPT():
    success, content = get_prompt("RESULTS_PROMPT")
    return content
    
@property
def ERROR_PROMPT():
    success, content = get_prompt("ERROR_PROMPT")
    return content

# 创建模块级别的PromptManager对象
class PromptManager:
    def get_prompt_with_status(self, prompt_name):
        """获取提示词并返回状态和内容"""
        return get_prompt(prompt_name)
        
    @property
    def SYSTEM_PROMPT(self):
        success, content = get_prompt("SYSTEM_PROMPT")
        return content
    
    @property
    def GENERATE_STRATEGY_TEMPLATE(self):
        success, content = get_prompt("GENERATE_STRATEGY_TEMPLATE")
        return content
    
    @property
    def MODIFY_STRATEGY_TEMPLATE(self):
        success, content = get_prompt("MODIFY_STRATEGY_TEMPLATE")
        return content
    
    @property
    def FIX_STRATEGY_TEMPLATE(self):
        success, content = get_prompt("FIX_STRATEGY_TEMPLATE")
        return content
    
    @property
    def RESULTS_PROMPT(self):
        success, content = get_prompt("RESULTS_PROMPT")
        return content
    
    @property
    def ERROR_PROMPT(self):
        success, content = get_prompt("ERROR_PROMPT")
        return content

# 创建单例实例
prompter = PromptManager()

# 原提示词模板代码已移除，现在通过函数或者prompter.XXX获取