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
        # 查找三个反引号包围的代码块，可能包含语言标识如```python
        code_blocks = re.findall(r'```(?:python)?(.*?)```', text, re.DOTALL)
        
        if code_blocks:
            # 找到了标准代码块
            extracted_code = code_blocks[0].strip()
            # 验证提取的代码
            if CodeParser._validate_code(extracted_code):
                return extracted_code
        
        # 如果没有找到标准代码块或标准代码块验证失败，尝试查找可能的非标准格式代码
        # 例如，寻找连续的缩进行，这可能是代码
        lines = text.split('\n')
        indented_blocks = []
        current_block = []
        in_block = False
        
        for line in lines:
            # 检查行是否以空格或制表符开始，或者是Python代码常见的起始关键字
            if line.strip() and (line.startswith((' ', '\t')) or line.startswith(('import ', 'from ', 'class ', 'def '))):
                if not in_block:
                    in_block = True
                current_block.append(line)
            else:
                if in_block and line.strip() == '':
                    # 保留代码块内的空行
                    current_block.append(line)
                elif in_block:
                    # 代码块结束
                    indented_blocks.append('\n'.join(current_block))
                    current_block = []
                    in_block = False
        
        # 不要忘记处理最后一个块
        if current_block:
            indented_blocks.append('\n'.join(current_block))
        
        if indented_blocks:
            # 筛选有效的代码块
            valid_blocks = []
            for block in indented_blocks:
                if len(block) > 50 and CodeParser._validate_code(block):  # 设置最小长度阈值，避免误提取
                    valid_blocks.append(block)
            
            if valid_blocks:
                # 优先选择包含 "if __name__ == "__main__":" 的完整代码块
                main_blocks = [b for b in valid_blocks if "if __name__ == \"__main__\":" in b or "if __name__ == '__main__':" in b]
                if main_blocks:
                    return max(main_blocks, key=len)
                
                # 其次选择包含 "def strategy_function" 或 "def initialize" 的代码块
                strategy_blocks = [b for b in valid_blocks if "def strategy_function" in b or "def initialize" in b]
                if strategy_blocks:
                    return max(strategy_blocks, key=len)
                
                # 其次选择最长的代码块
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