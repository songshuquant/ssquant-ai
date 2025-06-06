#!/usr/bin/env python3
"""
AI量化交易助手 - 一键安装脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def print_step(step, message):
    """打印安装步骤"""
    print(f"\n{'='*50}")
    print(f"步骤 {step}: {message}")
    print('='*50)

def install_requirements():
    """安装Python依赖"""
    print_step(1, "安装Python依赖")
    
    try:
        print("正在安装依赖包...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 依赖安装成功!")
            return True
        else:
            print(f"❌ 依赖安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 安装过程出错: {e}")
        return False

def check_ssquant():
    """检查ssquant包是否已安装"""
    print_step(2, "检查ssquant框架")
    
    try:
        import ssquant
        print("✅ ssquant框架已安装")
        return True
    except ImportError:
        print("❌ 未安装ssquant框架")
        print("请运行: pip install ssquant")
        return False

def create_env_template():
    """创建.env模板文件"""
    print_step(3, "创建配置文件")
    
    env_template = """# AI量化交易助手配置文件
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_URL=https://api.openai.com/v1
GPT_MODEL=gpt-4o

# 配置说明:
# 1. 将 sk-your-api-key-here 替换为您的实际API密钥
# 2. 如使用其他API提供商，修改 OPENAI_API_URL
# 3. 根据需要调整模型名称
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_template)
        print("✅ 已创建.env配置模板")
        print("⚠️  请编辑.env文件，填入您的API密钥")
    else:
        print("✅ .env文件已存在")
    
    return True

def test_installation():
    """测试安装是否成功"""
    print_step(4, "测试安装")
    
    try:
        # 测试核心模块导入
        from gpt_client import GPTClient
        from integration_module import IntegrationManager
        print("✅ 核心模块导入成功")
        
        # 测试tiktoken
        import tiktoken
        print("✅ Token管理功能正常")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主安装流程"""
    print("🚀 AI量化交易助手 - 安装向导")
    print("Author: Claude")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    print(f"✅ Python版本: {sys.version}")
    
    # 执行安装步骤
    steps = [
        install_requirements,
        check_ssquant,
        create_env_template,
        test_installation
    ]
    
    for step_func in steps:
        if not step_func():
            print("\n❌ 安装失败，请检查错误信息")
            sys.exit(1)
    
    # 安装成功
    print("\n" + "="*50)
    print("🎉 安装完成!")
    print("="*50)
    print("\n下一步:")
    print("1. 编辑 .env 文件，填入您的API密钥")
    print("2. 运行: python main.py")
    print("\n祝您使用愉快! 🎯")

if __name__ == "__main__":
    main() 