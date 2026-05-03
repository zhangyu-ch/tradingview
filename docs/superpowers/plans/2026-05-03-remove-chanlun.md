# Remove Chanlun Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all Chanlun analysis code from the runtime tree, rename the project package to `tradingview_zy`, and keep market data, basic Web K-line service, trader execution, generic backtesting, stock selection, and monitoring usable without Chanlun computation.

**Architecture:** This is a one-time migration, not a compatibility shim. The runtime package becomes `src/tradingview_zy`; Chanlun computation, drawing, strategy examples, and adapters are archived outside the import path. Stock selection and monitoring keep their entry points but run generic user-defined strategies against normal K-line data.

**Tech Stack:** Python 3.11, Flask, Tornado, APScheduler, SQLAlchemy, pandas, pytest, TradingView UDF HTTP endpoints.

---

## File Structure

### Runtime package

- Rename directory: `src/tradingview_zy/` -> `src/tradingview_zy/`.
- Keep and refactor:
  - `src/tradingview_zy/base.py`: market enum and generic project constants.
  - `src/tradingview_zy/exchange/`: exchange adapters and K-line access.
  - `src/tradingview_zy/db.py`, `src/tradingview_zy/file_db.py`: persisted data and records.
  - `src/tradingview_zy/fun.py`, `src/tradingview_zy/utils.py`, `src/tradingview_zy/encodefix.py`: generic utilities.
  - `src/tradingview_zy/zixuan.py`: watchlist support.
  - `src/tradingview_zy/backtesting/`: generic backtesting only.
  - `src/tradingview_zy/trader/`: execution adapters only.
- Create:
  - `src/tradingview_zy/strategies/__init__.py`: strategy package marker.
  - `src/tradingview_zy/strategies/base.py`: generic strategy protocol and result dataclasses.
  - `src/tradingview_zy/strategies/loader.py`: dotted-path strategy loader.
  - `src/tradingview_zy/selection.py`: generic stock selection runner.
  - `src/tradingview_zy/monitoring.py`: generic monitoring runner.
  - `src/tradingview_zy/web_payloads.py`: plain OHLCV conversion for TradingView history responses.
- Remove from runtime tree after archive:
  - `src/tradingview_zy/cl.py`
  - `src/tradingview_zy/cl_interface.py`
  - `src/tradingview_zy/cl_utils.py`
  - `src/tradingview_zy/cl_analyse.py`
  - `src/tradingview_zy/kcharts.py`
  - `src/tradingview_zy/strategy/`
  - `src/tradingview_zy/xuangu/`
  - encrypted/original Chanlun files such as `src/tradingview_zy/cl-原版.py`, `src/tradingview_zy/cl-加密.py`.

### Web package

- Rename directory: `web/tradingview_zy_chart/` -> `web/tradingview_zy_chart/`.
- Modify:
  - `web/tradingview_zy_chart/app.py`: import `tradingview_zy`, not `chanlun`.
  - `web/tradingview_zy_chart/cl_app/__init__.py`: remove Chanlun routes and convert `/tv/history` to plain OHLCV.
  - `web/tradingview_zy_chart/cl_app/alert_tasks.py`: run generic monitoring strategies.
  - `web/tradingview_zy_chart/cl_app/xuangu_tasks.py`: run generic selection strategies.
  - `web/tradingview_zy_chart/cl_app/templates/index.html`: remove Chanlun chart controls and keep navigation to generic watchlist, alerts, selection, jobs, settings.
  - `web/tradingview_zy_chart/cl_app/static/js/charts.js`: stop reading Chanlun overlay arrays from `/tv/history`.
- Keep existing template names for stock selection and alert pages during the first migration, but change labels from Chanlun terms to generic strategy terms.

### Scripts and project metadata

- Modify:
  - `pyproject.toml`: project name and description.
  - `setup.py`: package name and package discovery.
  - `check_env.py`: import `tradingview_zy`, check `src/tradingview_zy/config.py`.
  - `windows_run.bat`: start `web/tradingview_zy_chart/app.py`.
  - `script/tradingview_zy_web.config.js`, `script/tradingview_zy_demo.config.js`, `script/jupyter_lab.config.js`: update app path/name to `tradingview_zy` / `tradingview_zy_chart`.
  - `script/crontab/*.py`, `script/trader/*.py`: update imports; Chanlun-specific script bodies print an unavailable message and exit with code 0.

### Archive and docs

- Create:
  - `archive/chanlun-runtime-source.zip`: compressed copy of removed Chanlun runtime files.
  - `archive/docs/`: migrated Chanlun-related documentation.
  - `docs/web-right-panel-extension.md`: Web right panel extension guide.
  - `docs/custom-strategy-integration.md`: custom strategy integration guide.
- Modify:
  - `README.md`: describe `tradingview_zy` and current supported features.
  - `CLAUDE.md`: update package and command references if they still name `chanlun` as runtime package.

### Tests

- Create:
  - `tests/test_strategy_loader.py`
  - `tests/test_selection_monitoring.py`
  - `tests/test_web_payloads.py`
  - `tests/test_no_runtime_chanlun_imports.py`
  - `tests/test_backtesting_base_generic.py`

---

## Task 1: Add Characterization Tests for Generic Boundaries

**Files:**
- Create: `tests/test_strategy_loader.py`
- Create: `tests/test_selection_monitoring.py`
- Create: `tests/test_web_payloads.py`
- Create: `tests/test_no_runtime_chanlun_imports.py`

- [ ] **Step 1: Create tests for strategy loader, selection, monitoring, Web payloads, and removed imports**

Create `tests/test_strategy_loader.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.strategies.base import StrategyContext, StrategySignal
from tradingview_zy.strategies.loader import load_strategy


class LocalStrategy:
    name = "local_strategy"

    def run(self, context: StrategyContext):
        return [
            StrategySignal(
                code=context.code,
                name="测试标的",
                action="watch",
                score=88.0,
                message="close above open",
                frequency=context.frequency,
                event_time=context.now,
            )
        ]


def test_load_strategy_from_dotted_path():
    strategy = load_strategy("tests.test_strategy_loader:LocalStrategy")
    assert strategy.name == "local_strategy"


def test_load_strategy_rejects_object_without_run():
    with pytest.raises(TypeError, match="run"):
        load_strategy("pathlib:Path")
```

Create `tests/test_selection_monitoring.py`:

```python
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.base import StrategyContext, StrategySignal


class FakeExchange:
    def __init__(self):
        self.requested = []

    def klines(self, code, frequency):
        self.requested.append((code, frequency))
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-05-03 09:30:00"),
                    "frequency": frequency,
                    "code": code,
                    "open": 10.0,
                    "close": 11.0,
                    "high": 11.5,
                    "low": 9.8,
                    "volume": 1000,
                }
            ]
        )


class PositiveCloseStrategy:
    name = "positive_close"

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) > float(last["open"]):
            return [
                StrategySignal(
                    code=context.code,
                    name=context.name,
                    action="select",
                    score=1.0,
                    message="close > open",
                    frequency=context.frequency,
                    event_time=context.now,
                )
            ]
        return []


def test_selection_runner_uses_plain_klines_only():
    exchange = FakeExchange()
    runner = SelectionRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    results = runner.run(
        market="a",
        stocks=[{"code": "SH.000001", "name": "上证指数"}],
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert exchange.requested == [("SH.000001", "d")]
    assert results[0].code == "SH.000001"
    assert results[0].message == "close > open"


def test_monitoring_runner_returns_events_without_chanlun_data():
    exchange = FakeExchange()
    runner = MonitoringRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    events = runner.run_code(
        market="a",
        code="SH.000001",
        name="上证指数",
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert len(events) == 1
    assert events[0].action == "select"
    assert events[0].frequency == "d"
```

