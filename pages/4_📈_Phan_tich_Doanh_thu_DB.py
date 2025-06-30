import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os
import numpy as np
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm backend
from backend.analysis_logic import run_yearly_revenue_analysis_from_db, run_monthly_analysis_from_db, \
    run_daily_analysis_from_db

# --- Cấu hình trang ---
st.set_page_config(page_title="Phân tích Doanh thu (DB)", page_icon="💵", layout="wide")


# --- Các hàm vẽ biểu đồ (Không thay đổi) ---
def create_yearly_revenue_chart(df: pd.DataFrame):
    fig = Figure(figsize=(6, 4), dpi=100);
    ax1 = fig.add_subplot(111)
    if df is None or df.empty: ax1.text(0.5, 0.5, "Không có dữ liệu.", ha='center'); return fig
    df_plot = df.sort_values(by='Nam');
    labels = df_plot['Nam'].astype(str).tolist();
    x = np.arange(len(labels));
    width = 0.6
    ax1.bar(x, df_plot['TongThucThu'], width, label='Tổng Thực Thu', color='skyblue')
    ax1.bar(x, df_plot['Tồn Thu'], width, bottom=df_plot['TongThucThu'], label='Tồn Thu', color='salmon')
    ax1.plot(x, df_plot['TongDoanhThu'], color='darkgreen', marker='o', linestyle='-', linewidth=1.5,
             label='Tổng Doanh Thu')
    ax1.set_ylabel("Số Tiền (VNĐ)", fontsize=9);
    ax1.set_title("Doanh Thu Năm", pad=15, fontsize=10, fontweight='bold')
    ax1.set_xticks(x);
    ax1.set_xticklabels(labels, rotation=0, ha="center", fontsize=8)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: '{:,.0f}'.format(val)))
    ax1.legend(fontsize=8);
    fig.tight_layout();
    return fig


def create_monthly_revenue_chart(df: pd.DataFrame, selected_year: int):
    fig = Figure(figsize=(6, 4), dpi=100);
    ax1 = fig.add_subplot(111)
    if df is None or df.empty: ax1.text(0.5, 0.5, "Không có dữ liệu.", ha='center'); return fig
    df_plot = df.sort_values(by='Ky');
    labels = df_plot['Ky'].astype(str).tolist();
    x = np.arange(len(labels));
    width = 0.35
    ax1.bar(x - width / 2, df_plot['TongDoanhThuKy'], width, label='Doanh Thu Kỳ', color='darkcyan')
    ax1.bar(x + width / 2, df_plot['TongThucThuThang'], width, label='Thực Thu Tháng', color='orange')
    ax1.set_ylabel("Số Tiền (VNĐ)", fontsize=9)
    ax1.set_title(f"Doanh Thu theo Kỳ - Năm {selected_year}", pad=15, fontsize=10, fontweight='bold')
    ax1.set_xticks(x);
    ax1.set_xticklabels(labels);
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: '{:,.0f}'.format(val)))
    ax1.legend(fontsize=8);
    fig.tight_layout();
    return fig


def create_daily_revenue_chart(df: pd.DataFrame, year: int, ky: int):
    fig = Figure(figsize=(6, 4), dpi=100);
    ax = fig.add_subplot(111)
    if df is None or df.empty: ax.text(0.5, 0.5, "Không có dữ liệu.", ha='center'); return fig
    df_plot = df.dropna(subset=['NgayGiaiNgan']).sort_values(by='NgayGiaiNgan')
    if df_plot.empty: ax.text(0.5, 0.5, "Không có dữ liệu hợp lệ.", ha='center'); return fig
    ax.plot(df_plot['NgayGiaiNgan'], df_plot['TongCongNgay'], marker='o', linestyle='-', markersize=4, color='teal')
    ax.set_title(f"Thu Theo Ngày - Kỳ {ky}, Năm {year}", fontsize=10, pad=15)
    ax.set_ylabel("Tổng Cộng Ngày (VNĐ)", fontsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: '{:,.0f}'.format(val)))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10));
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate(rotation=30, ha='right');
    ax.tick_params(labelsize=8);
    ax.grid(True, linestyle='--', alpha=0.6);
    fig.tight_layout();
    return fig


# --- Giao diện chính ---
st.title("💵 Phân tích Doanh thu từ CSDL")

# Sidebar chỉ còn duy nhất bộ lọc tổng quan ban đầu
with st.sidebar:
    st.header("Bộ lọc Tổng quan");
    with st.form(key='yearly_revenue_form'):
        cy = datetime.now().year;
        start_year = st.number_input("Từ năm", cy - 30, cy + 5, cy - 1)
        end_year = st.number_input("Đến năm", cy - 30, cy + 5, cy)
        den_ngay_giai_filter = st.date_input("Ngày giải ngân tính đến", date.today())
        submit_button = st.form_submit_button(label="Chạy Phân Tích")

# --- Xử lý logic ---
if submit_button:
    if start_year > end_year:
        st.error("Năm bắt đầu không được lớn hơn năm kết thúc.")
    else:
        with st.spinner(f"Đang phân tích doanh thu từ năm {start_year} đến {end_year}..."):
            try:
                st.session_state.yearly_df = run_yearly_revenue_analysis_from_db(start_year, end_year,
                                                                                 den_ngay_giai_filter)
                # Xóa các kết quả chi tiết cũ khi chạy lại phân tích tổng quan
                if 'monthly_df' in st.session_state: del st.session_state.monthly_df
                if 'daily_df' in st.session_state: del st.session_state.daily_df
            except Exception as e:
                st.session_state.yearly_df = None;
                st.error("Lỗi phân tích năm.");
                st.exception(e)

