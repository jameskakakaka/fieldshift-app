"""FieldShift – trợ lý chọn mùa vụ và luân canh từ dữ liệu NASA.

Chạy:  streamlit run app.py
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import engine as en
import power_client as pc

st.set_page_config(page_title="FieldShift – Trợ lý luân canh", page_icon="🌾", layout="wide")

GREEN, GREEN_D, ORANGE, RED, BLUE, GRAY = "#43A047", "#1B5E20", "#FB8C00", "#E53935", "#1E88E5", "#78909C"
TOP_COLORS = ["#2E7D32", "#1E88E5", "#FB8C00", "#8E24AA"]
PLOT_CFG = {"displayModeBar": False}

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.hero {background: linear-gradient(120deg, #1B5E20 0%, #43A047 55%, #9CCC65 100%);
       color: #fff; padding: 22px 28px; border-radius: 20px; margin-bottom: 18px;
       box-shadow: 0 6px 20px rgba(27, 94, 32, .25);}
.hero h1 {color: #fff; margin: 0; font-size: 2.1rem; letter-spacing: .3px;}
.hero p {margin: 6px 0 0 0; font-size: 1.05rem; opacity: .95;}
.card {background: #fff; border-radius: 18px; padding: 16px 18px; border: 1px solid #E5EDE0;
       box-shadow: 0 3px 12px rgba(0,0,0,.05); height: 100%; transition: transform .2s ease, box-shadow .2s ease;}
.card:hover {transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,.08);}
.card .label {color: #5f6b5a; font-size: .92rem;}
.card .value {font-size: 2rem; font-weight: 800; line-height: 1.25;}
.card .sub {color: #7a8574; font-size: .86rem;}
.tip {background: #FFFBEA; border-left: 6px solid #F9A825; border-radius: 14px; padding: 14px 18px; height: 100%;}
.tip li {margin-bottom: 6px;}
.rec {background: #fff; border-radius: 20px; padding: 18px 20px; border: 2px solid #E5EDE0;
      box-shadow: 0 4px 16px rgba(0,0,0,.06); transition: transform .2s ease;}
.rec:hover {transform: translateY(-4px);}
.rec.top {border-color: #43A047; background: linear-gradient(180deg, #F1F8E9 0%, #FFFFFF 45%);}
.pill {display: inline-block; background: #2E7D32; color: #fff; border-radius: 999px; padding: 2px 12px; font-size: .82rem;}
.rec h3 {margin: 8px 0 2px 0; font-size: 1.15rem; color: #1F2A1C;}
.score {font-size: 2.4rem; font-weight: 800; color: #2E7D32; line-height: 1.1;}
.score small {font-size: .95rem; color: #7a8574; font-weight: 500;}
.axis {display: flex; align-items: center; gap: 8px; margin: 5px 0; font-size: .86rem;}
.axis .name {width: 132px; color: #4b5647;}
.bar {flex: 1; background: #EEF2EA; border-radius: 8px; height: 9px; overflow: hidden;}
.bar span {display: block; height: 9px; border-radius: 8px; background: linear-gradient(90deg, #81C784, #2E7D32);}
.badge {display: inline-block; padding: 3px 10px; border-radius: 999px; background: #E8F5E9; color: #2E7D32;
        font-size: .78rem; margin: 6px 4px 0 0;}
.stTabs [data-baseweb="tab"] {font-size: 1.05rem; padding: 10px 18px;}
div[data-testid="stForm"] {background: #fff; border-radius: 18px; border: 1px solid #E5EDE0; padding: 18px;}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------- tiện ích
def vn(x: float, d: int = 0) -> str:
    """Định dạng số kiểu Việt Nam: 1.234,5"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def style(fig: go.Figure, height: int = 340, title: str | None = None, axes: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=56 if title else 20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, 'Segoe UI', Roboto, sans-serif", size=13, color="#2b3527"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13), transition=dict(duration=500, easing="cubic-in-out"))
    if title:
        fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=16)))
    if axes:                                   # biểu đồ đồng hồ, radar không có trục x/y
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(gridcolor="#E3EADF", zeroline=False)
    return fig