Create `tests/test_web_payloads.py`:

```python
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.web_payloads import klines_to_tv_history


def test_klines_to_tv_history_returns_ohlcv_only():
    klines = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-05-03 09:30:00"),
                "open": 10.0,
                "close": 10.5,
                "high": 10.8,
                "low": 9.9,
                "volume": 100,
            }
        ]
    )

    payload = klines_to_tv_history(klines, update=False)

    assert payload == {
        "s": "ok",
        "t": [1777762200],
        "o": [10.0],
        "c": [10.5],
        "h": [10.8],
        "l": [9.9],
        "v": [100],
        "update": False,
    }
    assert "bis" not in payload
    assert "mmds" not in payload
```

Create `tests/test_no_runtime_chanlun_imports.py`:

```python
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = [ROOT / "src", ROOT / "web", ROOT / "script", ROOT / "check_env.py", ROOT / "setup.py"]
SKIP_PARTS = {".venv", "archive", "docs", "cookbook", "notebook", "__pycache__"}


def iter_python_files():
    for path in RUNTIME_PATHS:
        if path.is_file() and path.suffix == ".py":
            yield path
            continue
        if not path.exists():
            continue
        for py_file in path.rglob("*.py"):
            if any(part in SKIP_PARTS for part in py_file.parts):
                continue
            yield py_file


def test_runtime_python_files_do_not_import_chanlun():
    offenders = []
    for py_file in iter_python_files():
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "chanlun" or alias.name.startswith("tradingview_zy."):
                        offenders.append(f"{py_file}: import {alias.name}")
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "chanlun" or module.startswith("tradingview_zy."):
                    offenders.append(f"{py_file}: from {module} import ...")
    assert offenders == []
```

- [ ] **Step 2: Run tests and verify they fail because the new package does not exist yet**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_strategy_loader.py tests/test_selection_monitoring.py tests/test_web_payloads.py tests/test_no_runtime_chanlun_imports.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingview_zy'` for the first three files. The no-runtime-imports test may also fail because existing runtime imports still name `chanlun`.

- [ ] **Step 3: Commit failing characterization tests**

Run:

```bash
git add tests/test_strategy_loader.py tests/test_selection_monitoring.py tests/test_web_payloads.py tests/test_no_runtime_chanlun_imports.py
git commit -m "$(cat <<'EOF'
添加缠论剥离边界测试

问题或需求描述：需要用测试锁定新包名、通用策略接口、普通 K 线 Web payload 和运行路径不再导入 chanlun 的目标。
修复或实现思路：先添加失败的边界测试，作为后续迁移和剥离工作的验收约束。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 2: Archive Chanlun Sources and Documentation

**Files:**
- Create: `archive/chanlun-runtime-source.zip`
- Create/Move: `archive/docs/`
- Modify: `README.md`

- [ ] **Step 1: Create archive directories and compressed source archive**

Run:

```bash
mkdir -p archive/docs && python - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path.cwd()
archive_path = root / "archive" / "chanlun-runtime-source.zip"
sources = [
    root / "src" / "chanlun" / "cl.py",
    root / "src" / "chanlun" / "cl_interface.py",
    root / "src" / "chanlun" / "cl_utils.py",
    root / "src" / "chanlun" / "cl_analyse.py",
    root / "src" / "chanlun" / "kcharts.py",
    root / "src" / "chanlun" / "monitor.py",
    root / "src" / "chanlun" / "strategy",
    root / "src" / "chanlun" / "xuangu",
    root / "src" / "cl_myquant",
    root / "src" / "cl_vnpy",
    root / "src" / "cl_wtpy",
    root / "joinquant",
]
with ZipFile(archive_path, "w", ZIP_DEFLATED) as zf:
    for source in sources:
        if not source.exists():
            continue
        if source.is_file():
            zf.write(source, source.relative_to(root).as_posix())
        else:
            for file in source.rglob("*"):
                if file.is_file() and "__pycache__" not in file.parts:
                    zf.write(file, file.relative_to(root).as_posix())
print(archive_path)
PY
```

Expected: command prints `archive/chanlun-runtime-source.zip` path and exits with code 0.

- [ ] **Step 2: Move Chanlun-specific documentation into archive/docs**

Run:

```bash
python - <<'PY'
from pathlib import Path
import shutil

root = Path.cwd()
archive_docs = root / "archive" / "docs"
archive_docs.mkdir(parents=True, exist_ok=True)
for path in (root / "cookbook" / "docs").glob("*缠论*.md"):
    shutil.move(str(path), str(archive_docs / path.name))
for name in ["策略缠论参数优化.md", "缠论买卖点和背驰规则.md", "缠论数据对象与方法.md", "缠论配置项说明.md", "缠论回测与交易指南.md"]:
    path = root / "cookbook" / "docs" / name
    if path.exists():
        shutil.move(str(path), str(archive_docs / name))
print("archived docs", len(list(archive_docs.glob("*.md"))))
PY
```

Expected: prints `archived docs N` where `N` is greater than 0.

- [ ] **Step 3: Replace README with new project scope**

Write `README.md`:

```markdown
# tradingview_zy

`tradingview_zy` 是一个通用行情、TradingView 图表、选股监控、回测和交易执行工具。

本仓库已从原缠论分析系统迁移为普通行情/交易工具。运行路径中不再保留缠论计算、分型、笔、线段、中枢、买卖点、背驰等模块。历史缠论源码已压缩归档到 `archive/chanlun-runtime-source.zip`，相关文档已迁移到 `archive/docs/`。

## 当前保留能力

- 多市场交易所适配和 K 线查询。
- TradingView UDF 风格基础 K 线接口。
- 自选股、通用选股任务和通用监控任务外壳。
- 自定义策略接入接口。
- 通用回测框架。
- trader 下单、撤单、账户和持仓等交易执行适配。

## 环境

项目优先使用 Python 3.11：

```bash
uv venv --python=3.11 .venv
uv sync
export PYTHONPATH="$PWD/src"
```

运行前复制配置：

```bash
cp src/tradingview_zy/config.py.demo src/tradingview_zy/config.py
```

检查环境：

```bash
PYTHONPATH="$PWD/src" uv run python check_env.py
```

启动 Web 服务：

```bash
PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/app.py nobrowser
```

## 自定义策略

选股、监控、回测和交易信号统一面向普通 K 线数据。接入方式见：

