"""Setup configuration for UK Broadband Price Comparison Tool."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bb-price-compare",
    version="1.0.0",
    author="Sky Capability Team",
    description="UK Broadband Price Comparison Tool using web scraping",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "playwright>=1.42.0",
        "pandas>=2.2.1",
        "openpyxl>=3.1.2",
        "python-dotenv>=1.0.1",
        "pydantic>=2.6.3",
        "colorlog>=6.8.2",
    ],
    entry_points={
        "console_scripts": [
            "bb-compare=src.main:main",
        ],
    },
)
