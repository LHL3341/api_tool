import re
from pathlib import Path
from typing import Dict, Any, Tuple
from api_tool.utils.image_utils import encode_image_to_base64
from api_tool.utils.prompt_utils import fill_prompt
from api_tool.evaluator.base import BaseEvaluator
from api_tool.evaluator.stream_handler import StreamHandler
from api_tool.utils.token_utils import count_tokens
from api_tool.utils.io_utils import load_dataset_skip_existing, append_jsonl
from api_tool.utils.progress_utils import create_progress_bar
from rich.console import Console
import asyncio
import traceback
from queue import Queue
import json

console = Console(force_terminal=True)

class LLMEvaluator(BaseEvaluator):
    """LLM-as-Judge 主评估器"""

    def __init__(self, config):
        super().__init__(config)
        self.client = config.api.get_openai_client(timeout=config.concurrency.timeout)
        self.stream_handler = StreamHandler()

        # 输出路径
        self.output_dir = Path(config.io.output_dir)
        self.output_file = self.output_dir / "results.jsonl"

        # 并发控制
        self.concurrent_limit = config.concurrency.concurrency
        self.semaphore = asyncio.Semaphore(self.concurrent_limit)

        # 模型参数
        self.model_name = config.model.model
        self.temperature = config.model.temperature
        self.top_p = config.model.top_p
        self.max_tokens = config.model.max_tokens
        self.stream = config.model.stream
        self.thinking = config.model.thinking

        # 请求计数
        self.current_requests = 0
        self.total_requests_sent = 0
        self.total_requests_success = 0

    async def run(self):
        dataset = load_dataset_skip_existing(self.config.io.input_file, self.config.io.output_dir, self.config.io.key_name)
        if not dataset:
            console.print("[yellow]⚠️ No data loaded. Check your input_file path.[/yellow]")
            return

        self.prompt_template = Path(self.config.io.prompt_file).read_text(encoding="utf-8")
        first_item = dataset[0]
        messages, prompt = self.build_messages(first_item, self.prompt_template)

        # ✅ 打印预览
        print("\n==== Formatted Prompt ====\n")
        print(prompt)
        print("\n==== Messages ====\n")
        print(messages)

        results = []
        sem = asyncio.Semaphore(self.concurrent_limit)

        # 直接创建 progress（utils 内部会把 RequestsStatusColumn 自动加入）
        progress = create_progress_bar(self)  # 传 self 会自动插入请求状态列
        overall_task = progress.add_task("[cyan]Evaluating dataset...", total=len(dataset))

        # result_queue = Queue()
        # output_file = self.output_file

        # ✅ 异步安全写入协程
        async def writer():
            """持续从队列写入 JSONL 文件，防止并发冲突"""
            with open(output_file, "a", encoding="utf-8") as f:
                while True:
                    item = await result_queue.get()
                    if item is None:
                        break
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    f.flush()
                    result_queue.task_done()

        # writer_task = asyncio.create_task(writer())

        async def process_item(item):
            async with sem:
                self.current_requests += 1
                self.total_requests_sent += 1
                try:

                    messages, prompt = self.build_messages(item, self.prompt_template)

                    success, response_text = await self._call_model(messages)
                    if not success:
                        console.print(f"[yellow]⚠️ Skipped due to error: {response_text}[/yellow]")
                        return None
                        
                    key_name = self.config.io.key_name
                    result = {
                        key_name: item[key_name],
                        # "prompt": prompt,
                        "response": response_text,
                        "template": self.config.io.prompt_file,
                    }
                    # if not "10.140." in self.config.api.base_url:
                    #     result["token_usage"] = count_tokens(messages, self.model_name)

                    self.total_requests_success += 1
                    return result
                except Exception as e:
                    console.print(f"[red]Error processing item {item.get('id')}: {e}[/red]")
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                    return None
                finally:
                    self.current_requests -= 1

        with progress:
            tasks = [process_item(item) for item in dataset]
            for coro in asyncio.as_completed(tasks):
                res = await coro
                progress.update(overall_task, advance=1)
                if res:
                    # await result_queue.put(res)
                    results.append(res)
                    append_jsonl(res, self.output_file)

        # await result_queue.put(None)
        # await writer_task
        console.print(f"[bold blue]✅ Evaluation completed. Results saved to {self.output_file}[/bold blue]")

    def build_messages(self, item: Dict[str, Any], prompt_template: str) -> Tuple[list, str]:
        """
        构建 messages 输入：
        - 根据 prompt_template 中的占位符动态替换
        - 当模板中包含 {image} / {images} / {image_path} / {image_paths} 时，
        自动构建图像消息，否则仅为纯文本。
        """
        import traceback
        image_fields = ["image", "images", "image_path", "image_paths"]
        used_image_keys = [key for key in image_fields if f"{{{key}}}" in prompt_template]

        # 1️⃣ 先准备一个只包含非图像字段的 item，用于填充模板
        text_item = {k: v for k, v in item.items() if k not in used_image_keys}

        # 2️⃣ 填充模板
        formatted_prompt = fill_prompt(prompt_template, text_item)
        # print(formatted_prompt)

        if self.config.api.base_url and "10.140" in self.config.api.base_url and not self.thinking:
            formatted_prompt += "/no_think"

        # 3️⃣ 处理图像字段
        image_urls = []
        for key in used_image_keys:
            if key not in item or not item[key]:
                continue

            value = item[key]
            try:
                # 兼容 list / 单图
                if isinstance(value, list):
                    for v in value:
                        image_urls.append(encode_image_to_base64(v))
                else:
                    image_urls.append(encode_image_to_base64(value))
            except Exception as e:
                console.print(f"[yellow]{type(e).__name__}: {e}[/yellow]")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
                raise

        # 4️⃣ 构建 messages
        if image_urls:
            content_blocks = [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
            content_blocks.append({"type": "text", "text": formatted_prompt})
            messages = [{"role": "user", "content": content_blocks}]
        else:
            messages = [{"role": "user", "content": formatted_prompt}]
        # print(messages)

        return messages, formatted_prompt


    async def _call_model(self, messages: list) -> Tuple[str, str]:
        """调用模型 API（流式），返回 (response_text, raw_stream)"""
        item_idx, item_id, result = await self.stream_handler.run_completion_with_stream(
            messages=messages,
            item_idx=0,
            item_id=None,
            config=self.config,
            client=self.client
        )
        if "error" in result:
            return False, result["error"]
        return True, result.get("response", "")