- `docs/custom-strategy-integration.md`
- `docs/web-right-panel-extension.md`
```

- [ ] **Step 4: Commit archive and README changes**

Run:

```bash
git add archive README.md
git commit -m "$(cat <<'EOF'
归档缠论源码和文档

问题或需求描述：运行路径需要剥离缠论模块，但仍需保留历史源码和文档供查阅。
修复或实现思路：将缠论源码压缩归档到 archive，并把缠论文档迁入 archive/docs，主 README 改为 tradingview_zy 项目说明。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 3: Rename Runtime Package and Web Directory

**Files:**
- Rename: `src/tradingview_zy/` -> `src/tradingview_zy/`
- Rename: `web/tradingview_zy_chart/` -> `web/tradingview_zy_chart/`
- Modify: `pyproject.toml`
- Modify: `setup.py`
- Modify: `check_env.py`
- Modify: `windows_run.bat`

- [ ] **Step 1: Rename directories**

Run:

```bash
git mv src/tradingview_zy src/tradingview_zy
git mv web/tradingview_zy_chart web/tradingview_zy_chart
```

Expected: both `git mv` commands exit with code 0.

- [ ] **Step 2: Batch-replace import paths and Web app path strings in text files**

Run:

```bash
python - <<'PY'
from pathlib import Path

root = Path.cwd()
extensions = {".py", ".md", ".toml", ".bat", ".js", ".html", ".json", ".yml", ".yaml"}
skip_parts = {".git", ".venv", "archive", "__pycache__", "node_modules"}
replacements = {
    "tradingview_zy_chart": "tradingview_zy_chart",
    "tradingview_zy": "tradingview_zy",
    "tradingview_zy": "tradingview_zy",
    "from tradingview_zy": "from tradingview_zy",
    "import tradingview_zy": "import tradingview_zy",
    "tradingview_zy.": "tradingview_zy.",
    "src/tradingview_zy": "src/tradingview_zy",
    "src\\chanlun": "src\\tradingview_zy",
    "web/tradingview_zy_chart": "web/tradingview_zy_chart",
    "web\\tradingview_zy_chart": "web\\tradingview_zy_chart",
}
for path in root.rglob("*"):
    if not path.is_file() or path.suffix not in extensions:
        continue
    if any(part in skip_parts for part in path.parts):
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    new_text = text
    for old, new in replacements.items():
        new_text = new_text.replace(old, new)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
PY
```

Expected: command exits with code 0.

- [ ] **Step 3: Replace `pyproject.toml` project metadata**

Edit the top of `pyproject.toml` to this exact block:

```toml
[project]
name = "tradingview_zy"
version = "1.0.0"
description = "TradingView market data, monitoring, backtesting, and trading tools"
readme = "README.md"
requires-python = ">=3.11"
```

Keep the existing `dependencies`, `[tool.uv.sources]`, and `[[tool.uv.index]]` blocks unchanged.

- [ ] **Step 4: Replace `setup.py` with package discovery**

Write `setup.py`:

```python
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
```

- [ ] **Step 5: Replace `check_env.py` imports and messages**

Update `check_env.py` environment checks to this exact code:

```python
    try:
        from tradingview_zy import base
    except Exception:
        print("无法导入 tradingview_zy 模块，环境变量未设置或设置错误")
        print(f"当前的环境变量如下：{sys.path}")
        print(f"需要将 PYTHONPATH 环境变量设置为 {os.getcwd()}\\src 目录")
        return

    try:
        from tradingview_zy import config
    except Exception:
        print("无法导入 config，请在 src/tradingview_zy 目录复制 config.py.demo 为 config.py")
        return
```

Replace the old `from tradingview_zy import cl_interface` and `from tradingview_zy import config` blocks with the code above.

- [ ] **Step 6: Run package import smoke check**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python - <<'PY'
import tradingview_zy
from tradingview_zy.base import Market
print(tradingview_zy.__file__)
print([m.value for m in Market])
PY
```

Expected: command prints a path under `src/tradingview_zy` and market values including `a`, `hk`, `futures`, `currency`.

- [ ] **Step 7: Commit rename and metadata changes**

Run:

```bash
git add pyproject.toml setup.py check_env.py windows_run.bat src web script README.md CLAUDE.md
git commit -m "$(cat <<'EOF'
迁移运行包名为 tradingview_zy

问题或需求描述：项目运行路径需要从 chanlun 迁移为 tradingview_zy，避免继续暴露旧缠论包名。
修复或实现思路：一次性重命名源码包和 Web 目录，批量更新 import、启动路径和项目元数据。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 4: Add Generic Strategy Contracts and Plain Web Payload Conversion

**Files:**
- Create: `src/tradingview_zy/strategies/__init__.py`
- Create: `src/tradingview_zy/strategies/base.py`
- Create: `src/tradingview_zy/strategies/loader.py`
- Create: `src/tradingview_zy/web_payloads.py`
- Test: `tests/test_strategy_loader.py`
- Test: `tests/test_web_payloads.py`

- [ ] **Step 1: Create strategy package marker**

Write `src/tradingview_zy/strategies/__init__.py`:

```python
from .base import StrategyContext, StrategySignal
from .loader import load_strategy

__all__ = ["StrategyContext", "StrategySignal", "load_strategy"]
```

- [ ] **Step 2: Create generic strategy dataclasses**

Write `src/tradingview_zy/strategies/base.py`:

```python
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

StrategyAction = Literal["select", "watch", "buy", "sell", "open", "close", "ignore"]


@dataclass(frozen=True)
class StrategyContext:
    market: str
    code: str
    name: str
    frequency: str
    klines: pd.DataFrame
    now: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySignal:
    code: str
    name: str
    action: StrategyAction
    score: float
    message: str
    frequency: str
    event_time: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_strategy_results(results: Any) -> list[StrategySignal]:
    if results is None:
        return []
    if isinstance(results, StrategySignal):
        return [results]
    if isinstance(results, list) and all(isinstance(item, StrategySignal) for item in results):
        return results
    raise TypeError("strategy run() must return StrategySignal, list[StrategySignal], or None")
```

- [ ] **Step 3: Create dotted-path strategy loader**

Write `src/tradingview_zy/strategies/loader.py`:

```python
from __future__ import annotations

from importlib import import_module
from typing import Any


def load_strategy(dotted_path: str, **kwargs: Any) -> Any:
    if ":" not in dotted_path:
        raise ValueError("strategy path must use 'module:ClassName' format")
    module_name, class_name = dotted_path.split(":", 1)
    if module_name == "" or class_name == "":
        raise ValueError("strategy path must include module and class name")
    module = import_module(module_name)
    strategy_class = getattr(module, class_name)
    strategy = strategy_class(**kwargs)
    if not callable(getattr(strategy, "run", None)):
        raise TypeError("strategy object must define run(context)")
    return strategy
```

- [ ] **Step 4: Create plain TradingView history payload conversion**

Write `src/tradingview_zy/web_payloads.py`:

