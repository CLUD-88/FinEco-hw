# HW02-1 复现说明

- **来源与快照日期：** AKShare 1.18.97；2026-09-23。行情由 `stock_zh_a_hist_tx`（腾讯）下载，参数 `start_date=20201201`、`end_date=20260916`、`adjust=''` 与 `adjust='hfq'`；历史总市值由 `stock_value_em`（东方财富）下载。选择表的行业与上市日期来自 CSMAR 上市公司基本信息年度表 2025-12-31 记录。
- **原始数据快照：** `data/` 内十个以六位代码命名的 CSV；`selection.csv` 是选股表，`download_checks.csv` 是初步覆盖检查。金额和总市值为人民币元，原始收盘价为元/股。主分析使用成交额，因为腾讯接口本次返回的原始成交量在沪深股票间有单位差异。
- **运行依赖：** Python 3.13；`pip install -r requirements.txt`。已执行 Notebook 的结果保存在 `hw02-1.ipynb` 中。
- **从快照复现：** 在本目录打开 Jupyter Notebook 或 JupyterLab，重启内核并运行 `hw02-1.ipynb` 的全部单元格。Notebook 使用相对路径 `data/`，无需再次联网。预期生成价格、累计净值、日收益率、滚动波动率、相关性和组合图，含 1,384 个共同交易日。
- **重新下载（可选）：** 将目录上层的 CSMAR 年度公司信息文件夹按原名置于 `FinEco-hw` 的上一级目录，再从本目录运行 `python code/download_data.py`。脚本对已存在的股票快照采取跳过策略；如需整体更新，应先把旧快照移出本目录并保留版本记录。

[AKShare 官方股票接口文档](https://akshare.akfamily.xyz/data/stock/stock.html)。重新下载可能改变历史复权序列或数据修订，因此批改复现应优先使用本次快照。
