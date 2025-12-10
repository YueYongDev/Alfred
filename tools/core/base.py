from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from qwen_agent.tools import BaseTool

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class QwenAgentBaseTool(BaseTool):
    """Base tool class for Qwen Agent with logging capabilities."""
    
    def __init__(self):
        super().__init__()
        self.tool_name = self.__class__.__name__
    
    def call(self, params: Dict[str, Any], **kwargs: Any) -> str:
        """Override the call method to add logging."""
        start_time = time.time()
        
        # 记录工具调用开始
        logger.info(f"Tool {self.tool_name} called with params: {json.dumps(params, ensure_ascii=False)}")
        
        try:
            # 执行实际的工具逻辑
            result = self._execute_tool(params, **kwargs)
            
            # 记录成功执行
            execution_time = time.time() - start_time
            logger.info(f"Tool {self.tool_name} executed successfully in {execution_time:.2f}s")
            logger.info(f"Tool {self.tool_name} returned: {result}")
            return result
            
        except Exception as e:
            # 记录执行错误
            execution_time = time.time() - start_time
            logger.error(f"Tool {self.tool_name} failed after {execution_time:.2f}s with error: {str(e)}")
            raise
    
    def _execute_tool(self, params: Dict[str, Any], **kwargs: Any) -> str:
        """
        Subclasses should implement this method with their actual tool logic.
        This method is called by the parent call() method with logging around it.
        """
        raise NotImplementedError("_execute_tool method must be implemented by subclasses")