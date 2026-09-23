"""从授权的 CSMAR 原始下载构造 2005—2015 年房地产 A 股面板。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)


def source_file(pattern: str) -> Path:
    matches = list(SOURCE.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one source for {pattern}, found {len(matches)}")
    return matches[0]


def read_source(pattern: str, columns: list[str]) -> pd.DataFrame:
    return pd.read_csv(
        source_file(pattern),
        dtype=str,
        usecols=columns,
        encoding="utf-8-sig",
        low_memory=False,
    )


def annual_consolidated(frame: pd.DataFrame) -> pd.DataFrame:
    # CSMAR Typrep=A 为合并报表；仅保留年末资产负债表和年度利润表。
    frame = frame.loc[
        frame["Typrep"].eq("A") & frame["Accper"].str.endswith("12-31")
    ].copy()
    frame["year"] = frame["Accper"].str[:4].astype(int)
    frame = frame.loc[frame.year.between(2004, 2015)]
    if frame.duplicated(["Stkcd", "year"]).any():
        raise ValueError("Duplicate consolidated company-year source records")
    return frame


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator.gt(0)))


def main() -> None:
    listing = read_source(
        "上市公司基本信息年度表*/STK_LISTEDCOINFOANL.csv",
        ["Symbol", "ShortName", "EndDate", "IndustryName", "IndustryCode", "LISTINGDATE", "LISTINGSTATE"],
    )
    listing = listing.loc[listing.EndDate.between("2005-12-31", "2015-12-31")]
    flow = [{"step": "年度上市公司原始记录", "firm_years": len(listing), "firms": listing.Symbol.nunique()}]
    listing = listing.loc[listing.IndustryName.str.contains("房地产", na=False)].copy()
    flow.append({"step": "当年房地产行业", "firm_years": len(listing), "firms": listing.Symbol.nunique()})
    listing = listing.loc[listing.Symbol.str.match(r"^(0|3|6)\d{5}$", na=False)].copy()
    flow.append({"step": "剔除 B 股、保留 A 股代码", "firm_years": len(listing), "firms": listing.Symbol.nunique()})
    listing["year"] = listing.EndDate.str[:4].astype(int)
    if listing.duplicated(["Symbol", "year"]).any():
        raise ValueError("Duplicate company-year listing records")
    listing = listing.rename(columns={"Symbol": "code", "ShortName": "name"})

    ownership = read_source(
        "中国上市公司股权性质文件*/EN_EquityNatureAll.csv",
        ["Symbol", "EndDate", "ActualControllerName", "ActualControllerNatureID", "EquityNature", "EquityNatureID"],
    )
    ownership = ownership.loc[ownership.EndDate.between("2005-12-31", "2015-12-31")].copy()
    ownership["year"] = ownership.EndDate.str[:4].astype(int)
    ownership = ownership.rename(columns={"Symbol": "code"}).drop(columns="EndDate")
    if ownership.duplicated(["code", "year"]).any():
        raise ValueError("Duplicate ownership company-year records")
    panel = listing.merge(ownership, on=["code", "year"], how="left", validate="one_to_one", indicator="ownership_merge")
    flow.append({"step": "合并产权信息（保留产权缺失）", "firm_years": len(panel), "firms": panel.code.nunique()})
    panel["ownership"] = np.select(
        [panel.EquityNatureID.eq("1"), panel.EquityNatureID.eq("2"), panel.EquityNatureID.isna() | panel.EquityNatureID.eq("NaN")],
        ["国有", "民营", "产权不明"],
        default="其他",
    )

    balance = annual_consolidated(read_source(
        "资产负债表194100134*/FS_Combas.csv",
        ["Stkcd", "Accper", "Typrep", "A001101000", "A001000000", "A002100000", "A002000000", "A003000000"],
    ))
    balance = balance.rename(columns={
        "Stkcd": "code", "A001101000": "cash", "A001000000": "assets",
        "A002100000": "current_liabilities", "A002000000": "liabilities", "A003000000": "equity",
    })
    balance = balance.drop(columns=["Accper", "Typrep"])
    for column in ["cash", "assets", "current_liabilities", "liabilities", "equity"]:
        balance[column] = pd.to_numeric(balance[column], errors="coerce")
    previous = balance[["code", "year", "assets", "equity"]].copy()
    previous["year"] += 1
    previous = previous.rename(columns={"assets": "assets_lag", "equity": "equity_lag"})
    panel = panel.merge(balance, on=["code", "year"], how="left", validate="one_to_one", indicator="balance_merge")
    panel = panel.merge(previous, on=["code", "year"], how="left", validate="one_to_one", indicator="lag_merge")
    flow.append({"step": "匹配当年及上年合并资产负债表", "firm_years": len(panel), "firms": panel.code.nunique()})

    borrowings = annual_consolidated(read_source(
        "资产负债表204413575*/FS_Combas.csv",
        ["Stkcd", "Accper", "Typrep", "A002101000", "A002201000"],
    ))
    borrowings = borrowings.rename(columns={
        "Stkcd": "code", "A002101000": "short_borrowing", "A002201000": "long_borrowing",
    }).drop(columns=["Accper", "Typrep"])
    for column in ["short_borrowing", "long_borrowing"]:
        borrowings[column] = pd.to_numeric(borrowings[column], errors="coerce")
    panel = panel.merge(borrowings, on=["code", "year"], how="left", validate="one_to_one", indicator="borrow_merge")

    income = annual_consolidated(read_source(
        "利润表194142382*/FS_Comins.csv",
        ["Stkcd", "Accper", "Typrep", "B002000000"],
    ))
    income = income.rename(columns={"Stkcd": "code", "B002000000": "net_profit"}).drop(columns=["Accper", "Typrep"])
    income["net_profit"] = pd.to_numeric(income.net_profit, errors="coerce")
    panel = panel.merge(income, on=["code", "year"], how="left", validate="one_to_one", indicator="income_merge")
    flow.append({"step": "匹配借款与年度合并净利润", "firm_years": len(panel), "firms": panel.code.nunique()})

    panel["avg_assets"] = (panel.assets + panel.assets_lag) / 2
    panel["avg_equity"] = (panel.equity + panel.equity_lag) / 2
    panel["asset_liability_ratio"] = safe_ratio(panel.liabilities, panel.assets)
    # 短、长期借款为资产负债表科目，含非银行金融机构借款；此处采用用户确认的代理口径。
    panel["bankloan"] = safe_ratio(panel.short_borrowing + panel.long_borrowing, panel.liabilities)
    panel["short_liability_share"] = safe_ratio(panel.current_liabilities, panel.liabilities)
    panel["ROA"] = safe_ratio(panel.net_profit, panel.avg_assets)
    panel["ROE"] = safe_ratio(panel.net_profit, panel.avg_equity)
    panel["Cash_TA"] = safe_ratio(panel.cash, panel.assets)
    flow.append({"step": "完成六项指标（缺失保留）", "firm_years": len(panel), "firms": panel.code.nunique()})
    panel = panel.sort_values(["year", "code"])
    panel.to_csv(DATA / "panel_restricted.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(flow).to_csv(DATA / "sample_flow.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(flow).to_string(index=False))
    print("ownership", panel.ownership.value_counts().to_dict())
    print("missing", panel[["asset_liability_ratio", "bankloan", "short_liability_share", "ROA", "ROE", "Cash_TA"]].isna().sum().to_dict())


if __name__ == "__main__":
    main()
