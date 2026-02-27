from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml
from openai import AsyncOpenAI
import httpx


# =========================
# 🧩 API 配置
# =========================
@dataclass
class APIConfig:
    """API 相关配置"""
    api_key: str
    base_url: Optional[str] = None

    def get_openai_client(self, timeout: int = 120) -> AsyncOpenAI:
        """返回异步 OpenAI 客户端实例（兼容内部与外部 API）"""
        if not self.api_key:
            raise ValueError("Missing api_key in APIConfig")

        kwargs = {
            "api_key": self.api_key,
            "timeout": timeout,
        }

        if self.base_url:
            kwargs["base_url"] = self.base_url

            # 内部 API（禁用 SSL 验证）
            if "10.140." in self.base_url or "internal" in self.base_url:
                print("🧩 Using Internal API (SSL verify disabled)")
                kwargs["http_client"] = httpx.AsyncClient(verify=False)
            else:
                print("🌐 Using External API")

        return AsyncOpenAI(**kwargs)


# =========================
# ⚙️ 并发配置
# =========================
@dataclass
class ConcurrencyConfig:
    """并发与请求控制"""
    concurrency: int = 5
    write_interval: int = 5
    timeout: int = 120
    retry: int = 0
    rpm: int = 1000


# =========================
# 🤖 模型配置
# =========================
@dataclass
class ModelConfig:
    """模型参数与采样配置"""
    model: str
    temperature: float = 0.7
    top_p: float = 0.95
    max_tokens: int = 1024
    stream: bool = True
    thinking: bool = False


# =========================
# 📂 IO 配置
# =========================
@dataclass
class IOConfig:
    """输入输出目录与文件配置"""
    input_file: str
    output_dir: str
    prompt_file: Optional[str] = None
    key_name: str = "id"  # 新增唯一主键字段
    kept_columns: list[str] = field(default_factory=list)

# =========================
# 🧠 应用总配置
# =========================
@dataclass
class AppConfig:
    api: APIConfig
    model: ModelConfig
    concurrency: ConcurrencyConfig
    io: IOConfig

    @staticmethod
    def load(path: str) -> "AppConfig":
        """加载 YAML 配置文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        api_cfg = APIConfig(**data["api"])
        model_cfg = ModelConfig(**data["model"])
        concurrency_cfg = ConcurrencyConfig(**data.get("concurrency", {}))
        io_cfg = IOConfig(**data["io"])

        return AppConfig(
            api=api_cfg,
            model=model_cfg,
            concurrency=concurrency_cfg,
            io=io_cfg
        )


# =========================
# 统一入口
# =========================
def load_config(path: str) -> AppConfig:
    """统一配置加载入口"""
    return AppConfig.load(path)
