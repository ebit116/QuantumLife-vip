# QuantumLife-vip
Integrated Dynex advanced sampling function  集成 Dynex 高级采样功能 https://github.com/Dynex-Development/py-sdk
**✅ 已集成 Dynex 高级采样功能！**

以下是**完整升级版 Streamlit 应用**，已全面集成 Dynex SDK 的**高级采样配置**（基于最新 py-sdk 文档）：

- ✅ **Backend 自由选择**：CPU / GPU / QPU  
- ✅ **QPU 专用模型**：APOLLO_RC1（可扩展）  
- ✅ **高级采样参数**：`annealing_time`、`num_reads`、`shots`、`qpu_max_coeff`  
- ✅ **QPU 自动缩放**：自动调用 `dynex.scale_bqm_to_range()` 并恢复原始能量  
- ✅ **可配置 Timeout / Description**  
- ✅ 界面新增「高级采样设置」折叠面板，操作更直观  
- ✅ 采样结果显示真实 Dynex Job ID、能量值、缩放因子（QPU 模式下）  

---

### 1. 安装依赖（只需执行一次）
```bash
pip install streamlit dynex dimod pandas plotly