```python
from __future__ import annotations

import pandas as pd

from tradingview_zy import fun


def klines_to_tv_history(klines: pd.DataFrame, update: bool, status: str = "ok") -> dict:
    if klines is None or len(klines) == 0:
        return {"s": "no_data"}
    return {
        "s": status,
        "t": [fun.datetime_to_int(row["date"]) for _, row in klines.iterrows()],
        "o": klines["open"].tolist(),
        "c": klines["close"].tolist(),
        "h": klines["high"].tolist(),
        "l": klines["low"].tolist(),
        "v": klines["volume"].tolist(),
        "update": update,
    }
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_strategy_loader.py tests/test_web_payloads.py -q
```

Expected: PASS for both test files.

- [ ] **Step 6: Commit strategy contracts and payload converter**

Run:

```bash
git add src/tradingview_zy/strategies src/tradingview_zy/web_payloads.py tests/test_strategy_loader.py tests/test_web_payloads.py
git commit -m "$(cat <<'EOF'
添加通用策略接口和普通K线响应

问题或需求描述：选股、监控、回测和 Web K 线接口需要脱离缠论数据结构。
修复或实现思路：新增通用策略上下文、策略信号、策略加载器和 TradingView OHLCV 响应转换函数。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 5: Add Generic Selection and Monitoring Runners

**Files:**
- Create: `src/tradingview_zy/selection.py`
- Create: `src/tradingview_zy/monitoring.py`
- Test: `tests/test_selection_monitoring.py`

- [ ] **Step 1: Create generic selection runner**

Write `src/tradingview_zy/selection.py`:

```python
from __future__ import annotations

import datetime as dt
from typing import Iterable

from tradingview_zy.strategies.base import StrategyContext, StrategySignal, normalize_strategy_results


class SelectionRunner:
    def __init__(self, exchange, strategy):
        self.exchange = exchange
        self.strategy = strategy

    def run(
        self,
        market: str,
        stocks: Iterable[dict],
        frequency: str,
        now: dt.datetime | None = None,
    ) -> list[StrategySignal]:
        run_time = now or dt.datetime.now()
        results: list[StrategySignal] = []
        for stock in stocks:
            code = stock["code"]
            name = stock.get("name", code)
            klines = self.exchange.klines(code, frequency)
            context = StrategyContext(
                market=market,
                code=code,
                name=name,
                frequency=frequency,
                klines=klines,
                now=run_time,
            )
            results.extend(normalize_strategy_results(self.strategy.run(context)))
        return results
```

- [ ] **Step 2: Create generic monitoring runner**

Write `src/tradingview_zy/monitoring.py`:

```python
from __future__ import annotations

import datetime as dt

from tradingview_zy.strategies.base import StrategyContext, StrategySignal, normalize_strategy_results


class MonitoringRunner:
    def __init__(self, exchange, strategy):
        self.exchange = exchange
        self.strategy = strategy

    def run_code(
        self,
        market: str,
        code: str,
        name: str,
        frequency: str,
        now: dt.datetime | None = None,
    ) -> list[StrategySignal]:
        run_time = now or dt.datetime.now()
        klines = self.exchange.klines(code, frequency)
        context = StrategyContext(
            market=market,
            code=code,
            name=name,
            frequency=frequency,
            klines=klines,
            now=run_time,
        )
        return normalize_strategy_results(self.strategy.run(context))
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_selection_monitoring.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit generic runners**

Run:

```bash
git add src/tradingview_zy/selection.py src/tradingview_zy/monitoring.py tests/test_selection_monitoring.py
git commit -m "$(cat <<'EOF'
添加通用选股和监控运行器

问题或需求描述：选股和监控需要保留接口，但不能再依赖缠论分析。
修复或实现思路：新增基于普通 K 线和自定义策略的 SelectionRunner 与 MonitoringRunner。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 6: Remove Chanlun Runtime Files and Refactor Backtesting Base

**Files:**
- Delete: `src/tradingview_zy/cl.py`
- Delete: `src/tradingview_zy/cl_interface.py`
- Delete: `src/tradingview_zy/cl_utils.py`
- Delete: `src/tradingview_zy/cl_analyse.py`
- Delete: `src/tradingview_zy/kcharts.py`
- Delete: `src/tradingview_zy/strategy/`
- Delete: `src/tradingview_zy/xuangu/`
- Modify: `src/tradingview_zy/backtesting/base.py`
- Create: `tests/test_backtesting_base_generic.py`

- [ ] **Step 1: Create generic backtesting base test**

Write `tests/test_backtesting_base_generic.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.backtesting.base import MarketDatas, Operation, POSITION


def test_operation_uses_generic_signal_name():
    opt = Operation(code="SH.000001", opt="open", signal="breakout", msg="突破")
    assert opt.opt == "buy"
    assert opt.signal == "breakout"
    assert opt.open_uid == "SH.000001:breakout"


def test_position_accepts_generic_signal_name():
    pos = POSITION(code="SH.000001", signal="breakout")
    assert pos.signal == "breakout"
    assert pos.amount == 0


def test_market_datas_no_longer_exposes_get_cl_data():
    assert not hasattr(MarketDatas, "get_cl_data")
```

- [ ] **Step 2: Replace `backtesting/base.py` Chanlun imports and generic names**

In `src/tradingview_zy/backtesting/base.py`, remove these imports:

```python
import MyTT
from tradingview_zy.cl_interface import BI, ICL, XD, ZS
from tradingview_zy.cl_utils import cal_zs_macd_infos
```

Keep these imports if the file still uses them after cleanup:

```python
import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import talib