def _st_version() -> tuple:
    try:
        return tuple(int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        return (0, 0)


NEW_WIDTH_API = _st_version() >= (1, 50)     # từ bản 1.50 dùng width="stretch" thay cho use_container_width


def show(fig: go.Figure):
    if NEW_WIDTH_API:
        st.plotly_chart(fig, width="stretch", config=PLOT_CFG)
    else:
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)


def show_df(df: pd.DataFrame, **kw):
    if NEW_WIDTH_API:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def card(label: str, value: str, sub: str = "", color: str = GREEN_D) -> str:
    return (f'<div class="card"><div class="label">{label}</div>'
            f'<div class="value" style="color:{color}">{value}</div><div class="sub">{sub}</div></div>')


def risk_label(p: float | None):
    if p is None:
        return "Chưa có model: dùng tỷ lệ lịch sử 33%", GRAY
    if p >= 0.6:
        return "Rủi ro CAO: chuẩn bị nước sớm", RED
    if p >= 0.4:
        return "Cao hơn bình thường", ORANGE
    return "Bình thường hoặc thấp", GREEN


def soil_text(pct: float):
    if math.isnan(pct):
        return "—", GRAY
    if pct < 20:
        return "Khô hơn thường lệ", RED
    if pct > 80:
        return "Ẩm hơn thường lệ", BLUE
    return "Bình thường", GREEN


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def load_data(lat: float, lon: float):
    return pc.fetch_point(lat, lon)


# ----------------------------------------------------------------- thanh bên
with st.sidebar:
    st.markdown("## 📍 Ruộng của bạn")
    region = st.radio("Vùng", list(pc.REGIONS), format_func=lambda k: pc.REGIONS[k]["name"])
    places = list(pc.PRESETS[region]) + ["Tự nhập toạ độ"]
    place = st.selectbox("Địa điểm gần ruộng nhất", places)
    if place == "Tự nhập toạ độ":
        d_lat, d_lon = next(iter(pc.PRESETS[region].values()))
        lat = st.number_input("Vĩ độ (°N)", value=float(d_lat), step=0.01, format="%.3f")
        lon = st.number_input("Kinh độ (°E)", value=float(d_lon), step=0.01, format="%.3f")
        place_name = f"({lat:.2f}, {lon:.2f})"
    else:
        lat, lon = pc.PRESETS[region][place]
        place_name = place
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=6)
    st.caption("Toạ độ gần đúng. Ô lưới NASA POWER rộng khoảng 50 km, nên số liệu là khí hậu của cả vùng quanh ruộng.")

st.markdown(f"""<div class="hero"><h1>🌾 FieldShift</h1>
<p>Trợ lý chọn mùa vụ và luân canh từ dữ liệu vệ tinh NASA · <b>{place_name}</b>, {pc.REGIONS[region]['name']}</p>
</div>""", unsafe_allow_html=True)

with st.spinner("Đang tải 35 năm dữ liệu khí hậu NASA POWER cho ruộng của bạn..."):
    try:
        df, data_src = load_data(round(float(lat), 3), round(float(lon), 3))
    except Exception as e:
        st.error("Không tải được dữ liệu NASA POWER. Kiểm tra kết nối mạng rồi tải lại trang.")
        st.caption(f"Chi tiết: {e}")
        st.stop()
if data_src == "cache-cu":
    st.warning("Không kết nối được NASA POWER: đang dùng dữ liệu đã lưu lần trước.")

summary = pc.climate_summary(df, region)
normals = pc.monthly_normals(df)
fc = pc.load_forecast(region, lat, lon)
p = fc["p"] if fc else None
season = pc.next_dry_season(region)
dry_months = pc.REGIONS[region]["dry_months"]

tab_fc, tab_rot, tab_info = st.tabs(["🌦️ Dự báo khí hậu", "🌾 Tư vấn luân canh", "ℹ️ Về dữ liệu"])

