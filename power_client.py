"""Lấy dữ liệu NASA POWER cho một điểm ruộng và tính các chỉ số khí hậu cho app."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

POINT_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = ["PRECTOTCORR", "T2M", "T2M_MAX", "GWETROOT"]
DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "power_cache"
BASE = (1991, 2020)

REGIONS = {
    "DBSCL": {"name": "Đồng bằng sông Cửu Long", "dry_months": (12, 1, 2, 3, 4),
              "known_drought": [2016, 2020, 2024]},
    "TAYNGUYEN": {"name": "Tây Nguyên", "dry_months": (11, 12, 1, 2, 3, 4),
                  "known_drought": [2002, 2014, 2016, 2024]},
}

# Toạ độ gần đúng của trung tâm các địa phương
PRESETS = {
    "DBSCL": {"Cà Mau": (9.18, 105.15), "Bạc Liêu": (9.29, 105.72), "Sóc Trăng": (9.60, 105.97),
              "Trà Vinh": (9.94, 106.34), "Bến Tre": (10.24, 106.37), "Cần Thơ": (10.03, 105.78),
              "Long Xuyên": (10.38, 105.44), "Rạch Giá": (10.01, 105.08)},
    "TAYNGUYEN": {"Buôn Ma Thuột": (12.67, 108.04), "Krông Pắk": (12.70, 108.30), "Pleiku": (13.98, 108.00),
                  "Kon Tum": (14.35, 108.00), "Gia Nghĩa": (12.00, 107.69), "Bảo Lộc": (11.55, 107.81),
                  "Đà Lạt": (11.94, 108.44)},
}

MONTH_LABELS = [f"Th{m}" for m in range(1, 13)]


def _to_df(js: dict) -> pd.DataFrame:
    feats = js["features"] if "features" in js else [js]
    fill = js.get("header", {}).get("fill_value", -999)
    rows = []
    for f in feats:
        for p, series in f["properties"]["parameter"].items():
            for d, v in series.items():
                rows.append((d, p, v))
    long = pd.DataFrame(rows, columns=["date", "param", "value"])
    long["date"] = pd.to_datetime(long["date"], format="%Y%m%d")
    long["value"] = pd.to_numeric(long["value"], errors="coerce").replace(fill, np.nan)
    wide = long.pivot(index="date", columns="param", values="value").sort_index()
    wide.columns.name = None
    return wide


def fetch_point(lat: float, lon: float, start: str = "19910101", end: str | None = None,
                timeout: int = 180) -> tuple[pd.DataFrame, str]:
    """Trả về (bảng dữ liệu ngày, nguồn). Có cache trên đĩa; mất mạng thì dùng bản cache gần nhất."""
    end = end or (pd.Timestamp.today() - pd.Timedelta(days=4)).strftime("%Y%m%d")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{lat:.3f}_{lon:.3f}"
    path = CACHE_DIR / f"{stem}_{start}_{end}.csv"
    if path.exists():
        return pd.read_csv(path, index_col="date", parse_dates=["date"]), "cache"
    q = {"parameters": ",".join(PARAMS), "community": "ag", "latitude": lat, "longitude": lon,
         "start": start, "end": end, "format": "json", "units": "metric", "time-standard": "lst"}
    try:
        r = requests.get(POINT_URL, params=q, timeout=timeout)
        r.raise_for_status()
        df = _to_df(r.json())
        df.to_csv(path)
        return df, "api"
    except Exception:
        old = sorted(CACHE_DIR.glob(f"{stem}_*.csv"))
        if old:
            return pd.read_csv(old[-1], index_col="date", parse_dates=["date"]), "cache-cu"
        raise


def _base(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[f"{BASE[0]}-01-01":f"{BASE[1]}-12-31"]


def monthly_normals(df: pd.DataFrame) -> pd.DataFrame:
    b = _base(df)
    rain = b["PRECTOTCORR"].resample("MS").sum(min_count=20)
    out = pd.DataFrame({
        "rain_mm": rain.groupby(rain.index.month).mean(),
        "t2m": b["T2M"].groupby(b.index.month).mean(),
        "tmax": b["T2M_MAX"].groupby(b.index.month).mean(),
    })
    out.index.name = "month"
    return out.reindex(range(1, 13))


def this_year_rain(df: pd.DataFrame) -> tuple[pd.Series, int, pd.Timestamp]:
    last = df.index.max()
    cur = df.loc[str(last.year), "PRECTOTCORR"].resample("MS").sum(min_count=1)
    s = pd.Series(cur.values, index=cur.index.month).reindex(range(1, 13))
    return s, last.year, last


def dry_seasons(df: pd.DataFrame, dry_months) -> pd.Series:
    s = df[df.index.month.isin(dry_months)]
    season = np.where(s.index.month >= dry_months[0], s.index.year + 1, s.index.year)
    g = s.groupby(season)["PRECTOTCORR"].agg(["sum", "count"])
    g = g[g["count"] >= 0.9 * g["count"].max()]
    return g["sum"].rename("rain_mm")


def soil_band(df: pd.DataFrame, days: int = 150):
    """Độ ẩm đất vùng rễ gần đây so với dải bình thường (phân vị 10–50–90 cùng thời điểm trong năm)."""
    b = _base(df)["GWETROOT"].dropna()
    q = b.groupby(b.index.dayofyear).quantile([0.1, 0.5, 0.9]).unstack()
    q.columns = ["p10", "p50", "p90"]
    q = q.reindex(range(1, 367)).interpolate(limit_direction="both")
    pad = pd.concat([q.iloc[-15:], q, q.iloc[:15]])
    q = pad.rolling(15, center=True, min_periods=1).mean().iloc[15:-15]
    recent = df["GWETROOT"].dropna().iloc[-days:]
    band = q.reindex(recent.index.dayofyear)
    band.index = recent.index
    doy = b.index.dayofyear
    last_doy = recent.index[-1].dayofyear
    diff = np.minimum(np.abs(doy - last_doy), 366 - np.abs(doy - last_doy))
    same_time = b[diff <= 7]
    pct = float((same_time < recent.iloc[-1]).mean() * 100) if len(same_time) else float("nan")
    return recent, band, pct


def hot_days(df: pd.DataFrame):
    """Số ngày nóng bất thường mỗi năm: T2M_MAX vượt mức của 10% ngày nóng nhất giai đoạn 1991–2020."""
    thr = float(_base(df)["T2M_MAX"].quantile(0.9))
    t = df["T2M_MAX"]
    counts = t.groupby(t.index.year).agg(lambda x: int((x >= thr).sum()))
    n = t.groupby(t.index.year).count()
    return counts[n >= 330], thr


def climate_summary(df: pd.DataFrame, region: str) -> dict:
    b = _base(df)
    annual = b["PRECTOTCORR"].groupby(b.index.year).sum()
    ds = dry_seasons(df, REGIONS[region]["dry_months"])
    ds_base = ds.loc[BASE[0] + 1:BASE[1]]
    normals = monthly_normals(df)
    _, _, pct = soil_band(df)
    return {
        "annual_rain": float(annual.mean()),
        "dry_rain": float(ds_base.mean()) if len(ds_base) else float("nan"),
        "driest_month": int(normals["rain_mm"].idxmin()),
        "wettest_month": int(normals["rain_mm"].idxmax()),
        "soil_pct": pct,
        "soil_dry_now": bool(pct < 20) if not math.isnan(pct) else False,
        "last_date": df.index.max(),
    }


def load_forecast(region: str, lat: float, lon: float) -> dict | None:
    """Đọc file forecast_<REGION>.csv do notebook train model sinh ra; lấy ô gần ruộng nhất."""
    path = DATA_DIR / f"forecast_{region}.csv"
    if not path.exists():
        return None
    f = pd.read_csv(path)
    if f.empty or "p_kho_han" not in f:
        return None
    d = np.hypot(f["lat"] - lat, (f["lon"] - lon) * math.cos(math.radians(lat)))
    i = int(d.idxmin())
    return {"p": float(f.loc[i, "p_kho_han"]), "cell": str(f.loc[i, "cell"]), "dist_km": float(d.min() * 111)}


def next_dry_season(region: str, today: pd.Timestamp | None = None) -> int:
    """Năm đặt tên cho mùa khô sắp tới (mùa "2027" kết thúc vào tháng 4/2027)."""
    today = today or pd.Timestamp.today()
    return today.year + 1 if today.month >= 5 else today.year
