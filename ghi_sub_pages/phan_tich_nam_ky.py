# File: ghi_sub_pages/phan_tich_nam_ky.py
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import plotly.express as px

# Thêm đường dẫn của thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.analysis_logic import (
    get_ghi_yearly_analysis,
    get_ghi_available_years,
    get_ghi_yearly_comparison_data,
    get_ghi_monthly_analysis_for_year
)


# === HÀM VẼ BIỂU ĐỒ SO SÁNH (ĐÃ CÓ SỐ LIỆU) ===
def create_comparison_chart(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = df.index.astype(str)
    x = np.arange(len(labels))
    width = 0.35
    year_cols = df.columns.tolist()

    rects1 = ax.bar(x - width / 2, df[year_cols[0]], width, label=year_cols[0])
    rects2 = ax.bar(x + width / 2, df[year_cols[1]], width, label=year_cols[1])

    ax.set_ylabel('Sản Lượng Tiêu Thụ')
    ax.set_title('Biểu đồ so sánh sản lượng theo kỳ', fontsize=14, weight='bold')
    ax.set_xticks(x, labels)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda val, p: f'{val:,.0f}'))

    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            if height > 0:
                ax.annotate(f'{height:,.0f}', xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha='center', va='bottom', fontsize=8, rotation=90)

    add_labels(rects1)
    add_labels(rects2)
    fig.tight_layout()
    return fig


# === HÀM VẼ BIỂU ĐỒ CHI TIẾT (THÊM MỚI) ===
def create_monthly_detail_chart(df):
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = df['Ky'].astype(str)
    values = df['Tổng Tiêu Thụ Mới']

    rects = ax.bar(labels, values, color='dodgerblue')
    ax.set_ylabel('Sản Lượng Tiêu Thụ')
    ax.set_title(f"Chi tiết sản lượng theo Kỳ", fontsize=14, weight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda val, p: f'{val:,.0f}'))

    for rect in rects:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f'{height:,.0f}', xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

    fig.tight_layout()
    return fig