# ================================================================= TAB 1
with tab_fc:
    risk_txt, risk_col = risk_label(p)
    soil_lbl, soil_col = soil_text(summary["soil_pct"])
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(card(f"Mùa khô {season} khắc nghiệt?", f"{p:.0%}" if p is not None else "33%", risk_txt, risk_col),
                unsafe_allow_html=True)
    c2.markdown(card("Mưa trung bình năm", f"{vn(summary['annual_rain'])} mm", "Trung bình 1991–2020"),
                unsafe_allow_html=True)
    c3.markdown(card("Mưa cả mùa khô (bình thường)", f"{vn(summary['dry_rain'])} mm",
                     f"Tháng khô nhất: tháng {summary['driest_month']}", ORANGE), unsafe_allow_html=True)
    pct_txt = "" if math.isnan(summary["soil_pct"]) else f"Ẩm hơn {summary['soil_pct']:.0f}% số năm cùng thời điểm"
    c4.markdown(card("Độ ẩm đất hiện tại", soil_lbl, pct_txt, soil_col), unsafe_allow_html=True)
    st.write("")

    g1, g2 = st.columns([1, 1.6])
    with g1:
        val = (p if p is not None else 1 / 3) * 100
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=val, number={"suffix": "%", "font": {"size": 44}},
            title={"text": f"Khả năng mùa khô {season} thuộc nhóm ít mưa nhất", "font": {"size": 14}},
            gauge={"axis": {"range": [0, 100], "tickwidth": 0}, "bar": {"color": risk_col, "thickness": 0.3},
                   "steps": [{"range": [0, 33], "color": "#E8F5E9"}, {"range": [33, 60], "color": "#FFF3E0"},
                             {"range": [60, 100], "color": "#FFEBEE"}],
                   "threshold": {"line": {"color": "#455A64", "width": 3}, "thickness": 0.8, "value": 33.3}}))
        show(style(gauge, 280, axes=False))
        st.caption("Vạch xám là mức 33%: tỷ lệ 'mùa khô ít mưa' nếu chỉ đoán theo lịch sử.")
    with g2:
        tips = []
        if p is None:
            tips.append("Chưa có file dự báo từ model. Chạy notebook train model rồi chép "
                        f"<code>forecast_{region}.csv</code> vào thư mục <code>data/</code>.")
        elif p >= 0.5:
            tips.append(f"Mùa khô {season} nhiều khả năng ít mưa: ưu tiên cây ngắn ngày, ít nước; trữ nước ngọt sớm.")
        else:
            tips.append(f"Mùa khô {season} không có dấu hiệu khắc nghiệt hơn bình thường, vẫn nên trữ nước dự phòng.")
        if summary["soil_dry_now"]:
            tips.append(f"Đất đang khô hơn {100 - summary['soil_pct']:.0f}% số năm cùng thời điểm: "
                        "cân nhắc lùi lịch xuống giống, giữ ẩm bằng rơm rạ.")
        tips.append(f"Mưa tập trung nhiều nhất vào tháng {summary['wettest_month']}; tháng {summary['driest_month']} "
                    f"khô nhất. Bố trí vụ cần nhiều nước vào mùa mưa.")
        if region == "DBSCL":
            tips.append("Theo dõi bản tin xâm nhập mặn của Trung tâm Dự báo KTTV quốc gia trước khi lấy nước vào ruộng.")
        else:
            tips.append("Kiểm tra mực nước hồ, giếng trước mùa khô; tưới tiết kiệm (nhỏ giọt, phun gốc) cho cây lâu năm.")
        st.markdown('<div class="tip"><b>💡 Lời khuyên nhanh</b><ul>' + "".join(f"<li>{t}</li>" for t in tips)
                    + "</ul></div>", unsafe_allow_html=True)

    # Lịch mưa và nhiệt độ
    cur, cur_year, last_day = pc.this_year_rain(df)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for m in dry_months:
        fig.add_vrect(x0=m - 1.5, x1=m - 0.5, fillcolor="#FFF3E0", opacity=0.6, layer="below", line_width=0)
    fig.add_trace(go.Bar(x=pc.MONTH_LABELS, y=normals["rain_mm"], name="Mưa bình thường (1991–2020)",
                         marker=dict(color="#A5D6A7", line=dict(width=0)),
                         hovertemplate="%{x}: %{y:.0f} mm<extra>Bình thường</extra>"), secondary_y=False)
    fig.add_trace(go.Bar(x=pc.MONTH_LABELS, y=cur, name=f"Mưa năm {cur_year} (đến {last_day:%d/%m})",
                         marker=dict(color="#42A5F5", line=dict(width=0)),
                         hovertemplate="%{x}: %{y:.0f} mm<extra>" + str(cur_year) + "</extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=pc.MONTH_LABELS, y=normals["tmax"], name="Nhiệt độ cao nhất trung bình",
                             mode="lines+markers", line=dict(color=ORANGE, width=3, shape="spline"),
                             marker=dict(size=7), hovertemplate="%{x}: %{y:.1f} °C<extra></extra>"), secondary_y=True)
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_yaxes(title_text="Lượng mưa (mm/tháng)", secondary_y=False)
    fig.update_yaxes(title_text="°C", secondary_y=True, showgrid=False)
    show(style(fig, 380, "☔ Lịch mưa và nhiệt độ: năm nay so với bình thường"))
    st.caption("Nền cam là các tháng mùa khô. Cột xanh dương thấp hơn cột xanh lá nghĩa là tháng đó mưa ít hơn thường lệ.")

    s1, s2 = st.columns(2)
    with s1:
        recent, band, pct = pc.soil_band(df)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=band.index, y=band["p90"] * 100, line=dict(width=0), showlegend=False,
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=band.index, y=band["p10"] * 100, fill="tonexty", fillcolor="rgba(129,199,132,.28)",
                                 line=dict(width=0), name="Dải bình thường", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=band.index, y=band["p50"] * 100, line=dict(color=GREEN, dash="dot", width=2),
                                 name="Mức thường gặp", hovertemplate="%{y:.0f}%<extra>Thường gặp</extra>"))
        fig.add_trace(go.Scatter(x=recent.index, y=recent.values * 100, line=dict(color=BLUE, width=3, shape="spline"),
                                 name="Năm nay", hovertemplate="%{x|%d/%m}: %{y:.0f}%<extra>Năm nay</extra>"))
        fig.update_yaxes(title_text="Độ ẩm đất vùng rễ (%)")
        show(style(fig, 330, "🌱 Độ ẩm đất 5 tháng gần nhất"))
        st.caption("Đường xanh dương nằm dưới dải xanh lá nghĩa là đất đang khô hơn hầu hết các năm cùng thời điểm.")
    with s2:
        hd, thr = pc.hot_days(df)
        fig = go.Figure(go.Bar(x=hd.index, y=hd.values, marker=dict(color="#FFB74D", line=dict(width=0)),
                               name="Số ngày nóng", hovertemplate="%{x}: %{y} ngày<extra></extra>"))
        if len(hd) > 5:
            k = np.polyfit(hd.index.values.astype(float), hd.values.astype(float), 1)
            fig.add_trace(go.Scatter(x=hd.index, y=np.polyval(k, hd.index.values.astype(float)), mode="lines",
                                     line=dict(color=RED, width=3), name=f"Xu hướng: {k[0] * 10:+.0f} ngày mỗi 10 năm"))
        fig.update_yaxes(title_text="ngày/năm")
        show(style(fig, 330, f"🔥 Số ngày nóng trên {thr:.1f} °C mỗi năm"))
        st.caption("Ngày nóng ở đây là ngày nóng hơn mức của 10% ngày nóng nhất giai đoạn 1991–2020 tại chính nơi này.")

    ds = pc.dry_seasons(df, dry_months)
    known = pc.REGIONS[region]["known_drought"]
    fig = go.Figure(go.Bar(x=ds.index, y=ds.values,
                           marker=dict(color=[RED if y in known else "#81C784" for y in ds.index], line=dict(width=0)),
                           hovertemplate="Mùa khô %{x}: %{y:.0f} mm<extra></extra>", name="Mưa mùa khô"))
    if not math.isnan(summary["dry_rain"]):
        fig.add_hline(y=summary["dry_rain"], line_dash="dash", line_color="#455A64",
                      annotation_text="Bình thường", annotation_position="top left")
    fig.update_yaxes(title_text="Tổng mưa mùa khô (mm)")
    show(style(fig, 330, "📉 Lịch sử các mùa khô: tổng lượng mưa"))
    st.caption(f"Cột đỏ là các năm hạn đã được báo chí ghi nhận ({', '.join(map(str, known))}). "
               "Mùa khô được đặt tên theo năm kết thúc.")