from tradingview_zy.fun import get_logger
```

- [ ] **Step 3: Rename `mmd` constructor arguments to generic `signal` while keeping operation behavior**

In `POSITION.__init__`, change signature beginning to:

```python
    def __init__(
        self,
        code: str,
        signal: str,
        type: str = None,
        balance: float = 0,
```

Replace these assignments:

```python
        self.signal: str = signal
        self.mmd: str = signal
```

In `Operation.__init__`, change signature beginning to:

```python
    def __init__(
        self,
        code: str,
        opt: str,
        signal: str,
        loss_price: float = 0,
```

Replace the old `self.mmd` assignment with:

```python
        self.signal: str = signal
        self.mmd: str = signal
```

Replace the `open_uid` default line with:

```python
        self.open_uid: str = f"{code}:{signal}" if open_uid is None else open_uid
```

Replace `Operation.__str__` with:

```python
    def __str__(self):
        return f"signal {self.signal} opt {self.opt} loss_price {self.loss_price} msg: {self.msg}"
```

- [ ] **Step 4: Remove Chanlun data cache and abstract method from `MarketDatas`**

In `MarketDatas.__init__`, remove `cl_config`, `self.cl_config`, `self.cl_datas`, and `self.cache_cl_datas`. The constructor becomes:

```python
    def __init__(self, market: str, frequencys: List[str]):
        self.market = market
        self.frequencys = frequencys
```

Delete the abstract `get_cl_data` method entirely.

- [ ] **Step 5: Remove Chanlun indicator helpers from `Strategy`**

Delete static methods that accept `ICL` or read `cd.get_klines()`, `cd.get_src_klines()`, `cd.get_idx()`, `BI`, `XD`, or `ZS`. Keep generic lifecycle methods: `open`, `close`, `on_bt_loop_start`, `is_filter_opts`, `filter_opts`, `clear`, `write_log`, and `add_times`.

- [ ] **Step 6: Delete Chanlun runtime files and directories**

Run:

```bash
git rm -r src/tradingview_zy/cl.py src/tradingview_zy/cl_interface.py src/tradingview_zy/cl_utils.py src/tradingview_zy/cl_analyse.py src/tradingview_zy/kcharts.py src/tradingview_zy/strategy src/tradingview_zy/xuangu || true
git rm -f src/tradingview_zy/cl-原版.py src/tradingview_zy/cl-加密.py || true
```

Expected: files are staged for deletion if present; missing files are ignored by shell `|| true`.

- [ ] **Step 7: Run generic backtesting test**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_backtesting_base_generic.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit runtime removal and backtesting refactor**

Run:

```bash
git add src/tradingview_zy/backtesting/base.py tests/test_backtesting_base_generic.py
git add -u src/tradingview_zy
git commit -m "$(cat <<'EOF'
移除运行路径中的缠论计算模块

问题或需求描述：运行源码树不能再保留缠论计算、接口结构和策略实现。
修复或实现思路：删除缠论运行文件与策略目录，并将回测基类改为通用 signal 命名和普通市场数据接口。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 7: Convert Web History Endpoint to Plain OHLCV and Remove Chanlun Routes

**Files:**
- Modify: `web/tradingview_zy_chart/app.py`
- Modify: `web/tradingview_zy_chart/cl_app/__init__.py`
- Modify: `web/tradingview_zy_chart/cl_app/static/js/charts.js`
- Modify: `web/tradingview_zy_chart/cl_app/templates/index.html`

- [ ] **Step 1: Update app imports**

In `web/tradingview_zy_chart/app.py`, replace:

```python
import tradingview_zy.encodefix  # Fix Windows print 乱码问题  # noqa: F401
from tradingview_zy import config
```

Ensure no `chanlun` import remains in this file.

- [ ] **Step 2: Replace Web module imports**

At the top of `web/tradingview_zy_chart/cl_app/__init__.py`, remove imports of `cl_utils`, `AIAnalyse`, and Chanlun chart helpers. The generic import block should include:

```python
from tradingview_zy import config, fun
from tradingview_zy.base import Market
from tradingview_zy.config import get_data_path
from tradingview_zy.db import db
from tradingview_zy.exchange import get_exchange
from tradingview_zy.exchange.stocks_bkgn import StocksBKGN
from tradingview_zy.web_payloads import klines_to_tv_history
from tradingview_zy.zixuan import ZiXuan
```

Keep local task imports:

```python
from .alert_tasks import AlertTasks
from .other_tasks import OtherTasks
from .xuangu_tasks import XuanguTasks
```

- [ ] **Step 3: Replace `/tv/history` body with plain K-line response**

Inside `tv_history`, replace the code from `frequency = resolution_maps[resolution]` through `return info` with:

```python
        frequency = resolution_maps[resolution]
        klines = ex.klines(code, frequency)
        if klines is None or len(klines) == 0:
            return {"s": "no_data"}

        if int(_to) < fun.datetime_to_int(klines.iloc[0]["date"]):
            return {"s": "no_data"}

        if firstDataRequest == "false":
            klines = klines.iloc[-10:]

        return klines_to_tv_history(
            klines,
            update=False if firstDataRequest == "true" else True,
            status=s,
        )
```

- [ ] **Step 4: Remove Chanlun config routes from Web app**

Delete route functions:

```python
get_cl_config
set_cl_config
reset_cl_config
export_cl_config
ai_analyse
ai_analyse_records
```

Expected: `/tv/config`, `/tv/search`, `/tv/symbols`, `/tv/history`, `/tv/marks`, `/tv/timescale_marks`, watchlist, alert, selection, jobs, settings, and A-share sector routes remain.

- [ ] **Step 5: Update chart JavaScript to ignore overlays**

In `web/tradingview_zy_chart/cl_app/static/js/charts.js`, remove reads and drawing calls for these response keys:

```javascript
fxs
bis
xds
zsds
bi_zss
xd_zss
zsd_zss
bcs
mmds
```

Keep OHLCV chart update logic based on `t`, `o`, `h`, `l`, `c`, `v`.

- [ ] **Step 6: Remove Chanlun controls from index template**

In `web/tradingview_zy_chart/cl_app/templates/index.html`, remove buttons, modals, panels, and menu items whose labels include these terms:

```text
缠论
分型
笔
线段
中枢
买卖点
背驰
```

Keep market selector, symbol selector, chart container, watchlist, alert, selection, jobs, settings links, and static TradingView library loading.

- [ ] **Step 7: Run Web import smoke check**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("web/tradingview_zy_chart").resolve()))
from cl_app import create_app
app = create_app()
print(app.name)
print(len(app.url_map._rules))
PY
```

Expected: command prints `cl_app` and a positive route count. If it fails because `src/tradingview_zy/config.py` does not exist, copy `src/tradingview_zy/config.py.demo` to `src/tradingview_zy/config.py` locally and rerun; do not commit `config.py`.

- [ ] **Step 8: Commit Web refactor**

Run:

```bash
git add web/tradingview_zy_chart src/tradingview_zy/web_payloads.py
git commit -m "$(cat <<'EOF'
改造Web为普通K线服务

问题或需求描述：Web 图表和接口需要移除缠论图层、配置和 AI 分析入口，同时保留基础 K 线服务。
修复或实现思路：将 /tv/history 改为普通 OHLCV 响应，删除缠论配置与分析路由，并移除前端缠论控件。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 8: Wire Alert and Selection Tasks to Custom Strategies

**Files:**
- Modify: `web/tradingview_zy_chart/cl_app/alert_tasks.py`
- Modify: `web/tradingview_zy_chart/cl_app/xuangu_tasks.py`
- Modify: `src/tradingview_zy/db.py`

- [ ] **Step 1: Add strategy path storage using existing alert task fields**

Keep the existing `cl_alert_task` table columns for migration simplicity. Store custom strategy dotted path in `check_idx_ma_info` as JSON:

```json
{"strategy_path": "my_package.my_module:MyStrategy", "strategy_kwargs": {}}
```

Use `check_idx_macd_info` for optional display metadata:

```json
{"description": "策略说明"}
```

No database migration is required in this task.

- [ ] **Step 2: Replace alert task execution with MonitoringRunner**

In `web/tradingview_zy_chart/cl_app/alert_tasks.py`, use this import block:

```python
import json
from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from tqdm.auto import tqdm

from tradingview_zy import fun
from tradingview_zy.db import TableByAlertTask, db
from tradingview_zy.exchange import Market, get_exchange
from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.strategies.loader import load_strategy
from tradingview_zy.zixuan import ZiXuan
```

Replace the inner body of `alert_run` after `stocks = zx.zx_stocks(alert_config.zx_group)` with:

