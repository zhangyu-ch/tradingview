import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tradingview_zy",
    version="1.0.0",
    author="zy",
    description="TradingView market data, monitoring, backtesting, and trading tools.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    license="MIT",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    python_requires=">=3.11",
)
