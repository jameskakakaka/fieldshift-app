"""FieldShift engine: chấm điểm và xếp hạng các vòng luân canh.

Không phụ thuộc Streamlit, có thể test riêng. Mọi điểm số là ước lượng tương đối (0–100),
dựa trên đặc tính từng vòng luân canh, bằng chứng trong bài tổng quan MDPI (Su et al., 2026,
Applied Sciences 16(13):6511), khí hậu từ NASA POWER và xác suất mùa khô khắc nghiệt từ model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

AXES = {
    "water": "💧 Tiết kiệm nước",
    "soil": "🌱 Sức khỏe đất",
    "profit": "💰 Lợi nhuận",
    "stability": "🛡️ Ổn định",
}

# Màu cho từng loại cây trên lịch thời vụ
KIND_COLORS = {
    "lua": "#43A047", "mau": "#FB8C00", "dau": "#8E24AA", "tom": "#1E88E5",
    "phanxanh": "#9CCC65", "caphe": "#6D4C41", "ngo": "#FBC02D", "khoai": "#A1887F",
    "nghi": "#CFD8DC", "che_bong": "#00897B",
}

SRC_REVIEW = "Tổng quan MDPI 2026"
SRC_LOCAL = "Thực tiễn địa phương"
SRC_BASE = "Hiện trạng (mốc so sánh)"


@dataclass
class Rotation:
    key: str
    name: str
    region: str
    calendar: list            # [(nhãn, tháng bắt đầu, tháng kết thúc, loại)]
    water_dry: int            # nhu cầu nước NGỌT mùa khô: 1 rất ít ... 5 rất nhiều
    salt_tol: int             # 0 không chịu mặn ... 3 chịu mặn tốt
    legume: bool
    green_manure: bool
    n_species: int
    perennial: bool
    profit: int               # 1–5, tương đối
    labor: int                # 1–5
    needs_dry_irrigation: bool
    upland: bool              # có cây trồng cạn (màu, đậu, ngô...)
    source: str
    note: str
    evidence: list = field(default_factory=list)


ROTATIONS = [
    # ---------------- Đồng bằng sông Cửu Long ----------------
    Rotation("lua3", "Lúa 3 vụ (độc canh)", "DBSCL",
             [("Lúa Đông Xuân", 12, 3, "lua"), ("Lúa Hè Thu", 4, 7, "lua"), ("Lúa Thu Đông", 8, 11, "lua")],
             water_dry=5, salt_tol=0, legume=False, green_manure=False, n_species=1, perennial=False,
             profit=3, labor=3, needs_dry_irrigation=True, upland=False, source=SRC_BASE,
             note="Cách làm phổ biến nhưng tốn nước ngọt mùa khô, đất ít được nghỉ."),
    Rotation("lua2_mau", "Lúa – Màu – Lúa (dưa, rau màu)", "DBSCL",
             [("Lúa Đông Xuân", 11, 2, "lua"), ("Màu: dưa hấu, rau", 3, 5, "mau"), ("Lúa Hè Thu", 6, 9, "lua"),
              ("Nghỉ đất", 10, 10, "nghi")],
             water_dry=3, salt_tol=0, legume=False, green_manure=False, n_species=2, perennial=False,
             profit=4, labor=4, needs_dry_irrigation=True, upland=True, source=SRC_REVIEW,
             note="Thay một vụ lúa bằng cây màu ngắn ngày, cắt vòng đời sâu bệnh của lúa.",
             evidence=["Bài tổng quan nêu mô hình lúa – lúa – cải dầu/rau màu ở vùng trồng lúa."]),
    Rotation("lua_dau", "Lúa – Đậu xanh – Lúa", "DBSCL",
             [("Lúa Đông Xuân", 11, 2, "lua"), ("Đậu xanh", 3, 5, "dau"), ("Lúa Hè Thu", 6, 9, "lua"),
              ("Nghỉ đất", 10, 10, "nghi")],
             water_dry=2, salt_tol=0, legume=True, green_manure=False, n_species=2, perennial=False,
             profit=3, labor=3, needs_dry_irrigation=True, upland=True, source=SRC_REVIEW,
             note="Đậu xanh cần ít nước, cố định đạm cho vụ lúa sau.",
             evidence=["Mô hình lúa – đậu – lúa xuân (Nepal) trong bài tổng quan.",
                       "Cây trồng trước là họ đậu làm năng suất vụ sau tăng khoảng 23%, so với 16% khi không phải họ đậu."]),
    Rotation("lua_rau", "Lúa – Rau – Rau", "DBSCL",
             [("Lúa mùa mưa", 7, 10, "lua"), ("Rau vụ 1", 11, 1, "mau"), ("Rau vụ 2", 2, 4, "mau"),
              ("Nghỉ đất", 5, 6, "nghi")],
             water_dry=4, salt_tol=0, legume=False, green_manure=False, n_species=3, perennial=False,
             profit=5, labor=5, needs_dry_irrigation=True, upland=True, source=SRC_REVIEW,
             note="Lời cao nhưng cần nhiều công và nước tưới cho rau mùa khô.",
             evidence=["Mô hình lúa – rau – rau ở lưu vực Dương Tử và Nam Trung Quốc trong bài tổng quan."]),
    Rotation("lua_phanxanh", "Lúa – Điền thanh (phân xanh) – Lúa", "DBSCL",
             [("Lúa Đông Xuân", 11, 2, "lua"), ("Điền thanh phân xanh", 3, 4, "phanxanh"),
              ("Lúa Hè Thu", 5, 8, "lua"), ("Nghỉ đất", 9, 10, "nghi")],
             water_dry=2, salt_tol=1, legume=True, green_manure=True, n_species=2, perennial=False,
             profit=2, labor=2, needs_dry_irrigation=False, upland=True, source=SRC_REVIEW,
             note="Hy sinh một vụ để trả chất hữu cơ và đạm về đất, giảm phân bón.",
             evidence=["Mô hình lúa – tử vân anh (phân xanh) ở Dương Tử trong bài tổng quan.",
                       "Cây họ đậu có thể cố định 75–148 kg N/ha trong một số hệ thống."]),
    Rotation("lua_tom", "Lúa – Tôm (luân phiên mặn – ngọt)", "DBSCL",
             [("Nuôi tôm nước lợ", 12, 7, "tom"), ("Lúa mùa mưa", 8, 11, "lua")],
             water_dry=1, salt_tol=3, legume=False, green_manure=False, n_species=2, perennial=False,
             profit=5, labor=4, needs_dry_irrigation=False, upland=False, source=SRC_LOCAL,
             note="Dùng nước lợ mùa khô để nuôi tôm, chờ mưa rửa mặn rồi cấy lúa. Hợp vùng ven biển nhiễm mặn.",
             evidence=["Quy hoạch ĐBSCL định hướng đưa vùng ngọt hóa ven biển về luân phiên mặn – ngọt theo mùa.",
                       "Không có trong bài tổng quan: dựa trên thực tiễn ở ĐBSCL."]),

    # ---------------- Tây Nguyên ----------------
    Rotation("caphe", "Cà phê độc canh", "TAYNGUYEN",
             [("Cà phê: tưới mùa khô", 12, 4, "caphe"), ("Cà phê: mùa mưa", 5, 11, "caphe")],
             water_dry=5, salt_tol=0, legume=False, green_manure=False, n_species=1, perennial=True,
             profit=4, labor=3, needs_dry_irrigation=True, upland=True, source=SRC_BASE,
             note="Phụ thuộc nước tưới mùa khô từ hồ, giếng."),
    Rotation("caphe_xen", "Cà phê xen cây che bóng (bơ, muồng)", "TAYNGUYEN",
             [("Cà phê + cây che bóng", 12, 4, "che_bong"), ("Cà phê + cây che bóng", 5, 11, "che_bong")],
             water_dry=4, salt_tol=0, legume=True, green_manure=False, n_species=3, perennial=True,
             profit=4, labor=3, needs_dry_irrigation=True, upland=True, source=SRC_LOCAL,
             note="Tán che giúp giữ ẩm, chắn gió; thêm nguồn thu từ cây xen. Muồng là cây họ đậu.",
             evidence=["Hợp tác xã ở Tây Nguyên trồng xen bơ, sầu riêng, muồng đen để che bóng, chắn gió, giữ ẩm."]),
    Rotation("ngo_dau", "Ngô – Đậu (đậu nành, đậu xanh)", "TAYNGUYEN",
             [("Ngô vụ 1", 5, 8, "ngo"), ("Đậu vụ 2", 9, 11, "dau"), ("Phủ rơm, nghỉ mùa khô", 12, 4, "nghi")],
             water_dry=1, salt_tol=0, legume=True, green_manure=False, n_species=2, perennial=False,
             profit=3, labor=3, needs_dry_irrigation=False, upland=True, source=SRC_REVIEW,
             note="Trồng theo mùa mưa, mùa khô để đất nghỉ có phủ: gần như không cần tưới.",
             evidence=["Luân canh ngô – đậu nành (2–3 năm) là mô hình chính ở Đông Bắc và Hoàng Hoài Hải.",
                       "Cây trồng trước là họ đậu làm năng suất vụ sau tăng khoảng 23%, so với 16% khi không phải họ đậu."]),
    Rotation("dau_khoai", "Đậu – Khoai lang (vùng khô)", "TAYNGUYEN",
             [("Đậu", 5, 7, "dau"), ("Khoai lang", 8, 11, "khoai"), ("Nghỉ, phủ đất", 12, 4, "nghi")],
             water_dry=1, salt_tol=0, legume=True, green_manure=True, n_species=2, perennial=False,
             profit=3, labor=3, needs_dry_irrigation=False, upland=True, source=SRC_REVIEW,
             note="Phỏng theo mô hình đậu/phân xanh – khoai tây ở vùng khô hạn.",
             evidence=["Luân canh đậu/phân xanh – khoai tây giảm 11,2–26,1% lượng nước so với trồng khoai tây liên tục."]),
    Rotation("rau_dau", "Rau – Đậu – Rau (vùng có nước tưới)", "TAYNGUYEN",
             [("Rau vụ 1", 12, 3, "mau"), ("Đậu", 4, 6, "dau"), ("Rau vụ 2", 7, 11, "mau")],
             water_dry=4, salt_tol=0, legume=True, green_manure=False, n_species=3, perennial=False,
             profit=5, labor=5, needs_dry_irrigation=True, upland=True, source=SRC_REVIEW,
             note="Lời cao, cần nước tưới chủ động và nhiều công.",
             evidence=["Luân canh đa dạng giảm thiệt hại năng suất trong năm hạn 14–90% so với độc canh."]),
]

ROT_BY_KEY = {r.key: r for r in ROTATIONS}

CURRENT_OPTIONS = {
    "DBSCL": {"Lúa 3 vụ": "lua3", "Lúa 2 vụ + màu": "lua2_mau", "Lúa – tôm": "lua_tom",
              "Lúa xen đậu": "lua_dau", "Rau màu": "lua_rau", "Khác": None},
    "TAYNGUYEN": {"Cà phê": "caphe", "Cà phê xen cây": "caphe_xen", "Ngô, đậu": "ngo_dau",
                  "Rau": "rau_dau", "Khác": None},
}

SOILS = ["Phù sa ngọt", "Đất phèn", "Đất mặn ven biển", "Đất cát", "Đất đỏ bazan", "Đất xám"]
WATER_SOURCES = ["Kênh, sông nước ngọt quanh năm", "Giếng khoan", "Chỉ có nước mưa"]
SALINITY = ["Không", "Nhẹ (vài tuần)", "Nặng (2–4 tháng)"]


def _axes(r: Rotation) -> dict:
    water = 100 - (r.water_dry - 1) * 25
    soil = 25 + 20 * r.legume + 20 * r.green_manure + 10 * min(r.n_species - 1, 3)
    soil += 10 if (r.perennial and r.n_species > 1) else 0
    soil -= 10 if (r.n_species == 1) else 0
    profit = r.profit * 20
    stability = 30 + 12 * min(r.n_species - 1, 3) + (5 - r.water_dry) * 8 + 10 * r.legume
    return {k: float(max(0, min(100, v))) for k, v in
            {"water": water, "soil": soil, "profit": profit, "stability": stability}.items()}


def recommend(region: str, inputs: dict, climate: dict | None = None, p_drought: float | None = None):
    """Xếp hạng các vòng luân canh cho một ruộng.

    inputs: current (key hoặc None), soil, water_source, salinity (0/1/2), priorities {axis: 1–5}
    climate: annual_rain, dry_rain, soil_dry_now (bool)
    p_drought: xác suất mùa khô tới khắc nghiệt (0–1); None = không có dự báo, dùng 1/3
    """
    climate = climate or {}
    p = 1 / 3 if p_drought is None else float(p_drought)
    pri = inputs.get("priorities", {a: 3 for a in AXES})
    wsum = sum(pri.values()) or 1
    sal = int(inputs.get("salinity", 0))
    soil_type = inputs.get("soil", SOILS[0])
    src = inputs.get("water_source", WATER_SOURCES[0])
    if soil_type == "Đất mặn ven biển":
        sal = max(sal, 1)

    results = []
    for r in [x for x in ROTATIONS if x.region == region]:
        ax = _axes(r)
        feas, reasons = 1.0, []

        # Mặn
        gap = sal - r.salt_tol
        if gap > 0:
            feas *= 1 - 0.25 * gap
            reasons.append(f"⚠️ Ruộng nhiễm mặn {SALINITY[sal].lower()}: vòng này chịu mặn kém.")
        elif sal >= 1 and r.salt_tol >= 2:
            ax["stability"] = min(100, ax["stability"] + 15)
            reasons.append("✅ Tận dụng được nước lợ mùa khô thay vì chống mặn.")
        if r.salt_tol >= 3 and sal == 0:
            feas *= 0.3
            reasons.append("⛔ Cần nguồn nước lợ: chỉ hợp vùng ven biển nhiễm mặn. "
                           "Đưa nước mặn vào vùng ngọt sẽ làm hỏng đất.")

        # Nguồn nước
        dry_rain = climate.get("dry_rain")
        if src == WATER_SOURCES[2] and r.needs_dry_irrigation:
            feas *= 0.5
            msg = "⚠️ Cần tưới mùa khô nhưng ruộng chỉ có nước mưa"
            if dry_rain is not None:
                msg += f" (mùa khô ở đây trung bình chỉ khoảng {dry_rain:,.0f} mm mưa)"
            reasons.append(msg + ".")
        if src == WATER_SOURCES[1] and r.water_dry >= 4 and region == "DBSCL":
            ax["stability"] = max(0, ax["stability"] - 10)
            reasons.append("⚠️ Bơm nhiều nước ngầm mùa khô góp phần làm sụt lún đất ở ĐBSCL.")

        # Loại đất
        if soil_type == "Đất phèn" and r.upland and not r.perennial:
            feas *= 0.9
            reasons.append("ℹ️ Đất phèn: cây màu cần lên liếp, rửa phèn trước khi trồng.")
        if soil_type == "Đất cát" and any(c[3] == "lua" for c in r.calendar):
            feas *= 0.9
            reasons.append("ℹ️ Đất cát giữ nước kém, lúa tốn nước hơn.")

        # Dự báo mùa khô
        excess = max(0.0, p - 1 / 3) * 1.5
        penalty = excess * (r.water_dry - 1) * 6
        if climate.get("soil_dry_now"):
            penalty += 2 * (r.water_dry - 1)
        if r.key == "lua_tom" and p > 0.5:
            penalty += 6
            reasons.append("⚠️ Mùa khô khắc nghiệt dễ làm mưa đến muộn, chưa kịp rửa mặn để cấy lúa.")
        if p > 0.5 and r.water_dry <= 2:
            reasons.append(f"✅ Dự báo mùa khô tới có {p:.0%} khả năng khắc nghiệt: vòng này cần ít nước ngọt.")
        elif p > 0.5 and r.water_dry >= 4:
            reasons.append(f"⚠️ Dự báo mùa khô tới có {p:.0%} khả năng khắc nghiệt: vòng này cần nhiều nước.")

        # Bằng chứng
        if r.legume:
            reasons.append("🌱 Có cây họ đậu: bổ sung đạm tự nhiên, giảm phân bón.")
        if r.n_species >= 2:
            reasons.append("🔄 Đa dạng cây giúp cắt vòng sâu bệnh, giảm thiệt hại năm hạn.")
        if r.n_species == 1:
            reasons.append("ℹ️ Độc canh: đất không được nghỉ, sâu bệnh dễ tích tụ.")

        base = sum(pri[a] * ax[a] for a in AXES) / wsum
        total = max(0.0, min(100.0, base * feas - penalty))

        badges = []
        if r.legume:
            badges.append("🌱 Có cây họ đậu")
        if r.salt_tol >= 2:
            badges.append("🧂 Chịu mặn")
        if r.water_dry <= 2:
            badges.append("💧 Ít nước mùa khô")
        if r.n_species >= 3:
            badges.append("🔄 Đa dạng cây")
        badges.append("📚 " + r.source if r.source == SRC_REVIEW else "🏡 " + r.source)

        results.append({
            "key": r.key, "name": r.name, "total": round(total, 1), **{a: round(v, 1) for a, v in ax.items()},
            "feasibility": round(feas, 2), "forecast_penalty": round(penalty, 1),
            "is_current": r.key == inputs.get("current"), "reasons": reasons, "badges": badges,
            "note": r.note, "evidence": r.evidence, "calendar": r.calendar, "source": r.source,
        })

    results.sort(key=lambda d: d["total"], reverse=True)
    for i, d in enumerate(results, 1):
        d["rank"] = i
    return results


def plan_text(rec: dict, place: str, p_drought: float | None) -> str:
    """Kế hoạch dạng văn bản để nông dân tải về."""
    lines = [f"KẾ HOẠCH LUÂN CANH GỢI Ý – {place}", "=" * 50, f"Vòng luân canh: {rec['name']}",
             f"Điểm phù hợp: {rec['total']:.0f}/100", ""]
    if p_drought is not None:
        lines.append(f"Xác suất mùa khô tới khắc nghiệt: {p_drought:.0%}")
    lines += ["", "LỊCH THỜI VỤ:"]
    for label, s, e, _ in rec["calendar"]:
        lines.append(f"  - {label}: tháng {s} đến tháng {e}")
    lines += ["", "VÌ SAO:"] + [f"  - {x}" for x in rec["reasons"]]
    if rec["evidence"]:
        lines += ["", "BẰNG CHỨNG:"] + [f"  - {x}" for x in rec["evidence"]]
    lines += ["", "Lưu ý: lịch thời vụ là minh họa, cần điều chỉnh theo khuyến cáo của khuyến nông địa phương.",
              "Dữ liệu: NASA POWER; mô hình FieldShift (NASA Space Apps 2026)."]
    return "\n".join(lines)