# ================================================================= TAB 2
with tab_rot:
    st.markdown("### 👩‍🌾 Kể cho mình nghe về ruộng của bạn")
    with st.form("farm"):
        a, b = st.columns(2)
        with a:
            current_label = st.selectbox("Bạn đang trồng gì?", list(en.CURRENT_OPTIONS[region]))
            default_soil = en.SOILS.index("Đất đỏ bazan") if region == "TAYNGUYEN" else 0
            soil = st.selectbox("Loại đất", en.SOILS, index=default_soil)
            water = st.radio("Mùa khô, nước tưới lấy từ đâu?", en.WATER_SOURCES)
            if region == "DBSCL":
                sal_label = st.select_slider("Ruộng có bị nhiễm mặn vào mùa khô không?", options=en.SALINITY)
            else:
                sal_label = en.SALINITY[0]
            area = st.number_input("Diện tích (ha)", min_value=0.1, value=1.0, step=0.1)
        with b:
            st.markdown("**Bạn ưu tiên điều gì?** (1 = ít quan trọng, 5 = rất quan trọng)")
            pri = {k: st.slider(lbl, 1, 5, 3) for k, lbl in en.AXES.items()}
        submitted = st.form_submit_button("🌾 Gợi ý luân canh cho tôi", type="primary")

    if submitted:
        st.session_state["show_rec"] = True

    if not st.session_state.get("show_rec"):
        st.info("👆 Điền thông tin rồi bấm nút để xem gợi ý. Bạn có thể đổi lựa chọn và bấm lại bao nhiêu lần cũng được.")
    else:
        inputs = {"current": en.CURRENT_OPTIONS[region][current_label], "soil": soil, "water_source": water,
                  "salinity": en.SALINITY.index(sal_label), "priorities": pri}
        recs = en.recommend(region, inputs, summary, p)
        top = recs[:3]
        current_rec = next((r for r in recs if r["is_current"]), None)

        p_txt = f"{p:.0%}" if p is not None else "chưa có dự báo (dùng 33%)"
        st.success(f"Dựa trên 35 năm dữ liệu NASA tại {place_name} và khả năng mùa khô {season} khắc nghiệt "
                   f"là **{p_txt}**, đây là 3 vòng luân canh hợp nhất với ruộng {vn(area, 1)} ha của bạn.")
        if current_rec and current_rec["rank"] > 1:
            diff = top[0]["total"] - current_rec["total"]
            st.markdown(f"Cách bạn đang làm (**{current_rec['name']}**) được **{current_rec['total']:.0f} điểm**, "
                        f"xếp hạng {current_rec['rank']}/{len(recs)}. Phương án số 1 cao hơn **{diff:.0f} điểm**.")

        cols = st.columns(3)
        for i, (col, r) in enumerate(zip(cols, top)):
            bars = "".join(f'<div class="axis"><span class="name">{lbl}</span>'
                           f'<div class="bar"><span style="width:{r[k]:.0f}%"></span></div>'
                           f'<b>{r[k]:.0f}</b></div>' for k, lbl in en.AXES.items())
            badges = "".join(f'<span class="badge">{x}</span>' for x in r["badges"])
            now = " · đang làm" if r["is_current"] else ""
            col.markdown(f'<div class="rec {"top" if i == 0 else ""}"><span class="pill">#{i + 1}{now}</span>'
                         f'<h3>{r["name"]}</h3><div class="score">{r["total"]:.0f}<small> /100 điểm</small></div>'
                         f'{bars}<div>{badges}</div></div>', unsafe_allow_html=True)
            with col.expander("Vì sao?"):
                st.markdown(r["note"])
                for x in r["reasons"]:
                    st.markdown(f"- {x}")
                if r["evidence"]:
                    st.markdown("**Bằng chứng:**")
                    for x in r["evidence"]:
                        st.markdown(f"- {x}")

        st.write("")
        r1, r2 = st.columns([1, 1.35])
        with r1:
            shown = top + ([current_rec] if current_rec and current_rec not in top else [])
            cats = list(en.AXES.values())
            fig = go.Figure()
            for i, r in enumerate(shown):
                vals = [r[k] for k in en.AXES]
                color = TOP_COLORS[i] if not r["is_current"] or i < 3 else GRAY
                fig.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself", opacity=0.45,
                    name=("Đang làm: " if r["is_current"] else f"#{r['rank']} ") + r["name"],
                    line=dict(color=color, width=2.5, dash="dash" if r["is_current"] else "solid"),
                    hovertemplate="%{theta}: %{r:.0f}<extra></extra>"))
            fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)",
                                         radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#DDE7D8"),
                                         angularaxis=dict(gridcolor="#DDE7D8")))
            fig = style(fig, 420, "🧭 So sánh 4 tiêu chí", axes=False)
            fig.update_layout(legend=dict(orientation="h", y=-0.12, x=0, xanchor="left", yanchor="top"))
            show(fig)
        with r2:
            pick = st.selectbox("Xem lịch thời vụ của phương án:", [f"#{r['rank']} {r['name']}" for r in top])
            chosen = top[int(pick.split()[0][1:]) - 1]
            rows = [("Gợi ý", chosen)] + ([("Đang làm", current_rec)]
                                          if current_rec and current_rec["key"] != chosen["key"] else [])
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.4, 0.6], vertical_spacing=0.07)
            fig.add_trace(go.Bar(x=list(range(1, 13)), y=normals["rain_mm"], marker=dict(color="#90CAF9", line=dict(width=0)),
                                 name="Mưa bình thường", hovertemplate="Tháng %{x}: %{y:.0f} mm<extra></extra>"),
                          row=1, col=1)
            for row_label, rr in rows:
                for lab, s, e, kind in rr["calendar"]:
                    for a0, b0 in ([(s, e)] if s <= e else [(s, 12), (1, e)]):
                        fig.add_trace(go.Bar(
                            y=[row_label], x=[b0 - a0 + 1], base=[a0 - 0.5], orientation="h", showlegend=False,
                            marker=dict(color=en.KIND_COLORS[kind], line=dict(color="white", width=2)),
                            text=[lab if b0 - a0 + 1 >= 2 else ""], textposition="inside", insidetextanchor="middle",
                            textfont=dict(color="white", size=12),
                            hovertemplate=f"{lab}: tháng {s} đến tháng {e}<extra>{row_label}</extra>"), row=2, col=1)
            fig.update_layout(barmode="overlay", bargap=0.35)
            fig.update_xaxes(tickvals=list(range(1, 13)), ticktext=pc.MONTH_LABELS, range=[0.5, 12.5], row=2, col=1)
            fig.update_xaxes(range=[0.5, 12.5], row=1, col=1)
            fig.update_yaxes(title_text="mm", row=1, col=1)
            fig.update_yaxes(autorange="reversed", row=2, col=1)
            show(style(fig, 420, "🗓️ Lịch thời vụ đặt cạnh lịch mưa"))
            st.caption("Lịch là minh họa; điều chỉnh theo khuyến cáo của khuyến nông địa phương.")
            st.download_button("📥 Tải kế hoạch về máy", en.plan_text(chosen, place_name, p).encode("utf-8"),
                               file_name="ke_hoach_luan_canh.txt", mime="text/plain")

        st.markdown("#### 📋 Tất cả phương án")
        table = pd.DataFrame([{
            "Hạng": r["rank"],
            "Vòng luân canh": r["name"] + (" (đang làm)" if r["is_current"] else ""),
            "Điểm phù hợp": r["total"], "Nước": r["water"], "Đất": r["soil"],
            "Lợi nhuận": r["profit"], "Ổn định": r["stability"],
            "Trừ do dự báo": -r["forecast_penalty"], "Nguồn": r["source"]} for r in recs])
        show_df(table, column_config={
            "Điểm phù hợp": st.column_config.ProgressColumn("Điểm phù hợp", min_value=0, max_value=100, format="%.0f"),
            "Nước": st.column_config.NumberColumn(format="%.0f"), "Đất": st.column_config.NumberColumn(format="%.0f"),
            "Lợi nhuận": st.column_config.NumberColumn(format="%.0f"),
            "Ổn định": st.column_config.NumberColumn(format="%.0f"),
            "Trừ do dự báo": st.column_config.NumberColumn(format="%.1f")})

