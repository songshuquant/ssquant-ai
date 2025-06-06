"""
AI助手模块初始化文件
"""

# 移除不存在的路径导入
# from src.config.path_config import setup_python_path

# 不再需要调用setup_python_path函数
# setup_python_path()

# 版本信息
__version__ = "1.0.0"

# 导入路径修复模块，确保能正确加载模块
import os
import sys

# 获取当前文件所在目录的上级目录(项目根目录)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 删除旧的回测框架路径
old_path = r"d:\回测框架"
if old_path in sys.path:
    sys.path.remove(old_path)

# 添加当前项目路径到sys.path的最前面
if current_dir not in sys.path:
    sys.path.insert(0, current_dir) 