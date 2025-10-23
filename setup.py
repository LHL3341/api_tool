from setuptools import setup, find_packages

setup(
    name="api_tool",
    version="0.1.0",
    description="Automated evaluation using language models",
    author="LHL",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "openai>=1.0.0",
        "tiktoken>=0.7.0",
        "pillow>=10.0.0",
        "pyyaml>=6.0",
        "typer>=0.12.3",
        "rich>=13.7.1",
        "aiofiles>=23.2.1",
        "pandas>=2.2.2",
        "numpy>=1.26.4",
        "datasets>=2.14.2",
        "matplotlib>=3.9.0",
        "seaborn>=0.12.3",
        "httpx>=0.26.0"
    ],
    entry_points={
        "console_scripts": [
            "api=api_tool.main:app",  # ← 注意这里要用 :app
        ],
    },
    python_requires=">=3.9",
)
