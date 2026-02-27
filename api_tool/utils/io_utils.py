import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from rich.console import Console

console = Console()

def load_jsonl(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """加载 JSONL 文件"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def append_jsonl(record: Dict[str, Any], file_path: Union[str, Path]):
    """追加记录到 JSONL 文件"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()

def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """加载 JSON 文件"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_parquet(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """加载 Parquet 文件"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    df = pd.read_parquet(path)
    return df.to_dict(orient="records")

def load_dataset_skip_existing(
    input_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    key_name: str = "id"
) -> List[Dict[str, Any]]:
    """
    加载数据集，并自动去掉 output_file 已存在的记录。
    支持 JSONL 和 Parquet 文件（通过后缀判断）。
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found: {input_file}")

    # 1️⃣ 加载原始数据集
    if input_path.suffix.lower() in {".jsonl"}:
        dataset = load_jsonl(input_path)
    elif input_path.suffix.lower() in {".json"}:
        dataset = load_json(input_path)
    elif input_path.suffix.lower() in {".parquet", ".pq"}:
        dataset = load_parquet(input_path)
    else:
        raise ValueError(f"Unsupported input file format: {input_file}")

    total_count = len(dataset)
    console.print(f"[bold blue]📘 Loaded dataset: {total_count} total items[/bold blue]")
    console.print(dataset[0])

    # 2️⃣ 如果没有输出文件，则返回全部数据
    if output_file is None:
        console.print("[yellow]⚠️ No output file provided, returning full dataset[/yellow]")
        return dataset

    # 3️⃣ 检查输出路径
    output_path = Path(output_file)
    results_path = output_path / "results.jsonl"
    if not output_path.exists() or not results_path.exists():
        console.print(f"[green]✅ Output not found, creating new file at {results_path}[/green]")
        output_path.mkdir(parents=True, exist_ok=True)
        return dataset

    # 4️⃣ 加载已有结果
    if results_path.suffix.lower() in {".jsonl", ".json"}:
        scored_data = load_jsonl(results_path)
    elif results_path.suffix.lower() in {".parquet", ".pq"}:
        scored_data = load_parquet(results_path)
    else:
        raise ValueError(f"Unsupported output file format: {output_file}")

    scored_count = len(scored_data)
    scored_keys = {str(item[key_name]) for item in scored_data if key_name in item}

    # 5️⃣ 去掉重复项
    filtered_dataset = [item for item in dataset if str(item.get(key_name)) not in scored_keys]
    remaining_count = len(filtered_dataset)

    console.print(
        f"[bold cyan]🔹 Total: {total_count} | Completed: {scored_count} | Remaining: {remaining_count}[/bold cyan]"
    )

    return filtered_dataset