# === BỐ CỤC TAB MỚI GỌN GÀNG HƠN ===
tab_year, tab_month, tab_day = st.tabs(["📊 Theo Năm", "📅 Theo Kỳ", "🗓️ Theo Ngày"])

# --- Tab 1: Phân tích theo năm ---
with tab_year:
    st.header("Tổng quan theo Năm")
    df_yearly = st.session_state.get('yearly_df')
    if df_yearly is None:
        st.info("Vui lòng chạy phân tích từ thanh sidebar bên trái.")
    elif df_yearly.empty:
        st.warning("Không có dữ liệu cho các tiêu chí đã chọn.")
    else:
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.dataframe(df_yearly.style.format(
                {'TongDoanhThu': '{:,.0f}', 'TongThucThu': '{:,.0f}', 'Tồn Thu': '{:,.0f}', '% Đạt': '{:.2f}%'}),
                         height=35 * (len(df_yearly) + 1))
        with col2:
            st.pyplot(create_yearly_revenue_chart(df_yearly))

# --- Tab 2: Phân tích theo kỳ ---
with tab_month:
    st.header("Chi tiết theo Kỳ")
    df_yearly_for_select = st.session_state.get('yearly_df')
    if df_yearly_for_select is None or df_yearly_for_select.empty:
        st.info("Chưa có dữ liệu phân tích theo năm. Vui lòng chạy phân tích ở sidebar trước.")
    else:
        # Bộ lọc được đặt ngay trong tab
        years = df_yearly_for_select['Nam'].unique().tolist()
        col1, col2 = st.columns([1, 4])
        selected_year = col1.selectbox("Chọn năm để xem chi tiết:", options=years, key="year_select_in_tab")
        if col2.button("Xem chi tiết Kỳ", key="view_monthly_in_tab"):
            with st.spinner(f"Đang tải chi tiết cho năm {selected_year}..."):
                try:
                    st.session_state.monthly_df = run_monthly_analysis_from_db(selected_year)
                    st.session_state.drilldown_year = selected_year
                except Exception as e:
                    st.error(f"Lỗi tải chi tiết năm {selected_year}.");
                    st.exception(e)

    st.divider()

    # Hiển thị kết quả kỳ nếu có
    df_monthly = st.session_state.get('monthly_df')
    if df_monthly is not None and not df_monthly.empty:
        year_for_title = st.session_state.get('drilldown_year')
        st.markdown(f"#### Kết quả cho Năm {year_for_title}")
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.dataframe(df_monthly.style.format(
                {'TongDoanhThuKy': '{:,.0f}', 'TongThucThuThang': '{:,.0f}', 'Tồn Thu': '{:,.0f}', '% Đạt': '{:.2f}%'}),
                         height=35 * (len(df_monthly) + 1))
        with col2:
            st.pyplot(create_monthly_revenue_chart(df_monthly, year_for_title))

# --- Tab 3: Phân tích theo ngày ---
with tab_day:
    st.header("Chi tiết theo Ngày")
    # Cần có dữ liệu năm và kỳ để có thể chọn
    if st.session_state.get('yearly_df') is None or st.session_state.get('monthly_df') is None:
        st.info("Vui lòng chạy phân tích theo Năm và theo Kỳ trước.")
    else:
        # Bộ lọc cho ngày
        col1, col2, col3 = st.columns([1, 1, 3])
        # Chọn năm
        years_for_day = st.session_state.get('yearly_df')['Nam'].unique().tolist()
        selected_year_for_day = col1.selectbox("Chọn năm:", options=years_for_day, key="year_select_for_day")
        # Chọn kỳ
        # Chạy lại phân tích kỳ nếu năm thay đổi để có danh sách kỳ đúng
        if st.button("Tải danh sách kỳ", key="load_kys_for_day"):
            st.session_state.monthly_df_for_day_select = run_monthly_analysis_from_db(selected_year_for_day)

        if st.session_state.get('monthly_df_for_day_select') is not None:
            kys_for_day = st.session_state.get('monthly_df_for_day_select')['Ky'].unique().tolist()
            selected_ky_for_day = col2.selectbox("Chọn kỳ:", options=kys_for_day, key="ky_select_for_day")
            if col3.button("Xem chi tiết Ngày", key="view_daily_in_tab"):
                with st.spinner(f"Đang tải chi tiết cho năm {selected_year_for_day}, kỳ {selected_ky_for_day}..."):
                    try:
                        st.session_state.daily_df = run_daily_analysis_from_db(selected_year_for_day,
                                                                               selected_ky_for_day)
                        st.session_state.drilldown_year_final = selected_year_for_day
                        st.session_state.drilldown_ky_final = selected_ky_for_day
                    except Exception as e:
                        st.error(f"Lỗi tải chi tiết kỳ {selected_ky_for_day}.");
                        st.exception(e)

    st.divider()

    # Hiển thị kết quả ngày
    df_daily = st.session_state.get('daily_df')
    if df_daily is not None and not df_daily.empty:
        year_for_title = st.session_state.get('drilldown_year_final')
        ky_for_title = st.session_state.get('drilldown_ky_final')
        st.markdown(f"#### Kết quả cho Kỳ {ky_for_title} - Năm {year_for_title}")
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.dataframe(df_daily.style.format({'TongCongNgay': '{:,.0f}'}), height=35 * (len(df_daily) + 1))
        with col2:
            st.pyplot(create_daily_revenue_chart(df_daily, year_for_title, ky_for_title))