# 受限数据位置

`panel_restricted.csv` 是本地 CSMAR 公司级衍生面板；`sample_flow.csv` 是同次筛选日志。两者被上级 `.gitignore` 排除，不应推送到公开 GitHub 仓库。原始下载文件约 6.8 MB（上市公司年度信息）、2.6 MB（产权）、13.6 MB（利润表）、28.8 MB 与 54.9 MB（两份资产负债表），均位于 `FinEco-hw` 上一级目录相应 CSMAR 解压文件夹中。

访问入口：学校授权的 CSMAR 数据库（需中山大学账户权限；无公开下载地址）。本地复现顺序：将原始文件按原文件夹名称放在指定位置，安装依赖，运行 `hw02-2/code/prepare_data.py`，再运行 Notebook。字段、筛选和计算规则详见 [第二题说明](../README.md) 与 Notebook。
