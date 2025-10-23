import asyncio
import typer
import traceback
from rich.console import Console
from api_tool.config import load_config
from api_tool.evaluator.llm_evaluator import LLMEvaluator

app = typer.Typer(add_completion=False)

@app.command(name="run")
def run(
    config_path: str = typer.Option("config.yaml", "--config-path", "-c", help="Path to the configuration file.")
):
    """
    LLM-as-Judge: Automated evaluation using language models.
    """
    try:
        config = load_config(config_path)
        evaluator = LLMEvaluator(config)

        print("🚀 Starting LLM-as-Judge evaluation...")
        print(f"Loaded configuration from: {config_path}")
        print(f"Config: {config}")

        asyncio.run(evaluator.run())

    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        traceback.print_exc()
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        # 打印完整 traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
