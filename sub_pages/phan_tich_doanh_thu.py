import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os
import numpy as np
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import io

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm backend
from backend.analysis_logic import run_yearly_revenue_analysis_from_db, run_monthly_analysis_from_db, \
    run_daily_analysis_from_db
def show():
    # --- Cấu hình trang ---
    st.set_page_config(page_title="Phân tích Doanh thu (DB)", page_icon="💵", layout="wide")

    # === HÀM TIỆN ÍCH MỚI ĐỂ XUẤT EXCEL ===
    @st.cache_data
    def to_excel(df: pd.DataFrame) -> bytes:
        output = io.BytesIO()
        # Ghi đè lên file Excel trong bộ nhớ
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        processed_data = output.getvalue()
        return processed_data
    # =======================================

    # --- Các hàm vẽ biểu đồ (figsize đã được điều chỉnh nhỏ lại) ---
    def create_yearly_revenue_chart(df: pd.DataFrame):
        fig = Figure(figsize=(5.5, 3.8), dpi=100)
        ax1 = fig.add_subplot(111)
        if df is None or df.empty:
            ax1.text(0.5, 0.5, "Không có dữ liệu.", ha='center')
            return fig

        df_plot = df.sort_values(by='Nam')
        labels = df_plot['Nam'].astype(str).tolist()
        x = np.arange(len(labels))
        width = 0.6

        ax1.bar(x, df_plot['TongThucThu'], width, label='Thực thu', color='skyblue')
        ax1.bar(x, df_plot['Tồn Thu'], width, bottom=df_plot['TongThucThu'], label='Tồn Thu', color='salmon', alpha=0.7)
        ax1.plot(x, df_plot['TongDoanhThu'], color='darkgreen', marker='o', linestyle='-', linewidth=1.5, label='Chuẩn thu')

        # THÊM MỚI: Vòng lặp để thêm nhãn NĂM và PHẦN TRĂM
        for i in range(len(df_plot)):
            # Lấy các giá trị
            percent_val = df_plot['% Đạt'].iloc[i]
            thuc_thu_val = df_plot['TongThucThu'].iloc[i]
            year_label = labels[i]

            # Hiển thị % trên đỉnh cột Thực thu
            ax1.annotate(f'{percent_val:.2f}%',
                         (x[i], thuc_thu_val),
                         textcoords="offset points",
                         xytext=(0, 5),  # 5 điểm phía trên cột
                         ha='center',
                         fontsize=8,
                         fontweight='bold')

            # Hiển thị NĂM bên trong cột
            ax1.text(x[i], thuc_thu_val / 2, year_label,  # Đặt ở giữa chiều cao cột
                     ha='center', va='center',
                     fontsize=12, color='white', fontweight='bold')

        ax1.set_ylabel("Số Tiền (VNĐ)", fontsize=9)
        ax1.set_title("Doanh Thu Năm", pad=15, fontsize=10, fontweight='bold')

        # Bỏ nhãn ở trục X vì đã hiển thị bên trong cột
        ax1.set_xticks(x)
        ax1.set_xticklabels([])
        ax1.tick_params(axis='x', length=0)

        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: '{:,.0f}'.format(val)))
        ax1.legend(fontsize=8)
        fig.tight_layout()
        return fig


    def create_monthly_revenue_chart(df: pd.DataFrame, selected_year: int):
        fig = Figure(figsize=(5.5, 3.8), dpi=100)
        ax1 = fig.add_subplot(111)
        if df is None or df.empty:
            ax1.text(0.5, 0.5, "Không có dữ liệu.", ha='center')
            return fig

        df_plot = df.sort_values(by='Ky')
        labels = df_plot['Ky'].astype(str).tolist()
        x = np.arange(len(labels))
        width = 0.35

        ax1.bar(x - width / 2, df_plot['TongDoanhThuKy'], width, label='Chuẩn thu', color='darkcyan')
        ax1.bar(x + width / 2, df_plot['TongThucThuThang'], width, label='Thực thu', color='orange')

        # THÊM MỚI: Vòng lặp để thêm nhãn phần trăm
        for i in range(len(df_plot)):
            percent_val = df_plot['% Đạt'].iloc[i]
            # Lấy chiều cao của cột "Thực thu" để đặt nhãn
            y_pos = df_plot['TongThucThuThang'].iloc[i]

            # Hiển thị text ngay trên cột "Thực thu" (màu cam)
            ax1.annotate(f'{percent_val:.2f}%',
                         (x[i] + width / 2, y_pos),  # Căn theo vị trí cột "Thực thu"
                         textcoords="offset points",
                         xytext=(0, 5),  # 5 điểm theo chiều dọc phía trên
                         ha='center',
                         fontsize=8,
                         fontweight='bold')

        ax1.set_ylabel("Số Tiền (VNĐ)", fontsize=9)
        ax1.set_title(f"Doanh Thu theo Kỳ - Năm {selected_year}", pad=15, fontsize=10, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: '{:,.0f}'.format(val)))
        ax1.legend(fontsize=8)
        fig.tight_layout()
        return fig


    def create_daily_revenue_chart(df: pd.DataFrame, year: int, ky: int):
        fig = Figure(figsize=(5.5, 3.8), dpi=100);
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


    # --- Callback Functions ---
    def run_year_analysis():
        start_year = st.session_state.start_year_input
        end_year = st.session_state.end_year_input
        den_ngay_giai_filter = st.session_state.den_ngay_giai_input
        if start_year > end_year:
            st.error("Năm bắt đầu không được lớn hơn năm kết thúc.")
            return
        with st.spinner(f"Đang phân tích doanh thu từ năm {start_year} đến {end_year}..."):
            try:
                st.session_state.yearly_df = run_yearly_revenue_analysis_from_db(start_year, end_year, den_ngay_giai_filter)
                if 'monthly_df' in st.session_state:
                    del st.session_state.monthly_df
                if 'daily_df' in st.session_state:
                    del st.session_state.daily_df
            except Exception as e:
                st.session_state.yearly_df = None
                st.error("Lỗi phân tích năm.")
                st.exception(e)


    def run_month_analysis():
        selected_year = st.session_state.year_select_in_tab
        with st.spinner(f"Đang tải chi tiết cho năm {selected_year}..."):
            try:
                st.session_state.monthly_df = run_monthly_analysis_from_db(selected_year)
                st.session_state.drilldown_year = selected_year
                if 'daily_df' in st.session_state: del st.session_state.daily_df
            except Exception as e:
                st.error(f"Lỗi tải chi tiết năm {selected_year}."); st.exception(e)


    def run_day_analysis():
        year = st.session_state.get('drilldown_year')
        ky = st.session_state.ky_select_for_day
        if not year: st.warning("Vui lòng chọn năm ở tab Theo Kỳ trước."); return
        with st.spinner(f"Đang tải chi tiết cho năm {year}, kỳ {ky}..."):
            try:
                st.session_state.daily_df = run_daily_analysis_from_db(year, ky)
                st.session_state.drilldown_year_final = year
                st.session_state.drilldown_ky_final = ky
            except Exception as e:
                st.error(f"Lỗi tải chi tiết kỳ {ky}."); st.exception(e)


    # --- Giao diện chính ---
    st.title("💵 Phân tích Doanh thu từ CSDL")

    with st.sidebar:
        st.header("Bộ lọc Tổng quan");
        cy = datetime.now().year
        st.number_input("Từ năm", cy - 30, cy + 5, cy - 1, key="start_year_input")
        st.number_input("Đến năm", cy - 30, cy + 5, cy, key="end_year_input")
        st.date_input("Ngày giải ngân tính đến", date.today(), key="den_ngay_giai_input")
        st.button(label="Chạy Phân Tích", on_click=run_year_analysis)

    tab_year, tab_month, tab_day = st.tabs(["📊 Theo Năm", "📅 Theo Kỳ", "🗓️ Theo Ngày"])

    with tab_year:
        st.header("Tổng quan theo Năm")
        df_yearly = st.session_state.get('yearly_df')
        if df_yearly is None:
            st.info("Vui lòng chạy phân tích từ thanh sidebar bên trái.")
        elif df_yearly.empty:
            st.warning("Không có dữ liệu cho các tiêu chí đã chọn.")
        else:
            col1, col2 = st.columns([1.5, 1])
            with col1:
                df_display_yearly = df_yearly.rename(
                    columns={'Nam': 'Năm', 'TongDoanhThu': 'Chuẩn thu', 'TongThucThu': 'Thực thu'})
                st.dataframe(df_display_yearly.style.format(
                    {'Chuẩn thu': '{:,.0f}', 'Thực thu': '{:,.0f}', 'Tồn Thu': '{:,.0f}', '% Đạt': '{:.2f}%'}),
                             use_container_width=True)
            with col2:
                st.pyplot(create_yearly_revenue_chart(df_yearly))

    with tab_month:
        st.header("Chi tiết theo Kỳ")
        df_yearly_for_select = st.session_state.get('yearly_df')
        if df_yearly_for_select is None or df_yearly_for_select.empty:
            st.info("Chưa có dữ liệu. Vui lòng chạy phân tích ở sidebar trước.")
        else:
            with st.container(border=True):
                years = df_yearly_for_select['Nam'].unique().tolist()
                selected_year = st.selectbox("Chọn năm để xem chi tiết:", options=years, key="year_select_in_tab",
                                             on_change=run_month_analysis)
                st.caption(f"Đang hiển thị chi tiết cho năm: **{st.session_state.get('drilldown_year', 'Chưa chọn')}**")

            df_monthly = st.session_state.get('monthly_df')
            if df_monthly is not None:
                if not df_monthly.empty:
                    st.divider()
                    year_for_title = st.session_state.get('drilldown_year')
                    st.markdown(f"#### Kết quả cho Năm {year_for_title}")

                    # === NÚT TẢI EXCEL CHO BẢNG KỲ ===
                    excel_data_ky = to_excel(df_monthly)
                    st.download_button(
                        label="📥 Tải Excel (Chi tiết Kỳ)",
                        data=excel_data_ky,
                        file_name=f"ChiTiet_Ky_Nam_{year_for_title}.xlsx"
                    )

                    col1, col2 = st.columns([1.2, 1])
                    with col1:
                        df_display_monthly = df_monthly.rename(
                            columns={'Ky': 'Kỳ', 'TongDoanhThuKy': 'Chuẩn thu', 'TongThucThuThang': 'Thực thu'})
                        st.dataframe(df_display_monthly.style.format(
                            {'Chuẩn thu': '{:,.0f}', 'Thực thu': '{:,.0f}', 'Tồn Thu': '{:,.0f}', '% Đạt': '{:.2f}%'}),
                                     use_container_width=True)
                    with col2:
                        st.pyplot(create_monthly_revenue_chart(df_monthly, st.session_state.get('drilldown_year')))

    with tab_day:
        st.header("Chi tiết theo Ngày")

        # Lấy dữ liệu của tháng để có thể chọn kỳ
        df_monthly_for_select = st.session_state.get('monthly_df')

        if df_monthly_for_select is None or df_monthly_for_select.empty:
            st.info("Chưa có dữ liệu theo kỳ. Vui lòng chọn năm ở tab 'Theo Kỳ' trước.")
        else:
            with st.container(border=True):
                year_for_day = st.session_state.get('drilldown_year')
                st.markdown(f"**Năm đang chọn: {year_for_day}**")
                kys = df_monthly_for_select['Ky'].unique().tolist()

                # Sử dụng on_change để tự động tải khi chọn kỳ mới
                st.selectbox("Chọn kỳ để xem chi tiết:", options=kys, key="ky_select_for_day", on_change=run_day_analysis,
                             placeholder="Chọn một kỳ...")
                st.caption(f"Đang hiển thị chi tiết cho kỳ: **{st.session_state.get('drilldown_ky_final', 'Chưa chọn')}**")

        st.divider()

        # Hiển thị kết quả chi tiết ngày nếu có trong session_state
        df_daily = st.session_state.get('daily_df')
        if df_daily is not None:
            year_for_title = st.session_state.get('drilldown_year_final')
            ky_for_title = st.session_state.get('drilldown_ky_final')

            if year_for_title and ky_for_title:
                st.markdown(f"#### Kết quả cho Kỳ {ky_for_title} - Năm {year_for_title}")

                if df_daily.empty:
                    st.warning(f"Không có dữ liệu chi tiết ngày cho kỳ {ky_for_title}/{year_for_title}.")
                else:
                    # === SỬA LỖI XUẤT EXCEL TẠI ĐÂY ===
                    # Tạo một bản sao của DataFrame để xử lý cho việc xuất Excel
                    df_for_excel = df_daily.copy()
                    # Kiểm tra và loại bỏ thông tin timezone khỏi cột datetime
                    if pd.api.types.is_datetime64_any_dtype(df_for_excel['NgayGiaiNgan']):
                        # .dt.tz_localize(None) sẽ loại bỏ thông tin timezone
                        df_for_excel['NgayGiaiNgan'] = df_for_excel['NgayGiaiNgan'].dt.tz_localize(None)

                    excel_data_ngay = to_excel(df_for_excel)
                    st.download_button(
                        label="📥 Tải Excel (Chi tiết Ngày)",
                        data=excel_data_ngay,
                        file_name=f"ChiTiet_Ngay_Ky{ky_for_title}_{year_for_title}.xlsx"
                    )

                    # Bảng và Biểu đồ
                    col1, col2 = st.columns([1.2, 1])
                    with col1:
                        df_display_daily = df_daily.rename(
                            columns={'NgayGiaiNgan': 'Ngày giải ngân', 'SoLuongHoaDon': 'Hóa đơn',
                                     'TongCongNgay': 'Tổng cộng'})
                        st.dataframe(df_display_daily.style.format(
                            {'Ngày giải ngân': '{:%d/%m/%Y}', 'Tổng cộng': '{:,.0f}', 'Hóa đơn': '{:,}'}),
                                     use_container_width=True)
                    with col2:
                        st.pyplot(create_daily_revenue_chart(df_daily, year_for_title, ky_for_title))