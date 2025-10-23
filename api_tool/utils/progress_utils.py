# api_tool/utils/progress_utils.py
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    Task,
)
from rich.text import Text


class AverageTimeRemainingColumn(TimeRemainingColumn):
    """进度条平均剩余时间列（兼容 rich 版本）"""
    def render(self, task: Task):
        # 防护性检查：确保有总量和速度
        if task.total and task.speed:
            remaining = (task.total - task.completed) / task.speed
            # 使用父类的格式化方法（内部方法）
            # 在某些 rich 版本上 _format_time 可用，若报错请改为自定义格式
            try:
                return super()._format_time(remaining)
            except Exception:
                # 回退到简单的秒数显示
                return Text(f"{int(remaining)}s")
        return super().render(task)


class RequestsStatusColumn(TextColumn):
    """显示当前活动请求数、已发送总请求数、成功请求数"""
    def __init__(self, evaluator, **kwargs):
        # 传入空字符串不会在列前添加额外文字
        super().__init__("", **kwargs)
        self.evaluator = evaluator

    def render(self, task: Task):
        text = (
            f"Active: {self.evaluator.current_requests} | "
            f"Sent: {self.evaluator.total_requests_sent} | "
            f"Success: {self.evaluator.total_requests_success}"
        )
        return Text(text, style="green")


def create_progress_bar(evaluator=None) -> Progress:
    """
    返回一个 Progress 实例。
    如果传入 evaluator，则会在列中自动加入 RequestsStatusColumn(evaluator)。
    """
    columns = [
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[green]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        AverageTimeRemainingColumn(),
    ]

    if evaluator is not None:
        # 把 RequestsStatusColumn 加在倒数第二个位置（在 AverageTimeRemainingColumn 之前）
        columns.insert(-1, RequestsStatusColumn(evaluator))

    progress = Progress(*columns)
    return progress