```python
        strategy_config = json.loads(alert_config.check_idx_ma_info or "{}")
        strategy_path = strategy_config.get("strategy_path", "")
        strategy_kwargs = strategy_config.get("strategy_kwargs", {})
        if strategy_path == "":
            self.log.error(f"{alert_config.task_name} 未配置 strategy_path")
            return False

        strategy = load_strategy(strategy_path, **strategy_kwargs)
        runner = MonitoringRunner(exchange=ex, strategy=strategy)
        for s in tqdm(stocks):
            try:
                events = runner.run_code(
                    alert_config.market,
                    s["code"],
                    s["name"],
                    alert_config.frequency,
                )
                for event in events:
                    db.alert_record_save(
                        market=alert_config.market,
                        task_name=alert_config.task_name,
                        stock_code=event.code,
                        stock_name=event.name,
                        frequency=event.frequency,
                        alert_msg=event.message,
                        bi_is_done=event.action,
                        bi_is_td=str(event.score),
                        line_type="strategy",
                        line_dt=event.event_time,
                    )
            except Exception as e:
                self.log.error(f'run {s["code"]} alert exception {e}')
```

- [ ] **Step 3: Simplify alert list/edit payloads to generic strategy fields**

In route serialization for `/alert_list/<market>`, return these fields for each task:

```python
{
    "id": _l.id,
    "market": _l.market,
    "task_name": _l.task_name,
    "zx_group": _l.zx_group,
    "interval_minutes": _l.interval_minutes,
    "frequency": _l.frequency,
    "strategy_config": _l.check_idx_ma_info,
    "strategy_memo": _l.check_idx_macd_info,
    "is_send_msg": _l.is_send_msg,
    "is_run": _l.is_run,
}
```

In `/alert_save`, build `alert_config` with legacy columns set to empty strings except strategy JSON:

```python
        strategy_config = json.dumps(
            {
                "strategy_path": request.form["strategy_path"],
                "strategy_kwargs": json.loads(request.form.get("strategy_kwargs") or "{}"),
            },
            ensure_ascii=False,
        )
        alert_config = {
            "id": request.form["id"],
            "market": request.form["market"],
            "task_name": request.form["task_name"],
            "interval_minutes": int(request.form["interval_minutes"]),
            "zx_group": request.form["zx_group"],
            "frequency": request.form["frequency"],
            "check_bi_type": "",
            "check_bi_beichi": "",
            "check_bi_mmd": "",
            "check_xd_type": "",
            "check_xd_beichi": "",
            "check_xd_mmd": "",
            "check_idx_ma_info": strategy_config,
            "check_idx_macd_info": request.form.get("strategy_memo", ""),
            "is_send_msg": int(request.form["is_send_msg"]),
            "is_run": int(request.form["is_run"]),
        }
```

- [ ] **Step 4: Replace selection task implementation with SelectionRunner**

In `web/tradingview_zy_chart/cl_app/xuangu_tasks.py`, remove imports of Chanlun strategy modules and use:

```python
from tradingview_zy.exchange import Market, get_exchange
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.loader import load_strategy
from tradingview_zy.zixuan import ZiXuan
```

Expose `xuangu_task_config_list()` as configured strategy entries from config:

```python
    def xuangu_task_config_list(self):
        return getattr(config, "XUANGU_STRATEGIES", {})
```

Implement `run_xuangu` with this body:

```python
    def run_xuangu(self, market, task_name, frequencys, opt_type, zx_group):
        task_config = self.xuangu_task_config_list()[task_name]
        strategy = load_strategy(
            task_config["strategy_path"],
            **task_config.get("strategy_kwargs", {}),
        )
        ex = get_exchange(Market(market))
        zx = ZiXuan(market)
        stocks = zx.zx_stocks(zx_group)
        runner = SelectionRunner(exchange=ex, strategy=strategy)
        results = []
        for frequency in frequencys:
            results.extend(runner.run(market, stocks, frequency))
        self.running_tasks[task_name] = results
        return True
```

- [ ] **Step 5: Add default empty strategy config to config demo**

In `src/tradingview_zy/config.py.demo`, add:

```python
XUANGU_STRATEGIES = {}
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_selection_monitoring.py tests/test_strategy_loader.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit task wiring changes**

Run:

```bash
git add web/tradingview_zy_chart/cl_app/alert_tasks.py web/tradingview_zy_chart/cl_app/xuangu_tasks.py web/tradingview_zy_chart/cl_app/__init__.py src/tradingview_zy/config.py.demo
git commit -m "$(cat <<'EOF'
将选股和监控接入自定义策略

问题或需求描述：选股和监控需要保留入口，但不能再调用缠论信号。
修复或实现思路：通过通用策略加载器、SelectionRunner 和 MonitoringRunner 执行用户自定义策略，并复用现有任务记录外壳。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 9: Update Scripts and Disable Chanlun-Specific Entrypoints Cleanly

**Files:**
- Modify: `script/crontab/*.py`
- Modify: `script/trader/*.py`
- Rename/Modify: `script/tradingview_zy_web.config.js`
- Rename/Modify: `script/tradingview_zy_demo.config.js`
- Modify: `windows_run.bat`

- [ ] **Step 1: Replace imports in scripts**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in list(Path("script").rglob("*.py")) + [Path("windows_run.bat")]:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("from tradingview_zy", "from tradingview_zy")
    text = text.replace("import tradingview_zy", "import tradingview_zy")
    text = text.replace("tradingview_zy.", "tradingview_zy.")
    text = text.replace("web/tradingview_zy_chart", "web/tradingview_zy_chart")
    text = text.replace("web\\tradingview_zy_chart", "web\\tradingview_zy_chart")
    path.write_text(text, encoding="utf-8")
