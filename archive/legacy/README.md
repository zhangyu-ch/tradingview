# 历史适配源码归档

本目录只保存已经退出当前运行边界的历史源码快照。归档内容不属于
`tradingview_zy` 的可安装包、运行入口、示例或受支持能力，也不得加入
`PYTHONPATH` 后直接执行。

## `joinquant-source.zip`

- 来源：仓库根目录原 `joinquant/`，归档前固定在提交
  `e514d66eb0c993d25d10286f001621d20c5b22ff`。
- SHA-256：`2a7f493e754eaad1cc402ea338a0293c2d77c02e61c041bb689e375e25f28a08`。
- 文件：`joinquant/README.md`、`joinquant/fun.py`、两个聚宽 notebook，以及依赖该下载流程的 `notebook/导入聚宽数据.ipynb`。
- 原因：代码依赖聚宽专用 `jqdata` 环境和已经从当前运行树移除的 `cl`
  缠论模块，无法在当前项目依赖和策略协议下运行。

如需重新支持聚宽平台，应从归档中单独恢复到新分支，重新实现为普通
OHLCV/Strategy 接口，补齐依赖声明、无副作用导入测试和平台 contract tests；
不要把该 ZIP 直接解压回仓库根目录。
