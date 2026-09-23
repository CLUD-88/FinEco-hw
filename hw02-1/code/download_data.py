"""下载 HW02-1 的固定日期数据快照；数据单位保留 AKShare 原始定义。"""
from __future__ import annotations

import json
import time
from pathlib import Path

import akshare as ak
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
START = "20201201"
END = "20260916"
STOCKS = [
    ("000001", "平安银行", "银行", "银行业代表"),
    ("600036", "招商银行", "银行", "股份制银行代表"),
    ("600519", "贵州茅台", "酒、饮料和精制茶制造业", "白酒龙头"),
    ("000858", "五粮液", "酒、饮料和精制茶制造业", "白酒行业对照"),
    ("000333", "美的集团", "电气机械和器材制造业", "家电制造代表"),
    ("002415", "海康威视", "计算机、通信和其他电子设备制造业", "电子设备代表"),
    ("600276", "恒瑞医药", "医药制造业", "医药制造代表"),
    ("600011", "华能国际", "电力、热力生产和供应业", "公用事业代表"),
    ("601888", "中国中免", "商务服务业", "消费服务代表"),
    ("600104", "上汽集团", "汽车制造业", "汽车制造代表"),
]


def request_with_retry(callback, label: str):
    for attempt in range(3):
        try:
            result = callback()
            if result is None or result.empty:
                raise ValueError(f"{label}: empty response")
            return result
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def main() -> None:
    listing = pd.read_csv(
        next(ROOT.parents[1].glob("上市公司基本信息年度表*/STK_LISTEDCOINFOANL.csv")),
        dtype=str,
        encoding="utf-8-sig",
    )
    listing = listing.loc[listing["EndDate"].eq("2025-12-31")].set_index("Symbol")
    selection = []
    checks = []
    for code, name, industry, reason in STOCKS:
        symbol = ("sh" if code.startswith("6") else "sz") + code
        record = listing.loc[code]
        selection.append(
            {
                "代码": code,
                "简称": name,
                "行业": industry,
                "上市日期": record["LISTINGDATE"],
                "选股理由": reason,
                "行业代码": record["IndustryCode"],
                "CSMAR行业名称": record["IndustryName"],
                "分类日期": "2025-12-31",
            }
        )
        output = DATA / f"{code}.csv"
        if output.exists():
            print(f"SKIP {code}: snapshot exists", flush=True)
            frame = pd.read_csv(output)
        else:
            raw = request_with_retry(
                lambda: ak.stock_zh_a_hist_tx(
                    symbol=symbol, start_date=START, end_date=END, adjust=""
                ),
                f"{code} raw",
            )
            adjusted = request_with_retry(
                lambda: ak.stock_zh_a_hist_tx(
                    symbol=symbol, start_date=START, end_date=END, adjust="hfq"
                ),
                f"{code} hfq",
            )
            value = request_with_retry(lambda: ak.stock_value_em(symbol=code), f"{code} value")
            raw["date"] = pd.to_datetime(raw["date"])
            adjusted["date"] = pd.to_datetime(adjusted["date"])
            value["数据日期"] = pd.to_datetime(value["数据日期"])
            adjusted = adjusted[["date", "close"]].rename(columns={"close": "close_hfq"})
            value = value[["数据日期", "总市值"]].rename(
                columns={"数据日期": "date", "总市值": "market_cap_yuan"}
            )
            frame = raw.merge(adjusted, on="date", how="left", validate="one_to_one")
            frame = frame.merge(value, on="date", how="left", validate="one_to_one")
            frame.insert(0, "code", code)
            frame = frame.sort_values("date")
            frame.to_csv(output, index=False, encoding="utf-8-sig")
            time.sleep(0.5)
        sample = frame.loc[(frame.date >= "2021-01-01") & (frame.date <= "2026-09-16")]
        check = {
            "code": code,
            "rows": len(sample),
            "first": str(sample.date.iloc[0]),
            "last": str(sample.date.iloc[-1]),
            "missing_hfq": int(sample.close_hfq.isna().sum()),
            "missing_market_cap": int(sample.market_cap_yuan.isna().sum()),
        }
        checks.append(check)
        print(json.dumps(check, ensure_ascii=True), flush=True)
    pd.DataFrame(selection).to_csv(DATA / "selection.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(DATA / "download_checks.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