PY
```

Expected: command exits with code 0.

- [ ] **Step 2: Rename PM2 config files**

Run:

```bash
# PM2 config files were renamed during Task 3 migration.
python - <<'PY'
from pathlib import Path
for path in Path("script").glob("tradingview_zy_*.config.js"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("chanlun", "tradingview_zy")
    text = text.replace("web/tradingview_zy_chart/app.py", "web/tradingview_zy_chart/app.py")
    path.write_text(text, encoding="utf-8")
PY
```

Expected: config files are renamed if they existed.

- [ ] **Step 3: Disable scripts that still require removed Chanlun strategies**

For every script importing any removed module path below, replace the file body with the unavailable message:

Removed module path patterns:

```text
tradingview_zy.cl
tradingview_zy.cl_interface
tradingview_zy.cl_utils
tradingview_zy.strategy
tradingview_zy.xuangu
src.cl_myquant
src.cl_vnpy
src.cl_wtpy
```

Replacement body:

```python
"""Legacy Chanlun entrypoint removed from runtime."""

MESSAGE = "缠论模块已移除，请改用 docs/custom-strategy-integration.md 中的自定义策略接口。"


if __name__ == "__main__":
    print(MESSAGE)
```

Use this script to apply it:

```bash
python - <<'PY'
from pathlib import Path
patterns = [
    "tradingview_zy.cl",
    "tradingview_zy.cl_interface",
    "tradingview_zy.cl_utils",
    "tradingview_zy.strategy",
    "tradingview_zy.xuangu",
    "src.cl_myquant",
    "src.cl_vnpy",
    "src.cl_wtpy",
]
body = '''"""Legacy Chanlun entrypoint removed from runtime."""

MESSAGE = "缠论模块已移除，请改用 docs/custom-strategy-integration.md 中的自定义策略接口。"


if __name__ == "__main__":
    print(MESSAGE)
'''
for path in Path("script").rglob("*.py"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(pattern in text for pattern in patterns):
        path.write_text(body, encoding="utf-8")
PY
```

Expected: Chanlun-specific scripts become clean message-only entrypoints; K-line sync scripts that only use exchange/db remain functional.

- [ ] **Step 4: Run script import check**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python - <<'PY'
from pathlib import Path
import py_compile

for path in Path("script").rglob("*.py"):
    py_compile.compile(str(path), doraise=True)
print("script compile ok")
PY
```

Expected: prints `script compile ok`.

- [ ] **Step 5: Commit script changes**

Run:

```bash
git add script windows_run.bat
git commit -m "$(cat <<'EOF'
更新脚本入口为 tradingview_zy

问题或需求描述：脚本入口需要跟随新包名迁移，并且旧缠论入口不能在 import 阶段崩溃。
修复或实现思路：更新通用脚本 import，重命名启动配置，并将缠论专用脚本改为清晰的不可用提示。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 10: Remove Remaining Runtime Chanlun Imports

**Files:**
- Modify: all runtime Python files still reported by `tests/test_no_runtime_chanlun_imports.py`
- Test: `tests/test_no_runtime_chanlun_imports.py`

- [ ] **Step 1: Run no-runtime-imports test**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_no_runtime_chanlun_imports.py -q
```

Expected: FAIL if any runtime Python file still imports `chanlun`; PASS if all imports are removed.

- [ ] **Step 2: List remaining textual Chanlun references in runtime paths**

Run:

```bash
python - <<'PY'
from pathlib import Path
for root in [Path("src"), Path("web"), Path("script")]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".js", ".html", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "chanlun" in text or "缠论" in text:
                print(path)
PY
```

Expected: output only for files that intentionally display the removal message or archived docs references in non-runtime docs. Runtime imports must not appear.

- [ ] **Step 3: Fix remaining Python imports using explicit replacements**

For each Python file printed by Step 1, apply one of these exact changes:

```python
from tradingview_zy import config
```

becomes:

```python
from tradingview_zy import config
```

```python
from tradingview_zy.base import Market
```

becomes:

```python
from tradingview_zy.base import Market
```

```python
from tradingview_zy.exchange import get_exchange
```

becomes:

```python
from tradingview_zy.exchange import get_exchange
```

Any import from `tradingview_zy.cl`, `tradingview_zy.cl_interface`, `tradingview_zy.cl_utils`, `tradingview_zy.strategy`, or `tradingview_zy.xuangu` must be deleted, and the caller must use `tradingview_zy.strategies`, `tradingview_zy.selection`, or `tradingview_zy.monitoring` instead.

- [ ] **Step 4: Run no-runtime-imports test again**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_no_runtime_chanlun_imports.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit import cleanup**

Run:

```bash
git add src web script tests/test_no_runtime_chanlun_imports.py
git commit -m "$(cat <<'EOF'
清理运行路径旧包导入

问题或需求描述：运行路径不能继续依赖 chanlun 包名或已删除的缠论模块。
修复或实现思路：按测试报告清理剩余 import，将通用依赖切换为 tradingview_zy，并删除缠论专用依赖。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds if files changed. If Step 1 already passed and there are no file changes, skip this commit.

---

## Task 11: Write Custom Strategy and Web Right Panel Documentation

**Files:**
- Create: `docs/custom-strategy-integration.md`
- Create: `docs/web-right-panel-extension.md`

- [ ] **Step 1: Write custom strategy integration guide**

Create `docs/custom-strategy-integration.md`:

```markdown
# 自定义策略接入指南

`tradingview_zy` 的选股、监控、回测和交易信号统一通过普通 K 线数据接入，不依赖缠论结构。

## 策略类约定

策略类使用 `module:ClassName` 路径加载。类实例必须提供 `run(context)` 方法。

```python
from tradingview_zy.strategies.base import StrategyContext, StrategySignal


class CloseAboveOpenStrategy:
    name = "close_above_open"

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) <= float(last["open"]):
            return []
        return [
            StrategySignal(
                code=context.code,
                name=context.name,
                action="select",
                score=1.0,
                message="收盘价高于开盘价",
                frequency=context.frequency,
                event_time=context.now,
            )
        ]
```

## StrategyContext 字段

- `market`：市场，例如 `a`、`hk`、`us`。
- `code`：标的代码。
- `name`：标的名称。
- `frequency`：周期，例如 `5m`、`d`。
- `klines`：普通 pandas DataFrame，包含 `date`、`open`、`close`、`high`、`low`、`volume`。
- `now`：本次任务触发时间。
- `metadata`：调用方传入的附加信息。

## StrategySignal 字段

- `code`：标的代码。
- `name`：标的名称。
- `action`：`select`、`watch`、`buy`、`sell`、`open`、`close`、`ignore`。
- `score`：排序或强度分数。
- `message`：展示给用户的原因。
- `frequency`：触发周期。
- `event_time`：触发时间。
- `metadata`：策略自定义信息。

## 选股接入

在 `src/tradingview_zy/config.py` 中配置：

```python
XUANGU_STRATEGIES = {
    "收盘强势": {
        "strategy_path": "my_strategies.close_above_open:CloseAboveOpenStrategy",
        "strategy_kwargs": {},
        "task_memo": "收盘价高于开盘价",
        "frequency_memo": "选择一个 K 线周期",
        "frequency_num": 1,
    }
}
```

Web 选股任务会读取自选组股票，按配置周期拉取 K 线，然后执行策略。

## 监控接入

监控任务保存 `strategy_path` 和 `strategy_kwargs`。任务触发时会拉取当前标的 K 线，并把策略返回的 `StrategySignal` 写入监控记录。

## 回测和交易接入

回测和交易模块消费同一类策略信号。策略只负责生成信号，回测撮合和 trader 下单逻辑负责执行。
```

- [ ] **Step 2: Write Web right panel extension guide**

Create `docs/web-right-panel-extension.md`:

```markdown
# Web 端右侧扩展窗口开发指南

本文说明如何在 `web/tradingview_zy_chart` 的图表页右侧添加扩展窗口。

## 目标结构

右侧扩展窗口应作为图表页面的独立区域，不修改 TradingView 图表库源码。推荐结构：

```text
web/tradingview_zy_chart/cl_app/templates/index.html
web/tradingview_zy_chart/cl_app/static/js/right_panel.js
web/tradingview_zy_chart/cl_app/static/css/right_panel.css
```

## HTML 容器

在 `index.html` 的图表容器旁添加：

```html
<div id="main-layout">
  <div id="tv-chart-container"></div>
  <aside id="right-extension-panel" class="right-extension-panel">
    <div class="right-extension-panel__header">
      <span>扩展窗口</span>
      <button id="right-extension-panel-toggle" type="button">收起</button>
    </div>
    <div id="right-extension-panel-content" class="right-extension-panel__content"></div>
  </aside>
</div>
```

## CSS 布局

新增 `static/css/right_panel.css`：

```css
#main-layout {
  display: flex;
  width: 100%;
  height: 100vh;
}

#tv-chart-container {
  flex: 1 1 auto;
  min-width: 0;
}

.right-extension-panel {
  flex: 0 0 360px;
  border-left: 1px solid #d9d9d9;
  background: #ffffff;
  overflow: hidden;
}

.right-extension-panel.is-collapsed {
  flex-basis: 40px;
}

.right-extension-panel__header {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #eeeeee;
}

.right-extension-panel__content {
  height: calc(100% - 40px);
  overflow: auto;
  padding: 12px;
}
```

## JavaScript 初始化

新增 `static/js/right_panel.js`：

```javascript
(function () {
  function initRightPanel() {
    const panel = document.getElementById('right-extension-panel');
    const toggle = document.getElementById('right-extension-panel-toggle');
    const content = document.getElementById('right-extension-panel-content');
    if (!panel || !toggle || !content) {
      return;
    }

    toggle.addEventListener('click', function () {
      panel.classList.toggle('is-collapsed');
      toggle.innerText = panel.classList.contains('is-collapsed') ? '展开' : '收起';
    });

    window.tradingviewZyRightPanel = {
      setContent: function (html) {
        content.innerHTML = html;
      },
      clear: function () {
        content.innerHTML = '';
      }
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRightPanel);
  } else {
    initRightPanel();
  }
})();
```

## 页面引用

在 `index.html` 中引入：

```html
<link rel="stylesheet" href="/static/css/right_panel.css">
<script src="/static/js/right_panel.js"></script>
```

## 与图表联动

业务代码可以通过全局对象更新右侧窗口：

```javascript
window.tradingviewZyRightPanel.setContent('<h3>策略结果</h3><p>等待信号...</p>');
```

如果需要根据当前标的更新内容，在 TradingView symbol change 回调中读取当前 `market`、`code`、`frequency`，请求后端接口并调用 `setContent()`。

## 后端接口建议

新增接口时保持右侧窗口与图表低耦合：

```python
@app.route('/panel/strategy_results/<market>/<code>')
@login_required
def panel_strategy_results(market, code):
    return {"code": 0, "data": []}
```

接口返回普通 JSON，由 `right_panel.js` 或业务脚本渲染，不把 HTML 拼接逻辑放到后端。
```

- [ ] **Step 3: Commit docs**

Run:

```bash
git add docs/custom-strategy-integration.md docs/web-right-panel-extension.md
git commit -m "$(cat <<'EOF'
补充自定义策略和右侧窗口文档

问题或需求描述：剥离缠论后需要明确自定义策略如何接入选股监控，以及 Web 右侧扩展窗口如何开发。
修复或实现思路：新增策略接入指南和右侧扩展窗口开发指南，给出字段协议、配置示例和前后端代码示例。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Task 12: Final Validation and Web Service Check

**Files:**
- Modify only files required by validation failures.

- [ ] **Step 1: Run full planned test set**

Run:

```bash
PYTHONPATH="$PWD/src" uv run pytest tests/test_strategy_loader.py tests/test_selection_monitoring.py tests/test_web_payloads.py tests/test_no_runtime_chanlun_imports.py tests/test_backtesting_base_generic.py -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run import smoke checks**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python - <<'PY'
from tradingview_zy.base import Market
from tradingview_zy.exchange import get_exchange
from tradingview_zy.backtesting.base import Operation, POSITION, Strategy, Trader, MarketDatas
from tradingview_zy.strategies.base import StrategyContext, StrategySignal
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.monitoring import MonitoringRunner
print("imports ok", Market.A.value, Operation("SH.000001", "open", "test").opt)
PY
```

Expected: prints `imports ok a buy`.

- [ ] **Step 3: Run environment check**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python check_env.py
```

Expected: either prints `环境OK`, or prints clear configuration messages about missing `src/tradingview_zy/config.py`, Redis, MySQL, proxy, or authorization. It must not print `无法导入 chanlun 模块`.

- [ ] **Step 4: Start Web service for manual UI verification**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/app.py nobrowser
```

Expected: prints `启动成功` and listens on `config.WEB_HOST:9900`. Visit `http://127.0.0.1:9900` manually and verify:

- Home page loads.
- Market and symbol search work for at least one configured market.
- Chart requests `/tv/config`, `/tv/search`, `/tv/symbols`, and `/tv/history` without server traceback.
- No UI control says 缠论、分型、笔、线段、中枢、买卖点、背驰.
- Watchlist, generic alert, generic selection, jobs, and settings pages load or show clear configuration errors.

Stop the server with Ctrl+C after verification.

- [ ] **Step 5: Run script compile check**

Run:

```bash
PYTHONPATH="$PWD/src" uv run python - <<'PY'
from pathlib import Path
import py_compile

for path in Path("script").rglob("*.py"):
    py_compile.compile(str(path), doraise=True)
print("script compile ok")
PY
```

Expected: prints `script compile ok`.

- [ ] **Step 6: Check Git status and commit validation fixes**

Run:

```bash
git status --short
```

If validation required code fixes, commit them:

```bash
git add src web script tests docs README.md check_env.py pyproject.toml setup.py windows_run.bat
git commit -m "$(cat <<'EOF'
完成缠论剥离验收修正

问题或需求描述：最终验收暴露了迁移后的导入、Web 启动或脚本检查问题。
修复或实现思路：按测试和启动检查结果修正剩余引用，确保 tradingview_zy 基础能力可运行。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

If `git status --short` is empty, no validation commit is needed.

---

## Self-Review

Spec coverage:

- One-time package migration to `tradingview_zy`: Tasks 3 and 10.
- No runtime `chanlun` compatibility layer: Tasks 6 and 10.
- Archive source and docs: Task 2.
- Preserve Web basic K-line service: Task 7 and Task 12.
- Preserve exchange/data layer: Tasks 3, 7, 12 keep exchange imports and test Web access.
- Preserve trader execution imports: Task 12 import smoke check.
- Generic backtesting: Task 6 and Task 12.
- Generic selection and monitoring: Tasks 4, 5, 8.
- Custom strategy documentation: Task 11.
- Web right panel documentation: Task 11.
- Validation standard B and best-effort C: Task 12.

Placeholder scan: no `TBD`, `TODO`, `implement later`, or unspecified validation step is present in this plan.

Type consistency:

- `StrategyContext`, `StrategySignal`, `SelectionRunner`, `MonitoringRunner`, `load_strategy`, and `klines_to_tv_history` are introduced before use.
- `Operation(signal=...)` and `POSITION(signal=...)` are defined before their validation import smoke check.
- Web `/tv/history` uses `klines_to_tv_history` from Task 4.
