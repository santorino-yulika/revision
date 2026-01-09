import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Ревізії кав'ярень",
    layout="wide"
)

st.title("☕ Аналітика ревізій кав'ярень")

# =========================
# LOAD DATA
# =========================
DEFAULT_FILE = "data/revisions.xlsx"

uploaded_file = st.sidebar.file_uploader(
    "Завантажити файл ревізій (Excel)",
    type=["xlsx"]
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)
else:
    try:
        df = pd.read_excel(DEFAULT_FILE)
        st.sidebar.info("Завантажено файл за замовчуванням")
    except Exception:
        st.error("❌ Файл за замовчуванням не знайдено")
        st.stop()

# =========================
# BASIC CLEANING
# =========================
df.columns = df.columns.str.strip()

df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True, errors="coerce")

# міжревізійний період: заміна ком на крапки
if "Міжревізійний період" in df.columns:
    df["Міжревізійний період"] = (
        df["Міжревізійний період"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

numeric_cols = [
    "Результат ВСЬОГО",
    "Результат по чашках",
    "Фактична кількість кави на порцію",
    "Кількість проливів",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# FILTERS
# =========================
df["Рік"] = df["Дата"].dt.year

years = sorted(df["Рік"].dropna().unique())
selected_years = st.sidebar.multiselect(
    "Рік",
    years,
    default=years
)

tts = sorted(df["ТТ Місто"].dropna().unique())
selected_tt = st.sidebar.multiselect(
    "ТТ Місто",
    tts,
    default=tts
)

df = df[
    df["Рік"].isin(selected_years) &
    df["ТТ Місто"].isin(selected_tt)
]

# =========================
# GRAM CONTROL
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
    if pd.isna(val):
        return ""
    if abs(val) <= 1:
        return "🟢 OK"
    if abs(val) <= 2:
        return "🟡 Увага"
    return "🔴 Критично"

df["Статус грамажу"] = df["Відхилення грамажу"].apply(gram_status)

# =========================
# COUNTER PROBLEM
# =========================
df["Проблема лічильника"] = np.where(
    (df["Кількість проливів"].isna()) |
    (df["Кількість проливів"] == 0),
    "⚠️ Так",
    ""
)

# =========================
# GENERAL STATUS
# =========================
def calc_status(row):
    if row["Результат ВСЬОГО"] < 0:
        return "🔴 Критично"
    if row["Статус грамажу"] == "🔴 Критично":
        return "🔴 Критично"
    if row["Статус грамажу"] == "🟡 Увага":
        return "🟡 Увага"
    return "🟢 OK"

df["Статус"] = df.apply(calc_status, axis=1)

# =========================
# DASHBOARDS
# =========================
st.subheader("📊 Дашборди")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Динаміка результату по датах**")
    daily = df.groupby("Дата")["Результат ВСЬОГО"].sum()
    st.line_chart(daily)

with col2:
    st.markdown("**Середній грамаж по ТТ**")
    avg_gram = df.groupby("ТТ Місто")["Фактична кількість кави на порцію"].mean()
    st.bar_chart(avg_gram)

st.markdown("### 🔥 TOP-10 ТТ з найбільшими втратами")

top10_loss = (
    df.groupby("ТТ Місто", as_index=False)["Результат ВСЬОГО"]
    .sum()
    .sort_values("Результат ВСЬОГО", ascending=True)
    .head(10)
)

st.bar_chart(
    top10_loss.set_index("ТТ Місто")["Результат ВСЬОГО"]
)

# =========================
# TABLE SETTINGS
# =========================
show_comments = st.sidebar.toggle(
    "Показувати коментар ревізора",
    value=True
)

main_columns = [
    "Дата",
    "ТТ Місто",
    "Міжревізійний період",
    "Результат ВСЬОГО",
    "Статус",
    "Відхилення грамажу",
    "Статус грамажу",
    "Проблема лічильника",
    "Коментар ревізора",
]

existing_main = [c for c in main_columns if c in df.columns]
other_cols = [c for c in df.columns if c not in existing_main]
ordered_cols = existing_main + other_cols

if not show_comments and "Коментар ревізора" in ordered_cols:
    ordered_cols.remove("Коментар ревізора")

df_display = df[ordered_cols].copy()
df_display["Дата"] = df_display["Дата"].dt.strftime("%d-%m-%Y")

def highlight_negative(val):
    if isinstance(val, (int, float)) and val < 0:
        return "color: red; font-weight: bold;"
    return ""

styled_df = df_display.sort_values(
    "Дата", ascending=False
).style.applymap(
    highlight_negative,
    subset=["Результат ВСЬОГО"]
)

st.subheader("📋 Таблиця ревізій")
st.dataframe(
    styled_df,
    use_container_width=True,
    height=550
)
