from abc import ABC, abstractmethod
from api_tool.config import AppConfig

class BaseEvaluator(ABC):
    """抽象评估基类，所有评估器继承自它"""

    def __init__(self, config: AppConfig):
        self.config = config

    @abstractmethod
    async def run(self):
        """主执行入口"""
        pass
