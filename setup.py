from setuptools import setup, find_packages

setup(
    name="hubseek",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27.0",
        "openai>=1.0.0",
        "diskcache>=5.6.3",
        "click>=8.1.7",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "hubseek=src.main:main",
        ],
    },
    python_requires=">=3.10",
    author="HubSeek",
    description="Natural language GitHub project finder powered by AI",
)
