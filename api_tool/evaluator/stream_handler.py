import asyncio
from typing import Tuple, Optional
from openai import AsyncOpenAI


class StreamHandler:
    """统一处理 LLM 异步流式输出"""

    def __init__(self):
        self.buffer = []

    async def _consume_stream(
        self, agen, timeout: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        异步消费 OpenAI 流式响应，支持整体超时
        返回: (collected_text, raw_stream)
        """
        collected_text = ""
        self.buffer.clear()

        async def _consume():
            nonlocal collected_text
            async for chunk in agen:
                self.buffer.append(str(chunk) + "\n")

                if not getattr(chunk, "choices", None):
                    continue
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", {})
                # print(delta)

                text_piece = getattr(delta, "content", None)
                if text_piece:
                    collected_text += text_piece

                if getattr(choice, "finish_reason", None) in ["length", "content_filter"]:
                    raise ValueError(
                        f"Output truncated by model (finish_reason={choice.finish_reason})"
                    )

        if timeout:
            await asyncio.wait_for(_consume(), timeout=timeout)
        else:
            await _consume()

        return collected_text.strip(), "".join(self.buffer)

    async def run_completion_with_stream(
        self,
        messages,
        config,
        client: AsyncOpenAI,
        item_idx: int = 0,
        item_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], str, str, dict]:
        """
        高层接口，统一处理异步流式请求
        返回: (item_idx, item_id, metric, mode, parsed_result)
        """
        try:
            # 异步客户端
            response = await client.chat.completions.create(
                model=config.model.model,
                messages=messages,
                stream=True,
                temperature=config.model.temperature,
                top_p=config.model.top_p,
                max_tokens=config.model.max_tokens,
                timeout=getattr(config, "timeout", None),
            )

            collected_text, _ = await self._consume_stream(
                response, timeout=getattr(config, "timeout", None)
            )

            # ===== 后处理 thinking 标签 =====
            base_url = getattr(config.api, "base_url", "")
            model_name = getattr(config.model, "model", "")
            if base_url and "10.140" in base_url:
                # 内部 API
                if config.model.thinking:
                    final_resp = collected_text
                else:
                    parts = collected_text.split("</think>\n\n")
                    final_resp = parts[1] if len(parts) > 1 else collected_text
            else:
                # 外部 API
                if config.model.thinking:
                    final_resp = "<think>" + collected_text + "</think>\n\n" + collected_text
                else:
                    final_resp = collected_text

            parsed_result = {"response": final_resp.strip()}
            return item_idx, item_id, parsed_result

        except asyncio.TimeoutError:
            return item_idx, item_id, {"error": f"Timeout after {config.concurrency.timeout}s"}
        except Exception as e:
            print(f"⚠️ Exception in stream for item #{item_idx}: {e}")
            return item_idx, item_id, {"error": str(e)}
