# 供应链与依赖证据

## 唯一安装契约

`pyproject.toml` 是直接依赖的声明，`uv.lock` 是唯一受支持的解析结果。依赖解析、安装脚本和 CI 的审计基线固定为 uv `0.10.0`，所有手工安装、Windows 安装和 CI 安装都必须执行：

```bash
uv sync --locked
```

仓库不再提供 `requirements.txt`、`setup.py`、Pipfile 或其他可绕过锁文件的安装入口。Tests workflow 的六个 job 都通过 `uv sync --locked` 安装；其中 `supply-chain-contracts` 还会先执行 `uv lock --check`。只读的 repository-hygiene workflow 不安装依赖，直接运行标准库治理脚本。`UV_PYTHON_DOWNLOADS=never` 防止 setup-python 已提供 3.11 后又静默下载其他解释器。

## 本地 wheel

`audit/supply-chain/local-artifacts.json` 是 `package/` 的完整许可清单。每一项记录：

- 仓库相对路径、包名、版本和平台 marker；
- 文件大小和 SHA-256；
- `uv.lock` 中的锁定证据；
- 可证明的来源、上游项目与下载 URL；
- wheel `METADATA` 和许可证文件哈希。

`package/` 不允许存在清单外文件。TA-Lib wheel 的字节哈希与 `uv.lock` 中的 registry URL 匹配；pytdx 的原始下载 URL没有留在用户提供的基线中，因此清单明确记录为未知，并保留人工许可证复核标记，不猜测来源。

过去提交的 `script/bin/uv*.exe` 已删除。`windows_install.bat` 只接受 PATH 中精确的 uv `0.10.0`，与 CI 的依赖审查基线一致。`windows_run.bat` 是已有环境的启动入口，当前接受 uv 0.10 或 0.11，但它调用默认 `uv run`，可能按 uv 行为同步环境。需要锁文件不变且安装可审计时，应先运行 `windows_install.bat` 或显式执行 `uv sync --locked`。

## 生成证据

以下文件从 `uv.lock` 和本地制品清单确定性生成：

- `audit/supply-chain/sbom.cdx.json`：CycloneDX 1.6 锁图清单；
- `audit/supply-chain/license-report.json`：离线许可证元数据库存；
- `audit/supply-chain/vulnerability-report.json`：明确标注“离线未执行”的占位证据。

复核或重生成：

```bash
uv run --locked python script/remediation/check_supply_chain.py
uv run --locked python script/remediation/generate_supply_chain_artifacts.py --check
uv run --locked python script/remediation/generate_supply_chain_artifacts.py
```

CI 在完整 `uv sync --locked` 后，会向 `.artifacts/supply-chain` 生成一份安装环境支持的许可证报告，再调用 OSV `querybatch` 生成实时漏洞报告。该目录作为 `supply-chain-evidence` workflow artifact 保存，不回写仓库快照。

## 漏洞策略

`audit/supply-chain/vulnerability-policy.json` 默认没有豁免。任何 OSV advisory 都使 `supply-chain-contracts` 失败。确需暂时接受时，条目必须包含 advisory ID、规范化包名、负责人、原因和到期日期；过期或重复条目由 checker 拒绝。

在线扫描失败、响应数量与请求不一致或返回无效 JSON 时均 fail closed。离线环境没有完成实时查询时，不得把 committed report 的空 advisory 数组描述为安全结论。

## 证据限制

SBOM 描述锁定的 Python 依赖图，不自动覆盖操作系统包、浏览器运行时、真实券商客户端或容器镜像。许可证报告是元数据库存，不是法律建议。OSV 结果受数据库覆盖面和包名/版本匹配限制；重要供应商仍应结合其安全公告与制品签名流程复核。
