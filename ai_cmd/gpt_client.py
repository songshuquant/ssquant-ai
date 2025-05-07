from openai import OpenAI
from typing import List, Dict, Any, Generator, Callable
# 使用绝对导入
import config

class GPTClient:
    """
    GPT客户端类，负责与OpenAI API或兼容API交互
    """
    
    def __init__(self):
        """初始化GPT客户端"""
        self.api_key = config.OPENAI_API_KEY
        self.api_url = config.OPENAI_API_URL
        self.model = config.GPT_MODEL
        success, content = config.get_prompt("SYSTEM_PROMPT")
        self.system_prompt = content
        if success:
            print("成功从服务器加载系统提示词")
        else:
            print("从服务器加载系统提示词失败，使用备用提示词")
        self.messages = [{"role": "system", "content": self.system_prompt}]
        
        # 使用新的OpenAI客户端方式
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )
            
    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到对话历史
        
        Args:
            role: 消息角色（"user", "assistant", "system"）
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})
    
    def get_response(self) -> str:
        """
        从API获取响应（非流式）
        
        Returns:
            str: 模型生成的响应文本
        """
        try:
            # 使用新的客户端方式调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                stream=False
            )
            
            # 获取响应内容
            content = response.choices[0].message.content
            self.add_message("assistant", content)
            return content
            
        except Exception as e:
            error_msg = f"调用API时出错: {e}"
            print(error_msg)
            return f"调用模型出错: {str(e)}\n\n请检查:\n1. API URL是否正确\n2. 模型名称是否正确\n3. API密钥是否有效"
    
    def get_stream_response(self, callback: Callable[[str], None] = None) -> str:
        """
        从API获取流式响应，并通过回调函数实时返回文本块
        
        Args:
            callback: 处理每个文本块的回调函数
            
        Returns:
            str: 完整的响应文本
        """
        try:
            # 使用流式模式调用API
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                stream=True
            )
            
            # 收集完整响应
            collected_content = ""
            
            # 处理流式响应
            for chunk in stream:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    content_chunk = chunk.choices[0].delta.content
                    if content_chunk:
                        collected_content += content_chunk
                        # 如果提供了回调函数，调用它处理这个文本块
                        if callback:
                            callback(content_chunk)
            
            # 将完整响应添加到对话历史
            self.add_message("assistant", collected_content)
            return collected_content
            
        except Exception as e:
            error_msg = f"调用流式API时出错: {e}"
            print(error_msg)
            error_response = f"调用模型出错: {str(e)}\n\n请检查:\n1. API URL是否正确\n2. 模型名称是否正确\n3. API密钥是否有效"
            if callback:
                callback(error_response)
            return error_response
    
    def clear_conversation(self) -> None:
        """清空对话历史，仅保留系统提示"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取当前对话历史
        
        Returns:
            List[Dict[str, str]]: 对话历史列表
        """
        return self.messages
    
    def save_conversation(self, filename: str) -> bool:
        """
        保存当前对话历史到文件
        
        Args:
            filename: 保存的文件名
            
        Returns:
            bool: 是否保存成功
        """
        try:
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存对话历史失败: {e}")
            return False
    
    def load_conversation(self, filename: str) -> bool:
        """
        从文件加载对话历史
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否加载成功
        """
        try:
            import json
            with open(filename, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
            return True
        except Exception as e:
            print(f"加载对话历史失败: {e}")
            return False
    
    def report_error(self, error_message: str, stream: bool = False, callback: Callable[[str], None] = None) -> str:
        """
        向GPT报告错误并获取修复建议
        
        Args:
            error_message: 错误信息
            stream: 是否使用流式响应
            callback: 流式响应的回调函数
            
        Returns:
            str: GPT的修复建议
        """
        success, error_prompt_template = config.get_prompt("ERROR_PROMPT")
        if success:
            print("成功从服务器加载ERROR_PROMPT")
        else:
            print("从服务器加载ERROR_PROMPT失败，使用备用提示词")
        
        error_prompt = error_prompt_template.format(error=error_message)
        self.add_message("user", error_prompt)
        
        if stream and callback:
            return self.get_stream_response(callback)
        else:
            return self.get_response()
    
    def report_results(self, results: str, stream: bool = False, callback: Callable[[str], None] = None) -> str:
        """
        向GPT报告回测结果并获取分析
        
        Args:
            results: 回测结果数据
            stream: 是否使用流式响应
            callback: 流式响应的回调函数
            
        Returns:
            str: GPT的结果分析
        """
        success, results_prompt_template = config.get_prompt("RESULTS_PROMPT")
        if success:
            print("成功从服务器加载RESULTS_PROMPT")
        else:
            print("从服务器加载RESULTS_PROMPT失败，使用备用提示词")
        
        results_prompt = results_prompt_template.format(results=results)
        self.add_message("user", results_prompt)
        
        if stream and callback:
            return self.get_stream_response(callback)
        else:
            return self.get_response() 