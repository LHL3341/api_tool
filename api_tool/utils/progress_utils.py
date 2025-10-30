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
from datetime import timedelta
from rich.console import Console


class AverageTimeRemainingColumn(TimeRemainingColumn):
    """改进版：智能格式化剩余时间（支持 h/m/s 显示）"""

    def render(self, task: Task) -> Text:
        if not task.total or not task.speed or task.speed <= 0:
            return Text("Estimating...", style="dim")

        remaining = (task.total - task.completed) / task.speed

        # 友好格式化：>1小时显示 h m；>1分钟显示 m s；否则 s
        td = timedelta(seconds=int(remaining))
        total_seconds = int(td.total_seconds())

        if total_seconds >= 3600:
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            text = f"{hours}h {minutes}m"
        elif total_seconds >= 60:
            minutes, seconds = divmod(total_seconds, 60)
            text = f"{minutes}m {seconds}s"
        else:
            text = f"{total_seconds}s"

        return Text(text, style="cyan")


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
    console = Console(force_terminal=True)
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

    progress = Progress(*columns, console=console)
    return progress