# ================================================================= TAB 3
with tab_info:
    fc_line = (f"Ô dự báo gần nhất: {fc['cell']}, cách khoảng {fc['dist_km']:.0f} km." if fc
               else "Chưa có file dự báo trong thư mục data/.")
    src_line = "Gọi trực tiếp NASA POWER" if data_src == "api" else "Dữ liệu NASA POWER đã lưu trên máy"
    st.markdown(f"""
### Dữ liệu
- **NASA POWER** (MERRA-2, CERES): mưa `PRECTOTCORR`, nhiệt độ `T2M`, `T2M_MAX`, độ ẩm đất vùng rễ `GWETROOT`,
  dữ liệu ngày từ 1991 đến {summary['last_date']:%d/%m/%Y}. Giấy phép CC BY 4.0.
- **Dự báo mùa khô**: model hồi quy logistic hoặc random forest, train trên POWER và chỉ số El Niño (ONI) của NOAA,
  đánh giá bằng cách để riêng từng năm làm đề kiểm tra. {fc_line}
- **Luân canh**: danh mục và bằng chứng từ tổng quan *Crop Rotation for Sustainable Agriculture* (Su et al., 2026,
  Applied Sciences 16(13):6511), cộng thêm mô hình lúa – tôm và cà phê xen cây từ thực tiễn địa phương.

### Cách tính điểm
1. Mỗi vòng luân canh được chấm 4 tiêu chí (0–100): tiết kiệm nước mùa khô, sức khỏe đất (cây họ đậu, phân xanh,
   số loại cây), lợi nhuận tương đối, ổn định trước rủi ro.
2. Nhân với độ khả thi theo ruộng: mặn, nguồn nước, loại đất.
3. Trừ điểm các vòng tốn nước khi xác suất mùa khô khắc nghiệt cao hơn 33%, hoặc khi đất đang khô bất thường.
4. Cộng theo trọng số ưu tiên bạn chọn, rồi xếp hạng.

### Giới hạn
- Ô lưới khoảng 50 km: chưa phân biệt được hai ruộng cạnh nhau.
- NASA POWER không đo độ mặn sông; mức mặn do bạn tự chọn.
- Lợi nhuận là ước lượng tương đối, chưa theo giá thị trường.
- Bằng chứng trong bài tổng quan chủ yếu từ Trung Quốc.

### Nguồn dữ liệu đang dùng
{src_line} · Toạ độ ({lat:.3f}, {lon:.3f})

*Ứng dụng được xây dựng với sự hỗ trợ của AI (Claude) cho NASA Space Apps Challenge 2026.*
""")
