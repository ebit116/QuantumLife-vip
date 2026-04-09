import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import dynex
import dimod
from dynex import DynexConfig, ComputeBackend, QPUModel

# ====================== 基础八字函数 ======================
HEAVENLY_STEMS = "甲乙丙丁戊己庚辛壬癸"
EARTHLY_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

def get_ganzhi_day(year: int, month: int, day: int) -> str:
    ref = datetime.date(1900, 1, 1)
    delta = (datetime.date(year, month, day) - ref).days
    stem = delta % 10
    branch = delta % 12
    return HEAVENLY_STEMS[stem] + EARTHLY_BRANCHES[branch]

def get_ganzhi_hour(hour: int) -> str:
    branch_idx = (hour + 1) // 2 % 12
    stem_idx = (branch_idx * 2) % 10
    return HEAVENLY_STEMS[stem_idx] + EARTHLY_BRANCHES[branch_idx]

# ====================== Dynex 高级采样函数 ======================
@st.cache_data(ttl=600)
def predict_minute_fortune(
    day_master: str,
    current_pillar: str,
    backend: ComputeBackend,
    qpu_model: QPUModel | None,
    annealing_time: int,
    num_reads: int,
    shots: int,
    qpu_max_coeff: float,
    default_timeout: float = 300.0,
):
    bqm = dimod.BinaryQuadraticModel('BINARY')
    vars_list = ['career', 'wealth', 'health', 'love', 'study']
    dm_idx = HEAVENLY_STEMS.find(day_master[0])
    for i, v in enumerate(vars_list):
        bqm.add_linear(v, -0.5 if i % 2 == dm_idx % 2 else 0.8)
    if current_pillar[1] in "子午卯酉":
        bqm.add_linear('health', 1.2)
        bqm.add_linear('love', 1.5)
    elif current_pillar[0] == day_master[0]:
        bqm.add_linear('career', -1.0)
        bqm.add_linear('wealth', -0.8)
    bqm.add_quadratic('career', 'wealth', -0.3)
    bqm.add_quadratic('health', 'love', -0.4)

    # QPU 专用缩放处理
    if backend == ComputeBackend.QPU:
        scaled_bqm, scale_factor = dynex.scale_bqm_to_range(bqm, max_abs_coeff=qpu_max_coeff)
        model = dynex.BQM(scaled_bqm)
    else:
        model = dynex.BQM(bqm)
        scale_factor = 1.0

    config = DynexConfig(
        compute_backend=backend,
        qpu_model=qpu_model,
        default_timeout=default_timeout,
        use_notebook_output=False,
    )

    sampler = dynex.DynexSampler(model, config=config)
    sampleset = sampler.sample(
        num_reads=num_reads,
        shots=shots,
        annealing_time=annealing_time,
        qpu_max_coeff=qpu_max_coeff if backend == ComputeBackend.QPU else None,
    )

    best = sampleset.first
    state = best.sample
    energy = best.energy / scale_factor if backend == ComputeBackend.QPU else best.energy

    scores = {k: "优秀" if v == 1 else "一般" for k, v in state.items()}
    total_score = max(0, min(100, int((5 - energy) / 5 * 100)))

    desc = f"整体运势 **{total_score}** 分 | 事业{scores['career']}、财运{scores['wealth']}、健康{scores['health']}、感情{scores['love']}、学业{scores['study']}"

    return {
        "pillar": current_pillar,
        "total_score": total_score,
        "details": scores,
        "description": desc,
        "energy": energy,
        "scale_factor": scale_factor,
        "job_id": getattr(sampleset, 'job_id', 'N/A') if hasattr(sampleset, 'job_id') else 'N/A'
    }

# ====================== Streamlit 界面 ======================
st.set_page_config(page_title="Dynex 量子八字 · 高级采样", page_icon="🌌", layout="wide")
st.title("🌌 Dynex 量子增强 · 八字每分钟运势（高级采样版）")
st.markdown("**已集成 Dynex QaaS 全部高级采样参数**：QPU 缩放、退火时间、shots、num_reads 等")

