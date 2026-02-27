import asyncio
from typing import Tuple, Optional, Any
from openai import AsyncOpenAI

class StreamHandler:
    """统一处理 LLM 请求（自动适配 Stream 和 Non-Stream）"""

    def __init__(self):
        self.buffer = []

    async def _consume_stream(
        self, agen, timeout: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        内部方法：消费流式响应
        返回: (content_text, reasoning_text)
        """
        collected_text = ""
        reasoning_text = ""
        # self.buffer.clear() # 如需调试可开启 buffer 记录

        async def _consume():
            nonlocal collected_text
            nonlocal reasoning_text
            async for chunk in agen:
                if not getattr(chunk, "choices", None):
                    continue
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", {})

                # 提取内容
                text_piece = getattr(delta, "content", None)
                reasoning_piece = getattr(delta, "reasoning_content", None) # 兼容 DeepSeek API

                if reasoning_piece:
                    reasoning_text += reasoning_piece
                if text_piece:
                    collected_text += text_piece

                # 检查截断
                if getattr(choice, "finish_reason", None) in ["length", "content_filter"]:
                    # print(f"Warning: Model truncated output: {choice.finish_reason}")
                    pass

        if timeout:
            await asyncio.wait_for(_consume(), timeout=timeout)
        else:
            await _consume()

        return collected_text.strip(), reasoning_text.strip()

    def _format_final_response(self, content: str, reasoning: str, config: Any) -> str:
        """
        统一后处理：根据配置决定是否拼接 <think> 标签
        """
        base_url = getattr(config.api, "base_url", "")
        
        # 1. 内部 API (10.140) 特殊逻辑
        if base_url and "10.140" in base_url:
            # 根据你之前的逻辑，内部 API 似乎直接返回 content 即可
            # 如果内部 API 的 reasoning 包含在 content 中，这里不需要额外操作
            return content
        
        # 2. 外部 API (如 DeepSeek, OpenAI)
        else:
            if config.model.thinking and reasoning:
                return f"<think>{reasoning}</think>\n\n{content}"
            else:
                return content

    async def run_completion_with_stream(
        self,
        messages,
        config,
        client: AsyncOpenAI,
        item_idx: int = 0,
        item_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], dict]:
        """
        统一执行入口
        根据 config.model.stream 自动选择请求模式
        返回: (item_idx, item_id, result_dict)
        """
        # 获取配置
        is_stream = getattr(config.model, "stream", True)
        # 优先使用 concurrency 下的超时，如果没有则尝试根目录，默认 120秒
        timeout = getattr(config.concurrency, "timeout", getattr(config, "timeout", 120))

        content = ""
        reasoning = ""

        try:
            if is_stream:
                # ==================== 流式调用 (Streaming) ====================
                response = await client.chat.completions.create(
                    model=config.model.model,
                    messages=messages,
                    stream=True,
                    temperature=config.model.temperature,
                    top_p=config.model.top_p,
                    max_tokens=config.model.max_tokens,
                    timeout=timeout,
                )
                content, reasoning = await self._consume_stream(response, timeout=timeout)

            else:
                # ==================== 非流式调用 (Non-Streaming) ====================
                response = await client.chat.completions.create(
                    model=config.model.model,
                    messages=messages,
                    stream=False,
                    temperature=config.model.temperature,
                    top_p=config.model.top_p,
                    max_tokens=config.model.max_tokens,
                    timeout=timeout,
                )
                
                message = response.choices[0].message
                content = message.content
                # 尝试获取 reasoning_content (标准 OpenAI 对象通常没有这个字段，但 DeepSeek 兼容接口可能有)
                reasoning = getattr(message, "reasoning_content", "") or ""

            # ==================== 统一格式化输出 ====================
            final_resp = self._format_final_response(content, reasoning, config)
            
            # 返回统一结构
            return item_idx, item_id, {"response": final_resp.strip()}

        except asyncio.TimeoutError:
            return item_idx, item_id, {"error": f"Timeout after {timeout}s"}
        except Exception as e:
            # print(f"⚠️ Exception in request for item #{item_idx}: {e}")
            return item_idx, item_id, {"error": str(e)}