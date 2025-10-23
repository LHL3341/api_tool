import base64
import io
import math
import mimetypes
from pathlib import Path
from PIL import Image, ImageOps
from typing import Union, Dict

SHORT_MIN = 32
LONG_MAX = 768

def compute_scale(w: int, h: int) -> float:
    short_side, long_side = min(w, h), max(w, h)
    need_up = short_side < SHORT_MIN
    need_down = long_side > LONG_MAX
    if not need_up and not need_down:
        return 1.0
    up_min = SHORT_MIN / short_side if need_up else 1.0
    down_max = LONG_MAX / long_side if need_down else 1.0
    return min(up_min, down_max)

def resize_image(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = compute_scale(w, h)
    if scale != 1.0:
        new_size = (max(1, int(math.ceil(w * scale))),
                    max(1, int(math.ceil(h * scale))))
        img = img.resize(new_size, Image.BICUBIC)
    return img

def encode_image_to_base64(image: Union[Path, Image.Image, str, Dict]) -> str:
    """
    将图片编码为 Base64 Data URL
    支持类型：
      - Path 或 str (文件路径)
      - PIL.Image.Image
      - dict {'bytes': b'...', 'path': '...'}
    """
    try:
        # 1️⃣ dict 类型
        if isinstance(image, dict):
            if "bytes" in image:
                img = Image.open(io.BytesIO(image["bytes"]))
                # print(1)
            elif "path" in image:
                img = Image.open(Path(image["path"]))
                # print(2)
            else:
                raise TypeError("dict image must contain 'bytes' or 'path'")
        
        # 2️⃣ Path 类型
        elif isinstance(image, Path):
            mime_type, _ = mimetypes.guess_type(image)
            # print(3)
            if not mime_type or not mime_type.startswith("image"):
                raise ValueError(f"Invalid image MIME: {image}")
            with Image.open(image) as img_tmp:
                img = img_tmp.copy()
        
        # 3️⃣ PIL.Image.Image 类型
        elif isinstance(image, Image.Image):
            img = image
            # print(4)
        
        # 4️⃣ str 类型（路径）
        elif isinstance(image, str):
            img = Image.open(Path(image))
            # print(5)
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

        # 统一处理：旋转、缩放、转换为 RGB
        img = ImageOps.exif_transpose(img)
        img = resize_image(img).convert("RGB")

        # 保存到 buffer 并转 base64
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

    except Exception as e:
        raise RuntimeError(f"Failed to encode image: {e}")
