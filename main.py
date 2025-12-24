import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# Streamlit 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ===============================
# 한글 폰트 (CSS)
# ===============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 상수 정의
# ===============================
DATA_DIR = Path("data")

EC_TARGETS = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLORS = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 파일명 NFC/NFD 정규화 유틸
# ===============================
def normalize_name(name: str, form: str):
    return unicodedata.normalize(form, name)

def find_file_by_keyword(directory: Path, keyword: str):
    for p in directory.iterdir():
        if p.is_file():
            for form in ["NFC", "NFD"]:
                if keyword in normalize_name(p.name, form):
                    return p
    return None

# ===============================
# 데이터 로딩 함수
# ===============================
@st.cache_data
def load_environment_data():
    env_data = {}
    for school in EC_TARGETS.keys():
        file_path = find_file_by_keyword(DATA_DIR, f"{school}_환경데이터")
        if file_path is None:
            continue
        df = pd.read_csv(file_path)
        df["school"] = school
        env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data():
    xlsx_path = find_file_by_keyword(DATA_DIR, "생육결과데이터")
    if xlsx_path is None:
        return None

    xls = pd.ExcelFile(xlsx_path, engine="openpyxl")
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["school"] = sheet
        data[sheet] = df
    return data

# ===============================
# 데이터 로딩
# ===============================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더 구조와 파일명을 확인하세요.")
    st.stop()

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 사이드바
# ===============================
school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + list(EC_TARGETS.keys())
)

selected_schools = (
    list(EC_TARGETS.keys())
    if school_option == "전체"
    else [school_option]
)

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1: 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        "본 연구는 서로 다른 EC 조건에서 재배된 극지식물의 생육 반응을 비교하여 "
        "최적 EC 농도를 도출하는 것을 목적으로 한다."
    )

    # 학교별 EC 조건 표
    overview_rows = []
    total_plants = 0
    for school, df in growth_data.items():
        overview_rows.append({
            "학교명": school,
            "EC 목표": EC_TARGETS.get(school),
            "개체수": len(df),
            "색상": SCHOOL_COLORS.get(school)
        })
        total_plants += len(df)

    overview_df = pd.DataFrame(overview_rows)
    st.dataframe(overview_df, use_container_width=True)

    # 주요 지표 카드
    col1, col2, col3, col4 = st.columns(4)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    col1.metric("총 개체수", f"{total_plants} 개")
    col2.metric("평균 온도", f"{avg_temp:.1f} °C")
    col3.metric("평균 습도", f"{avg_hum:.1f} %")
    col4.metric("최적 EC", "2.0 (하늘고)")

# ======================================================
# Tab 2: 환경 데이터
# ======================================================
with tab2:
    st.subheader("학교별 환경 데이터 비교")

    # 평균값 계산
    avg_rows = []
    for school in selected_schools:
        df = env_data[school]
        avg_rows.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean()
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["temperature"]), row=1, col=1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["humidity"]), row=1, col=2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["ph"]), row=2, col=1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC"), row=2, col=2)
    fig.add_trace(
        go.Bar(
            x=avg_df["학교"],
            y=[EC_TARGETS[s] for s in avg_df["학교"]],
            name="목표 EC"
        ),
        row=2, col=2
    )

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)

    # 시계열 그래프
    st.subheader("선택한 학교 시계열 데이터")
    for school in selected_schools:
        df = env_data[school]

        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["temperature"], name="온도"))
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["humidity"], name="습도"))
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["ec"], name="EC"))
        fig_ts.add_hline(
            y=EC_TARGETS[school],
            line_dash="dash",
            annotation_text="목표 EC"
        )
        fig_ts.update_layout(
            title=f"{school} 환경 변화",
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("환경 데이터 원본 및 다운로드"):
        all_env = pd.concat(env_data.values())
        st.dataframe(all_env)

        buffer = io.BytesIO()
        all_env.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "환경 데이터 다운로드 (XLSX)",
            data=buffer,
            file_name="환경데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ======================================================
# Tab 3: 생육 결과
# ======================================================
with tab3:
    st.subheader("🥇 EC별 생육 결과")

    growth_all = pd.concat(growth_data.values())
    growth_all["EC"] = growth_all["school"].map(EC_TARGETS)

    ec_weight = growth_all.groupby("EC")["생중량(g)"].mean()
    optimal_ec = ec_weight.idxmax()

    st.metric(
        "최대 평균 생중량 EC",
        f"{optimal_ec}",
        delta="최적"
    )

    # EC별 비교 그래프
    fig_growth = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig_growth.add_trace(
        go.Bar(x=ec_weight.index, y=ec_weight.values),
        row=1, col=1
    )

    fig_growth.add_trace(
        go.Bar(
            x=growth_all.groupby("EC")["잎 수(장)"].mean().index,
            y=growth_all.groupby("EC")["잎 수(장)"].mean().values
        ),
        row=1, col=2
    )

    fig_growth.add_trace(
        go.Bar(
            x=growth_all.groupby("EC")["지상부 길이(mm)"].mean().index,
            y=growth_all.groupby("EC")["지상부 길이(mm)"].mean().values
        ),
        row=2, col=1
    )

    fig_growth.add_trace(
        go.Bar(
            x=growth_all.groupby("EC").size().index,
            y=growth_all.groupby("EC").size().values
        ),
        row=2, col=2
    )

    fig_growth.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig_growth, use_container_width=True)

    # 분포
    fig_box = px.box(
        growth_all,
        x="school",
        y="생중량(g)",
        color="school"
    )
    fig_box.update_layout(
        title="학교별 생중량 분포",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # 상관관계
    fig_sc1 = px.scatter(
        growth_all,
        x="잎 수(장)",
        y="생중량(g)",
        color="school",
        title="잎 수 vs 생중량"
    )
    fig_sc2 = px.scatter(
        growth_all,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="school",
        title="지상부 길이 vs 생중량"
    )

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("생육 데이터 원본 및 다운로드"):
        st.dataframe(growth_all)

        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "생육 데이터 다운로드 (XLSX)",
            data=buffer,
            file_name="생육결과데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

