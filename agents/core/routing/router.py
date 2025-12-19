import copy
import logging
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent, MultiAgentHub
from qwen_agent.agents import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, ROLE, SYSTEM, Message
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import merge_generate_cfgs

logger = logging.getLogger(__name__)

ROUTER_PROMPT = '''
你是严格的任务路由器，只选择最合适的帮手，不回答用户问题。

可用帮手：
{agent_descs}
可选名称（必须选其一）：{agent_names}

优先级规则：
1) 若明显是延续上一轮（如“继续”“这张图”“接着刚才”），直接选上一次的帮手。
2) 需要多步骤/多能力协作的复杂任务，选“总协调助手”。
3) 图片相关选“多模态助手”；文档相关选“多文件智能助手”。
4) 其余与不确定情况，选“基础对话助手”。

唯一输出格式（只输出一行）：
Call: 帮手名称
不得输出其他内容或解释。
'''


class QwenAgentRouter(FnCallAgent, MultiAgentHub):
    """
    Router:
    - 继承 FnCallAgent 以便用 LLM 做“路由决策”；
    - 继承 MultiAgentHub 管理多个子 Agent；
    - 对外表现为一个 Agent：接收 messages，内部决定调用哪一个子 Agent。
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 files: Optional[List[str]] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 agents: Optional[List[Agent]] = None,
                 rag_cfg: Optional[Dict] = None):
        # MultiAgentHub 相关
        self._agents = agents or []

        agent_descs = '\n'.join([f'- {x.name}: {x.description}' for x in self._agents])
        agent_names_str = ', '.join(self.agent_names)

        # Router 自己是一个 FnCallAgent，使用统一的 llm 配置
        super().__init__(
            function_list=function_list,
            llm=llm,
            system_message=ROUTER_PROMPT.format(
                agent_descs=agent_descs,
                agent_names=agent_names_str
            ),
            name=name,
            description=description,
            files=files,
            rag_cfg=rag_cfg,
        )

        # Router 的 LLM 输出只需要 "Call: xxx" 一行，
        # 可以通过 stop 强制在首行换行时停止（更稳定）。
        self.extra_generate_cfg = merge_generate_cfgs(
            base_generate_cfg=self.extra_generate_cfg,
            new_generate_cfg={'stop': ['\n']}
        )

    # ----------------- MultiAgentHub 相关属性 -----------------

    @property
    def agents(self) -> List[Agent]:
        return self._agents

    @property
    def agent_names(self) -> List[str]:
        return [a.name for a in self._agents]

    # ----------------- 主运行逻辑 -----------------

    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        """
        对外的 run 逻辑：
        1. 先尝试用 Python 级 heuristic：如果明显是“继续上一轮”的指代，就直接沿用上次的 agent；
        2. 否则调用 Router 自己的 LLM，根据 ROUTER_PROMPT 输出一行 "Call: xxx"；
        3. 根据选中的 agent，转发原始 messages 给该 agent；
        4. 对外只 streaming 选中 agent 的输出，不暴露 Router 的中间结果。
        """

        # 1) 先做一层启发式判断：是否直接沿用上一次的 Agent
        heuristic_agent = self._pick_agent_by_heuristic(messages)
        if heuristic_agent and heuristic_agent in self.agent_names:
            selected_agent_name = heuristic_agent
            logger.info(f'[Router] Heuristic choose agent: {selected_agent_name}')
        else:
            # 2) 否则，调用 Router 自己的 LLM 做路由
            messages_for_router: List[Message] = []
            for msg in messages:
                # 把历史中的 assistant 消息补上 `Call: name` 标记，
                # 让 Router 在 prompt 里能看到“上一轮是哪位帮手”。
                try:
                    role = msg[ROLE] if isinstance(msg, dict) else msg.role
                except Exception:
                    role = getattr(msg, 'role', None) or (msg.get('role') if isinstance(msg, dict) else None)

                if role == ASSISTANT:
                    msg = self.supplement_name_special_token(msg)
                messages_for_router.append(msg)

            router_outputs: List[List[Message]] = []
            # OneLog.debug(f"[Router] messages_for_router: {messages_for_router}")

            # 调用父类 FnCallAgent._run，但不对外 yield，只收集最后结果
            for resp in super()._run(messages=messages_for_router, lang=lang, **kwargs):
                router_outputs.append(resp)

            if not router_outputs or not router_outputs[-1]:
                # LLM 异常情况，兜底用第一个 agent
                selected_agent_name = self.agent_names[0]
            else:
                last_msg = router_outputs[-1][-1]
                content = last_msg.content if isinstance(getattr(last_msg, 'content', None), str) else ''
                selected_agent_name = self._parse_call_from_content(content) or self.agent_names[0]

            # logger.info(f'[Router] LLM choose agent: {selected_agent_name}')
            llm_cfg = self.agents[self.agent_names.index(selected_agent_name)].llm
            llm_cfg_info = self._serialize_llm_config(llm_cfg)
            logger.info(f"[Router] LLM choose agent: {selected_agent_name}, llm_cfg详细信息: {llm_cfg_info}")

        # 3) 找到对应的子 Agent
        if selected_agent_name not in self.agent_names:
            # 模型生成了一个不存在的 agent 名称，兜底第一个
            logger.warning(
                f'[Router] Unknown agent name from model: {selected_agent_name}, '
                f'use default: {self.agent_names[0]}'
            )
            selected_agent_name = self.agent_names[0]

        selected_agent = self.agents[self.agent_names.index(selected_agent_name)]

        # 4) 转发消息给子 Agent
        new_messages = copy.deepcopy(messages)
        if new_messages:
            first = new_messages[0]
            first_role = first[ROLE] if isinstance(first, dict) else getattr(first, 'role', None)
            if first_role == SYSTEM:
                # 子 Agent 通常都会有自己的 system_message，这里可以去掉 Router 这一层的 system
                new_messages.pop(0)

        for response in selected_agent.run(messages=new_messages, lang=lang, **kwargs):
            # 给所有 assistant 响应加上 name 字段，方便后续多轮记忆
            for i in range(len(response)):
                if response[i].role == ASSISTANT:
                    response[i].name = selected_agent_name
            # 这才是对外真正 streaming 的内容
            yield response

    # ----------------- 工具方法 -----------------

    @staticmethod
    def supplement_name_special_token(message: Message) -> Message:
        """
        将历史里的 assistant 消息内容前面补上：
        "Call: {name}\n{原始内容}"

        只在 Router 内部使用，不会对用户可见。
        """
        message = copy.deepcopy(message)

        # 兼容 dict / Message 两种形式
        if isinstance(message, dict):
            name = message.get('name')
            content = message.get('content')
        else:
            name = getattr(message, 'name', None)
            content = getattr(message, 'content', None)

        if not name:
            return message

        # content 是 str
        if isinstance(content, str):
            new_content = f'Call: {name}\n{content}'
            if isinstance(message, dict):
                message['content'] = new_content
            else:
                message.content = new_content
            return message

        # content 是 list（富文本）时，找到第一个 text 项进行注入
        if isinstance(content, list):
            for i, item in enumerate(content):
                # item 也可能是 pydantic 模型
                if hasattr(item, 'model_dump'):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    continue

                if 'text' in item_dict:
                    prefix = f'Call: {name}\n'
                    new_text = prefix + item_dict['text']

                    if hasattr(item, 'text'):
                        item.text = new_text
                    elif isinstance(item, dict):
                        item['text'] = new_text
                    content[i] = item
                    break

            if isinstance(message, dict):
                message['content'] = content
            else:
                message.content = content

        return message

    @staticmethod
    def _serialize_llm_config(llm_cfg) -> str:
        """
        尝试多种方式序列化llm_cfg对象为可读的字符串格式

        Args:
            llm_cfg: LLM配置对象

        Returns:
            str: 序列化后的配置信息字符串
        """
        try:
            if hasattr(llm_cfg, 'model_dump_json'):
                return llm_cfg.model_dump_json()
            elif hasattr(llm_cfg, 'model_dump'):
                return str(llm_cfg.model_dump())
            elif hasattr(llm_cfg, 'dict'):
                return str(llm_cfg.dict())
            elif hasattr(llm_cfg, '__dict__'):
                return str(vars(llm_cfg))
            else:
                return str(llm_cfg)
        except Exception as e:
            return f"Error serializing llm_cfg: {e}, type: {type(llm_cfg)}, str: {str(llm_cfg)}"

    @staticmethod
    def _parse_call_from_content(content: str) -> Optional[str]:
        """
        从 Router LLM 的输出中解析出 "Call: xxx" 的 xxx 部分。
        """
        if not content:
            return None
        # 只取第一行，防止模型啰嗦
        first_line = content.strip().split('\n', 1)[0].strip()
        if not first_line.startswith('Call:'):
            return None
        agent_name = first_line[len('Call:'):].strip()
        return agent_name or None

    def _pick_agent_by_heuristic(self, messages: List[Message]) -> Optional[str]:
        """
        一个简单的启发式策略：
        - 找到最近一次 assistant 消息上的 name（上一轮的 agent）；
        - 找到最近一条 user 消息，看看是不是“继续 / 再来一个 / 这张图 / 这个文档”等；
        - 如果是，就直接沿用上一轮 agent，不再调用 Router LLM。
        """
        last_agent_name: Optional[str] = None
        last_user_text: str = ''

        # 从后往前扫描消息
        for msg in reversed(messages):
            # 兼容 dict / Message
            if isinstance(msg, dict):
                role = msg.get('role') or msg.get(ROLE)
                content = msg.get('content')
                name = msg.get('name')
            else:
                role = getattr(msg, 'role', None)
                content = getattr(msg, 'content', None)
                name = getattr(msg, 'name', None)

            if role == ASSISTANT and last_agent_name is None and name:
                last_agent_name = name

            if role == 'user' and not last_user_text:
                if isinstance(content, str):
                    last_user_text = content
                elif isinstance(content, list):
                    texts: List[str] = []
                    for item in content:
                        # dict 富文本
                        if isinstance(item, dict) and 'text' in item:
                            t = item.get('text')
                            if t is not None:
                                texts.append(str(t))
                        # pydantic / 其他对象，带 text 属性
                        elif hasattr(item, 'text'):
                            t = getattr(item, 'text', None)
                            if t is not None:
                                texts.append(str(t))
                    if texts:
                        last_user_text = '\n'.join(texts)

                if last_user_text:
                    break

        if not last_agent_name or not last_user_text:
            return None

        # 一些常见的“延续”关键词，可以按需要扩展
        continuation_keywords = [
            '继续', '接着', '再来一个', '再来一张', '再画一个',
            '再生成一张', '这张图', '这个图', '这张图片', '这个图片',
            '这个文档', '继续翻译', '接着翻译', '按刚才的来'
        ]
        if any(kw in last_user_text for kw in continuation_keywords):
            return last_agent_name

        return None