with st.sidebar:
    st.header("📅 基础信息")
    birth_date = st.date_input("出生日期", value=datetime.date(1995, 6, 15))
    target_date = st.date_input("查询日期", value=datetime.date.today())
    granularity = st.selectbox("时间粒度", [1, 5, 10, 15, 30, 60], index=5, format_func=lambda x: f"每{x}分钟" if x<60 else "每小时")

    st.divider()
    st.header("⚙️ 高级采样设置")
    
    backend_str = st.selectbox("计算后端", ["CPU", "GPU", "QPU"], index=0)
    backend = {"CPU": ComputeBackend.CPU, "GPU": ComputeBackend.GPU, "QPU": ComputeBackend.QPU}[backend_str]

    qpu_model = None
    if backend == ComputeBackend.QPU:
        qpu_model = st.selectbox("QPU 型号", [QPUModel.APOLLO_RC1], format_func=lambda x: x.name)

    annealing_time = st.slider("退火时间 (ms)", 10, 1000, 300, help="QPU 模式下越大越精准")
    num_reads = st.slider("num_reads", 10, 100, 30, help="并行采样次数")
    shots = st.slider("shots", 1, 20, 3, help="网络请求的最小解数量")
    qpu_max_coeff = st.slider("QPU 最大系数", 1.0, 20.0, 9.0, help="QPU 缩放上限")
    default_timeout = st.slider("超时时间 (秒)", 60, 600, 300)

    run_button = st.button("🚀 开始高级量子采样", type="primary")

if run_button:
    with st.spinner("正在连接 Dynex 量子路由引擎并进行高级采样..."):
        birth_pillar = get_ganzhi_day(birth_date.year, birth_date.month, birth_date.day)
        day_master = birth_pillar[0]
        st.success(f"命主日干：**{day_master}**（{birth_pillar}日） | 后端：**{backend_str}**")

        results = []
        start = datetime.datetime.combine(target_date, datetime.time(0, 0))
        current = start
        total_steps = (24 * 60) // granularity
        progress_bar = st.progress(0)
        status_text = st.empty()

        idx = 0
        while current.hour < 24:
            hour_pillar = get_ganzhi_hour(current.hour)
            time_str = current.strftime("%H:%M")
            status_text.text(f"采样 {time_str} ...")

            fortune = predict_minute_fortune(
                day_master=day_master,
                current_pillar=hour_pillar,
                backend=backend,
                qpu_model=qpu_model,
                annealing_time=annealing_time,
                num_reads=num_reads,
                shots=shots,
                qpu_max_coeff=qpu_max_coeff,
                default_timeout=default_timeout,
            )

            results.append({
                "时间": time_str,
                "时柱": hour_pillar,
                "总分": fortune["total_score"],
                "事业": fortune["details"]["career"],
                "财运": fortune["details"]["wealth"],
                "健康": fortune["details"]["health"],
                "感情": fortune["details"]["love"],
                "学业": fortune["details"]["study"],
                "描述": fortune["description"],
                "能量": round(fortune["energy"], 4),
                "缩放因子": fortune["scale_factor"],
                "Job ID": fortune["job_id"]
            })

            idx += 1
            progress_bar.progress(idx / total_steps)
            current += datetime.timedelta(minutes=granularity)

        df = pd.DataFrame(results)

        st.subheader(f"📅 {target_date} 全天运势（高级采样 · {backend_str}）")
        
        fig = px.line(df, x="时间", y="总分", markers=True, title="全天运势总分曲线（Dynex 高级采样）")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df.style.background_gradient(cmap="RdYlGn", subset=["总分"]),
            use_container_width=True,
            hide_index=True
        )

        col1, col2 = st.columns(2)
        best = df.loc[df["总分"].idxmax()]
        worst = df.loc[df["总分"].idxmin()]
        with col1:
            st.metric("🌟 最佳时刻", f"{best['时间']} ({best['总分']}分)", delta=best['时柱'])
        with col2:
            st.metric("⚠️ 低谷时刻", f"{worst['时间']} ({worst['总分']}分)", delta=worst['时柱'])

        st.info("**Dynex 高级采样信息**：\n"
                f"- 后端：{backend_str} {'(' + qpu_model.name + ')' if backend == ComputeBackend.QPU else ''}\n"
                f"- 退火时间：{annealing_time} ms | num_reads：{num_reads} | shots：{shots}\n"
                f"- QPU 缩放上限：{qpu_max_coeff}（缩放因子已在结果中显示）")

else:
    st.info("👈 在左侧填写信息并点击「开始高级量子采样」")
    st.caption("Powered by Dynex QaaS 高级采样 + Streamlit | 技术演示 · 娱乐参考")
