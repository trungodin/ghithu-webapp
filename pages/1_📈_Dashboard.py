# GhithuWebApp/pages/1_📈_Dashboard.py

import streamlit as st
import pandas as pd
from matplotlib.figure import Figure
import matplotlib.ticker as mticker
import sys
import os

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Bây giờ mới import các module của dự án
from backend.analysis_logic import fetch_dashboard_data

# --- Cấu hình trang ---
st.set_page_config(
    page_title="Dashboard Tổng quan",
    page_icon="📈",
    layout="wide"
)


# --- Các hàm vẽ biểu đồ (Tái sử dụng từ logic cũ) ---

def create_bar_chart(data: pd.Series):
    """Tạo biểu đồ cột nợ theo khu vực."""
    fig = Figure(figsize=(7, 5))
    ax = fig.add_subplot(111)
    if not data.empty:
        data.plot(kind='bar', ax=ax, color='#2980b9')
        ax.set_ylabel('Tổng tiền nợ (VND)', fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        ax.tick_params(axis='x', labelrotation=45, labelsize=9)
    ax.set_title('Top 10 Khu vực có Nợ Tồn Cao nhất', fontsize=14, weight='bold')
    ax.set_xlabel('Mã Khu vực (GB)', fontsize=10)
    fig.tight_layout()
    return fig


def create_line_chart(data: pd.Series):
    """Tạo biểu đồ đường xu hướng nợ theo thời gian."""
    fig = Figure(figsize=(7, 5))
    ax = fig.add_subplot(111)
    if not data.empty:
        data.plot(kind='line', ax=ax, marker='o', color='#c0392b')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.set_title('Xu hướng Nợ Tồn (2 năm gần nhất)', fontsize=14, weight='bold')
    ax.set_ylabel('Tổng tiền nợ (VND)', fontsize=10)
    ax.set_xlabel('Tháng/Năm', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    fig.tight_layout()
    return fig


# --- Giao diện chính của trang Dashboard ---

st.title("📈 Dashboard Tổng quan Tình hình Nợ tồn")

# Nút làm mới dữ liệu
if st.button("Làm mới dữ liệu"):
    # Xóa cache của hàm fetch_dashboard_data
    st.cache_data.clear()
    st.toast("Đang tải lại dữ liệu mới nhất...")


# Sử dụng decorator của Streamlit để cache kết quả
# ttl=3600 nghĩa là cache sẽ hết hạn sau 3600 giây (1 giờ)
@st.cache_data(ttl=3600)
def cached_fetch_dashboard_data():
    return fetch_dashboard_data()


# Lấy dữ liệu và hiển thị
try:
    with st.spinner("Đang tải dữ liệu từ server, vui lòng chờ..."):
        data = cached_fetch_dashboard_data()

    if not data:
        st.warning("Không có dữ liệu nợ tồn để hiển thị.")
    else:
        # --- Hiển thị các chỉ số KPI ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Tổng Nợ Tồn",
                value=f"{int(data.get('total_debt', 0)):,}"
            )
        with col2:
            st.metric(
                label="Tổng số Khách hàng nợ",
                value=f"{data.get('total_debtors', 0):,}"
            )
        with col3:
            st.metric(
                label="Số KH nợ >= 3 kỳ",
                value=f"{data.get('debtors_over_3_periods', 0):,}"
            )

        st.divider()

        # --- Hiển thị các biểu đồ ---
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            debt_by_gb_data = data.get('debt_by_gb', pd.Series(dtype=float))
            fig_bar = create_bar_chart(debt_by_gb_data)
            st.pyplot(fig_bar)

        with chart_col2:
            debt_over_time_data = data.get('debt_over_time', pd.Series(dtype=float))
            fig_line = create_line_chart(debt_over_time_data)
            st.pyplot(fig_line)

except Exception as e:
    st.error(f"Đã xảy ra lỗi khi tải dữ liệu Dashboard: {e}")
    st.exception(e)