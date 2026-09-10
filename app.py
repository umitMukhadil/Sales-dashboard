"""Дашборд продаж. Запуск: streamlit run app.py"""
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Продажи", page_icon="📊", layout="wide")

# ---------- Оформление ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Manrope', sans-serif; }
.stApp { background: #F7F8F5; }
h1 { font-weight: 800; letter-spacing: -0.02em; color: #14261F; }
.kpi { background: #FFFFFF; border-left: 4px solid #1F6F5A; padding: 14px 18px; border-radius: 6px; }
.kpi .label { color: #5C6B64; font-size: 0.85rem; margin-bottom: 4px; }
.kpi .value { color: #14261F; font-size: 1.7rem; font-weight: 800; line-height: 1.1; }
.kpi .delta { font-size: 0.85rem; margin-top: 4px; }
.up { color: #1F6F5A; } .down { color: #B8452E; }
section[data-testid="stSidebar"] { background: #EEF2EC; }
</style>
""", unsafe_allow_html=True)

PALETTE = ["#1F6F5A", "#5DA57F", "#A9CBB0", "#E0B85C", "#B8452E", "#6B7F98", "#C9D3CF"]


# ---------- Данные ----------
@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path(__file__).parent / "sales.csv"
    df = pd.read_csv(path, parse_dates=["date"])
    return df


df = load_data()
min_date, max_date = df["date"].min().date(), df["date"].max().date()


def fmt_money(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f} млн ₸"
    return f"{v:,.0f} ₸".replace(",", " ")


# ---------- Фильтры ----------
with st.sidebar:
    st.header("Период")
    preset = st.radio(
        "Быстрый выбор",
        ["7 дней", "30 дней", "Квартал", "Год", "Свой период"],
        index=1,
    )
    if preset == "Свой период":
        start, end = st.date_input(
            "Даты", (max_date - timedelta(days=29), max_date),
            min_value=min_date, max_value=max_date,
        )
    else:
        days = {"7 дней": 7, "30 дней": 30, "Квартал": 91, "Год": 365}[preset]
        end = max_date
        start = max(min_date, end - timedelta(days=days - 1))

    st.header("Фильтры")
    sel_managers = st.multiselect("Менеджер", sorted(df.manager.unique()))
    sel_cities = st.multiselect("Город", sorted(df.city.unique()))
    granularity = st.selectbox("Шаг графика", ["День", "Неделя", "Месяц"], index=0)

# Текущий и предыдущий период одинаковой длины
period_len = (end - start).days + 1
prev_start, prev_end = start - timedelta(days=period_len), start - timedelta(days=1)


def apply_filters(frame: pd.DataFrame, a, b) -> pd.DataFrame:
    m = (frame.date.dt.date >= a) & (frame.date.dt.date <= b)
    if sel_managers:
        m &= frame.manager.isin(sel_managers)
    if sel_cities:
        m &= frame.city.isin(sel_cities)
    return frame[m]


cur = apply_filters(df, start, end)
prev = apply_filters(df, prev_start, prev_end)

# ---------- Заголовок и KPI ----------
st.title("Продажи")
st.caption(f"{start:%d.%m.%Y} — {end:%d.%m.%Y}, сравнение с предыдущими {period_len} дн.")

if cur.empty:
    st.warning("За выбранный период и фильтры данных нет. Расширьте период или снимите фильтры.")
    st.stop()


def kpi(col, label, value, prev_value, money=True):
    delta = None if not prev_value else (value - prev_value) / prev_value * 100
    shown = fmt_money(value) if money else f"{value:,.0f}".replace(",", " ")
    if delta is None:
        d_html = '<div class="delta">нет данных для сравнения</div>'
    else:
        cls = "up" if delta >= 0 else "down"
        arrow = "▲" if delta >= 0 else "▼"
        d_html = f'<div class="delta {cls}">{arrow} {abs(delta):.1f}% к прошлому периоду</div>'
    col.markdown(
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{shown}</div>{d_html}</div>',
        unsafe_allow_html=True,
    )


c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Выручка", cur.revenue.sum(), prev.revenue.sum())
kpi(c2, "Заказов", cur.order_id.nunique(), prev.order_id.nunique(), money=False)
kpi(c3, "Средний чек", cur.revenue.sum() / cur.order_id.nunique(),
    prev.revenue.sum() / prev.order_id.nunique() if not prev.empty else 0)
kpi(c4, "Товаров продано", cur.quantity.sum(), prev.quantity.sum(), money=False)

st.write("")

# ---------- Динамика ----------
rule = {"День": "D", "Неделя": "W-MON", "Месяц": "MS"}[granularity]
ts_cur = cur.set_index("date").resample(rule)["revenue"].sum().reset_index()
ts_prev = prev.set_index("date").resample(rule)["revenue"].sum().reset_index()
ts_prev["date"] = ts_prev["date"] + timedelta(days=period_len)  # наложить на текущий период

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=ts_prev.date, y=ts_prev.revenue, name="Прошлый период",
    line=dict(color="#C9D3CF", width=2, dash="dot"), hovertemplate="%{y:,.0f} ₸<extra>Прошлый</extra>",
))
fig.add_trace(go.Scatter(
    x=ts_cur.date, y=ts_cur.revenue, name="Текущий период",
    line=dict(color="#1F6F5A", width=3), fill="tozeroy", fillcolor="rgba(31,111,90,0.08)",
    hovertemplate="%{x|%d.%m}: %{y:,.0f} ₸<extra></extra>",
))
fig.update_layout(
    title="Выручка по дням", height=340, margin=dict(l=0, r=0, t=40, b=0),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=1.12, x=0), font=dict(family="Manrope"),
    yaxis=dict(gridcolor="#E4E8E3", tickformat=","), xaxis=dict(showgrid=False),
)
st.plotly_chart(fig, width="stretch")

# ---------- Разрезы ----------
left, right = st.columns([1, 1])

with left:
    by_mgr = cur.groupby("manager", as_index=False).revenue.sum().sort_values("revenue")
    fig_m = px.bar(
        by_mgr, x="revenue", y="manager", orientation="h", title="Выручка по менеджерам",
        color_discrete_sequence=["#1F6F5A"], text=by_mgr.revenue.map(fmt_money),
    )
    fig_m.update_traces(textposition="outside", hovertemplate="%{y}: %{x:,.0f} ₸<extra></extra>")
    fig_m.update_layout(
        height=320, margin=dict(l=0, r=60, t=40, b=0), yaxis_title=None, xaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Manrope"),
        xaxis=dict(showgrid=False, showticklabels=False),
    )
    st.plotly_chart(fig_m, width="stretch")

with right:
    by_city = cur.groupby("city", as_index=False).revenue.sum()
    fig_c = px.pie(
        by_city, values="revenue", names="city", title="Доля городов", hole=0.55,
        color_discrete_sequence=PALETTE,
    )
    fig_c.update_traces(textinfo="percent", hovertemplate="%{label}: %{value:,.0f} ₸<extra></extra>")
    fig_c.update_layout(
        height=320, margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope"), legend=dict(orientation="v"),
    )
    st.plotly_chart(fig_c, width="stretch")

# ---------- Таблица товаров ----------
st.subheader("Товары")
by_prod = (
    cur.groupby("product")
    .agg(Выручка=("revenue", "sum"), Штук=("quantity", "sum"), Заказов=("order_id", "nunique"))
    .sort_values("Выручка", ascending=False)
)
prev_prod = prev.groupby("product").revenue.sum()
by_prod["Динамика, %"] = ((by_prod["Выручка"] - prev_prod.reindex(by_prod.index).fillna(0))
                          / prev_prod.reindex(by_prod.index).replace(0, pd.NA) * 100).round(1)
by_prod["Доля, %"] = (by_prod["Выручка"] / by_prod["Выручка"].sum() * 100).round(1)

st.dataframe(
    by_prod,
    width="stretch",
    column_config={
        "Выручка": st.column_config.NumberColumn(format="%d ₸"),
        "Доля, %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        "Динамика, %": st.column_config.NumberColumn(format="%+.1f%%"),
    },
)

with st.expander("Все заказы за период"):
    st.dataframe(
        cur.sort_values("date", ascending=False).reset_index(drop=True),
        width="stretch", hide_index=True,
    )
    st.download_button(
        "Скачать CSV", cur.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"sales_{start}_{end}.csv", mime="text/csv",
    )
