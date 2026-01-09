import streamlit as st
import pandas as pd
import numpy as np
import os

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Ревізії кавʼярень",
    layout="wide"
)

st.title("📊 Аналітика ревізій кавʼярень")

DEFAULT_FILE = "data.xlsx"

# =========================
# FUNCTIONS
# =========================
def parse_revision_period(val):
    if pd.isna(val):
        return pd.NaT, pd.NaT, None
    try:
        start, end = val.split("-")
        start = pd.to_datetime(start.replace(",", "."), dayfirst=True)
        end = pd.to_datetime(end.replace(",", "."), dayfirst=True)
        return start, end, (end - start).days
    except Exception:
        return pd.NaT, pd.NaT, None


def load_data(file):
    df = pd.read_excel(file)

    df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True, errors="coerce")

    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Міжревізійний період" in df.columns:
        df[["Дата початку", "Дата кінця", "Днів між ревізіями"]] = (
            df["Міжревізійний період"]
            .apply(lambda x: pd.Series(parse_revision_period(x)))
        )

    return df


def highlight_negative(val):
    if isinstance(val, (int, float)) and val < 0:
        return "color: red; font-weight: bold;"
    return ""


# =========================
# DATA LOAD
# =========================
st.sidebar.header("📂 Дані")

uploaded = st.sidebar.file_uploader("Завантажити Excel", type=["xlsx"])

if uploaded:
    df = load_data(uploaded)
    st.sidebar.success("Файл завантажено")
elif os.path.exists(DEFAULT_FILE):
    df = load_data(DEFAULT_FILE)
    st.sidebar.info("Файл за замовчуванням")
else:
    st.warning("Файл за замовчуванням не знайдено. Завантаж Excel.")
    st.stop()

# =========================
# FILTERS
# =========================
df["Рік"] = df["Дата"].dt.year

years = sorted(df["Рік"].dropna().unique())
selected_years = st.sidebar.multiselect("Рік", years, default=years)

tts = sorted(df["ТТ Місто"].dropna().unique())
selected_tts = st.sidebar.multiselect("Кавʼярня", tts, default=tts)

df = df[
    (df["Рік"].isin(selected_years)) &
    (df["ТТ Місто"].isin(selected_tts))
]

# =========================
# GRAMMAGE CONTROL
# =========================
target_gram = st.sidebar.slider(
    "Нормативний грамаж (г)",
    min_value=7.0,
    max_value=12.0,
    value=10.0,
    step=0.1
)

df["Відхилення грамажу"] = (
    df["Фактична кількість кави на порцію"] - target_gram
)

def gram_status(val):
    if abs(val) <= 1:
        return "🟢 OK"
    if abs(val) <= 2:
        return "🟡 Увага"
    return "🔴 Критично"

df["Статус грамажу"] = df["Відхилення грамажу"].apply(gram_status)

# =========================
# COUNTER CONTROL
# =========================
df["Проблема лічильника"] = np.where(
    ((df["Кількість проливів"].isna()) | (df["Кількість проливів"] == 0)) &
    (df["Виручка за період"] > 0),
    "⚠️ Лічильник",
    ""
)

# =========================
# FINAL STATUS
# =========================
def calc_status(row):
    if row.get("Результат ВСЬОГО", 0) < 0:
        return "🔴 Критично"
    if row["Статус грамажу"] == "🔴 Критично":
        return "🔴 Критично"
    if row["Статус грамажу"] == "🟡 Увага":
        return "🟡 Увага"
    return "🟢 OK"

df["Статус"] = df.apply(calc_status, axis=1)

# =========================
# TABLE (FULL)
# =========================
st.subheader("📋 Повна таблиця ревізій")

df_display = df.copy()
df_display["Дата"] = df_display["Дата"].dt.strftime("%d-%m-%Y")

styled_df = df_display.sort_values(
    "Дата", ascending=False
).style.applymap(
    highlight_negative,
    subset=["Результат ВСЬОГО"]
)

st.dataframe(
    styled_df,
    use_container_width=True,
    height=520
)

# =========================
# DASHBOARDS
# =========================

# ---- FINANCE ----
st.divider()
st.subheader("💰 Фінансова аналітика")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### 📉 Динаміка результату по датах")
    trend = (
        df.groupby("Дата", as_index=False)["Результат ВСЬОГО"]
        .sum()
        .sort_values("Дата")
    )
    st.line_chart(trend.set_index("Дата")["Результат ВСЬОГО"])

with c2:
    st.markdown("### 🔥 TOP-10 ТТ з найбільшим розходженням")
    top10 = (
        df.groupby("ТТ Місто", as_index=False)["Результат ВСЬОГО"]
        .sum()
        .sort_values("Результат ВСЬОГО", ascending=False)
        .head(10)
    )
    st.bar_chart(top10.set_index("ТТ Місто")["Результат ВСЬОГО"])

# ---- CUPS / COUNTER ----
st.divider()
st.subheader("☕ Чашки та проливи")

cups = (
    df.groupby("Дата", as_index=False)
    .agg({
        "Результат по чашках": "sum",
        "Кількість проливів": "sum"
    })
    .sort_values("Дата")
    .set_index("Дата")
)

st.line_chart(cups)

# ---- GRAMMAGE ----
st.divider()
st.subheader("⚖️ Середній грамаж по ТТ")

avg_gram = (
    df.groupby("ТТ Місто", as_index=False)
    ["Фактична кількість кави на порцію"]
    .mean()
    .sort_values("Фактична кількість кави на порцію", ascending=False)
)

st.bar_chart(
    avg_gram.set_index("ТТ Місто")
    ["Фактична кількість кави на порцію"]
)
