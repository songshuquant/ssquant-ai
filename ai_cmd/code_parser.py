import re
from typing import Optional, Tuple

class CodeParser:
    """
    代码解析类，用于从GPT响应中提取Python代码
    """
    
    @staticmethod
    def extract_code(text: str) -> Optional[str]:
        """
        从文本中提取Python代码块
        
        Args:
            text: 包含可能代码块的文本
            
        Returns:
            Optional[str]: 提取出的代码，如果没有找到则返回None
        """
        # 首先尝试匹配标准的代码块格式（包括可能的语言标识）
        code_block_patterns = [
            r'```python\s*(.*?)```',  # python标识的代码块
            r'```py\s*(.*?)```',      # py标识的代码块
            r'```\s*(.*?)```',        # 无标识的代码块
            r'`{3,}(.*?)`{3,}'        # 任意数量反引号的代码块
        ]
        
        for pattern in code_block_patterns:
            code_blocks = re.findall(pattern, text, re.DOTALL)
            if code_blocks:
                # 如果找到多个代码块，选择最长的一个
                extracted_code = max(code_blocks, key=len).strip()
                if CodeParser._validate_code(extracted_code):
                    return extracted_code
        
        # 如果没有找到标准代码块，尝试查找可能的非标准格式代码
        lines = text.split('\n')
        code_blocks = []
        current_block = []
        in_block = False
        
        for line in lines:
            stripped_line = line.strip()
            # 检查是否是代码行的开始
            if not in_block and (
                stripped_line.startswith(('import ', 'from ', 'class ', 'def ', '#', 'global ')) or
                line.startswith((' ', '\t'))
            ):
                in_block = True
                current_block = []
            
            # 如果在代码块中
            if in_block:
                # 如果遇到明显的非代码行（如markdown格式的文本），结束当前块
                if stripped_line and not line.startswith((' ', '\t')) and not any(
                    stripped_line.startswith(x) for x in 
                    ('import ', 'from ', 'class ', 'def ', '#', '@', 'if ', 'for ', 'while ', 'try:', 'else:', 'elif ', 'except:', 'finally:', 'with ', 'async ', 'await ', 'return ', 'yield ', 'raise ', 'assert ', 'global ', 'nonlocal ', 'pass', 'break', 'continue', ')', ']', '}', '"""', "'''")
                ):
                    if current_block:
                        code_blocks.append('\n'.join(current_block))
                    current_block = []
                    in_block = False
                else:
                    current_block.append(line)
            
            # 处理空行
            if in_block and not stripped_line:
                current_block.append(line)
        
        # 添加最后一个块
        if current_block:
            code_blocks.append('\n'.join(current_block))
        
        # 验证并选择最佳代码块
        valid_blocks = []
        for block in code_blocks:
            if len(block.strip()) > 50 and CodeParser._validate_code(block):
                valid_blocks.append(block)
        
        if valid_blocks:
            # 优先选择包含完整程序结构的代码块
            main_blocks = [b for b in valid_blocks if "if __name__ == \"__main__\":" in b or "if __name__ == '__main__':" in b]
            if main_blocks:
                return max(main_blocks, key=len)
            
            # 其次选择包含策略函数的代码块
            strategy_blocks = [b for b in valid_blocks if "def strategy_function" in b or "def initialize" in b]
            if strategy_blocks:
                return max(strategy_blocks, key=len)
            
            # 最后选择最长的有效代码块
            return max(valid_blocks, key=len)
        
        return None
    
    @staticmethod
    def _validate_code(code: str) -> bool:
        """
        简单验证提取的代码是否可能是有效的Python代码
        
        Args:
            code: 提取的代码
            
        Returns:
            bool: 代码是否可能有效
        """
        # 检查是否包含常见的Python语法元素
        if not any(keyword in code for keyword in ['def ', 'class ', 'import ', 'from ']):
            return False
        
        # 检查缩进是否一致
        lines = code.split('\n')
        indentation_levels = set()
        for line in lines:
            if line.strip():  # 跳过空行
                indent = len(line) - len(line.lstrip())
                indentation_levels.add(indent)
        
        # 正常的Python代码通常有多个缩进级别
        if len(indentation_levels) < 1:
            return False
        
        # 检查括号是否平衡
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        for char in code:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack or brackets[stack.pop()] != char:
                    return False
        
        # 检查是否包含主函数
        if "if __name__ == \"__main__\":" in code or "if __name__ == '__main__':" in code:
            return True
        
        # 检查是否包含策略函数或策略类相关代码
        if "def strategy_function" in code or "def initialize" in code:
            return True
        
        # 兼容旧的类风格 - 检查是否包含策略类相关代码
        if "class" in code and "Strategy" in code:
            return True
            
        # 如果代码长度足够长，可能是有效的
        if len(code) > 200:
            return True
            
        return False 