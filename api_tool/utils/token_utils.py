import base64
import io
from PIL import Image
import tiktoken
from api_tool.utils.image_utils import compute_scale
def count_tokens(messages, model: str):
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")

    text_tokens, image_tokens = 0, 0

    for msg in messages:
        content = msg["content"]

        if isinstance(content, str):
            text_tokens += len(enc.encode(content))

        elif isinstance(content, list):
            for part in content:
                if part["type"] == "text":
                    text_tokens += len(enc.encode(part["text"]))
                elif part["type"] == "image_url":
                    url = part["image_url"]["url"]

                    try:
                        # Base64 Data URL
                        if isinstance(url, str) and url.startswith("data:image"):
                            header, encoded = url.split(",", 1)
                            img_bytes = base64.b64decode(encoded)
                            img = Image.open(io.BytesIO(img_bytes))

                        # 文件路径
                        elif isinstance(url, str):
                            img = Image.open(url)

                        # PIL.Image.Image
                        elif isinstance(url, Image.Image):
                            img = url

                        else:
                            raise TypeError(f"Unsupported image type: {type(url)}")

                        # 图像 token 估算
                        w, h = img.size
                        scale = compute_scale(w, h)
                        img_tokens = ((int(h * scale)) // 32) * ((int(w * scale)) // 32)
                        image_tokens += img_tokens

                    except Exception as e:
                        print(f"[yellow]Error counting image tokens: {e}[/yellow]")

    return {"total": text_tokens + image_tokens, "text": text_tokens, "image": image_tokens, "image_size": f'{w}x{h}'}