def show():
    """Hàm để hiển thị nội dung của trang này."""
    st.header("Phân Tích Sản Lượng Theo Năm & Kỳ")

    # ... (Phần so sánh 2 năm giữ nguyên) ...
    st.subheader("So sánh sản lượng giữa hai năm")
    years = get_ghi_available_years()

    if not years:
        st.warning("Không có dữ liệu năm để thực hiện so sánh.")
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            year1 = st.selectbox("Chọn Năm 1", options=years, index=0)
        with col2:
            year2 = st.selectbox("Chọn Năm 2", options=years, index=min(1, len(years) - 1))
        with col3:
            st.write("");
            st.write("")
            if st.button("Thực hiện so sánh", use_container_width=True):
                if year1 == year2:
                    st.error("Vui lòng chọn hai năm khác nhau để so sánh.")
                else:
                    with st.spinner(f"Đang so sánh dữ liệu năm {year1} và {year2}..."):
                        st.session_state.ghi_comparison_df = get_ghi_yearly_comparison_data(int(year1), int(year2))
                        if 'ghi_yearly_df' in st.session_state: del st.session_state.ghi_yearly_df
                        if 'ghi_monthly_df' in st.session_state: del st.session_state.ghi_monthly_df

    st.divider()

    # ... (Phần phân tích tổng quan giữ nguyên) ...
    st.subheader("Phân tích tổng quan sản lượng theo từng năm")
    if st.button("Tải Phân Tích Tổng Quan"):
        with st.spinner("Đang tổng hợp dữ liệu theo năm..."):
            st.session_state.ghi_yearly_df = get_ghi_yearly_analysis()
            if 'ghi_comparison_df' in st.session_state: del st.session_state.ghi_comparison_df
            if 'ghi_monthly_df' in st.session_state: del st.session_state.ghi_monthly_df

    # --- HIỂN THỊ KẾT QUẢ ---
    if 'ghi_comparison_df' in st.session_state and not st.session_state.ghi_comparison_df.empty:
        df_comparison = st.session_state.ghi_comparison_df
        st.write(f"##### Kết quả so sánh sản lượng Năm {year1} và {year2}")
        fig = create_comparison_chart(df_comparison)
        st.pyplot(fig)
        st.dataframe(df_comparison.style.format("{:,.0f}"), use_container_width=True)


    elif 'ghi_yearly_df' in st.session_state and not st.session_state.ghi_yearly_df.empty:

        df_yearly = st.session_state.ghi_yearly_df.copy()

        # Thêm cột "Xem chi tiết"

        df_yearly["Xem chi tiết"] = False

        # --- BỐ CỤC MỚI CHO PHẦN TỔNG QUAN ---

        col1_res, col2_res = st.columns([5, 4], gap="large")  # Tăng tỷ lệ cho bảng

        with col1_res:

            st.write("###### Bảng Tổng Quan Theo Năm (Chọn ô để xem chi tiết)")

            # --- LOGIC MỚI: TÍNH CHIỀU CAO VÀ ÉP ĐỊNH DẠNG SỐ ---

            # 1. Tính chiều cao động để bảng co giãn đủ các dòng

            table_height = (len(df_yearly) + 1) * 35 + 3

            # 2. Tạo bản sao để định dạng, giữ lại bản gốc với kiểu số

            df_display_yearly = df_yearly.copy()

            df_display_yearly['Tổng Tiêu Thụ Mới'] = df_display_yearly['Tổng Tiêu Thụ Mới'].apply(lambda x: f"{x:,.0f}")

            df_display_yearly['Số Lượng Bản Ghi'] = df_display_yearly['Số Lượng Bản Ghi'].apply(lambda x: f"{x:,.0f}")

            # 3. Dùng st.data_editor với các cấu hình mới

            edited_df = st.data_editor(

                df_display_yearly,

                height=table_height,  # Thêm chiều cao động

                column_order=("Xem chi tiết", "Nam", "Tổng Tiêu Thụ Mới", "Số Lượng Bản Ghi"),

                column_config={

                    "Xem chi tiết": st.column_config.CheckboxColumn(default=False),

                    "Nam": st.column_config.TextColumn(disabled=True),

                    # Đổi sang TextColumn vì đã tự định dạng

                    "Tổng Tiêu Thụ Mới": st.column_config.TextColumn(disabled=True),

                    "Số Lượng Bản Ghi": st.column_config.TextColumn(disabled=True),

                },

                use_container_width=True,

                hide_index=True

            )

            selected_row = edited_df[edited_df["Xem chi tiết"]]

            if not selected_row.empty:
                selected_year = selected_row.iloc[0]["Nam"]

                with st.spinner(f"Đang tải chi tiết cho năm {selected_year}..."):
                    st.session_state.ghi_monthly_df = get_ghi_monthly_analysis_for_year(selected_year)

                    st.session_state.selected_year_for_detail = selected_year

                st.rerun()

        with col2_res:
            st.write("###### Biểu đồ Sản Lượng")

            # Chuẩn bị dữ liệu cho biểu đồ
            df_for_chart = df_yearly.set_index('Nam')

            # Tạo biểu đồ bằng Plotly Express
            fig = px.bar(
                df_for_chart,
                y='Tổng Tiêu Thụ Mới',
                text_auto=',.0f',  # Tự động thêm số liệu lên trên cột
                labels={'Nam': 'Năm', 'Tổng Tiêu Thụ Mới': 'Tổng Tiêu Thụ'}
            )

            # Cập nhật định dạng cho tooltip khi di chuột
            fig.update_traces(
                textposition='outside',
                hovertemplate="<b>Năm %{x}</b><br>Tổng Tiêu Thụ: %{y:,.0f}<extra></extra>"
            )

            # Cập nhật layout cho đẹp hơn
            fig.update_layout(
                yaxis_title="Tổng Tiêu Thụ Mới",
                xaxis_title="Năm",
                showlegend=False
            )

            # === THÊM DÒNG NÀY ĐỂ HIỂN THỊ ĐỦ CÁC NĂM ===
            fig.update_xaxes(dtick=1)

            # Hiển thị biểu đồ Plotly
            st.plotly_chart(fig, use_container_width=True)

        if 'ghi_monthly_df' in st.session_state and not st.session_state.ghi_monthly_df.empty:
            df_monthly = st.session_state.ghi_monthly_df
            selected_year_title = st.session_state.selected_year_for_detail
            st.divider()
            st.subheader(f"Chi tiết sản lượng theo Kỳ - Năm {selected_year_title}")

            col1_detail, col2_detail = st.columns([1, 1], gap="large")
            with col1_detail:
                # Bỏ 2 cột thừa và định dạng số
                df_display = df_monthly.drop(columns=['id', 'rowOrder'], errors='ignore')
                st.dataframe(df_display.style.format({
                    'Tổng Tiêu Thụ Mới': '{:,.0f}',
                    'Số Lượng Bản Ghi': '{:,.0f}'
                }), use_container_width=True)
            with col2_detail:
                # Vẽ biểu đồ chi tiết bằng Matplotlib
                fig_monthly = create_monthly_detail_chart(df_monthly)
                st.pyplot(fig_monthly)
    else:
        st.info("Nhấn nút 'Thực hiện so sánh' hoặc 'Tải Phân Tích Tổng Quan' để xem báo cáo.")