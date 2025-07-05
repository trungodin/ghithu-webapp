# File: ghi_sub_pages/phan_tich_to_may.py

import streamlit as st
import pandas as pd
import sys
import os
import io
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Thêm đường dẫn của thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.analysis_logic import (
    get_ghi_team_analysis_data,
    get_ghi_outstanding_invoices_for_team,
)

# Bảng tra cứu Máy -> Tên Nhân Viên
EMPLOYEE_MAP = {
    11: "Lê Trung Quốc", 12: "Vũ Hoàng Quốc Việt", 13: "Lê Hồng Tuấn", 14: "Bùi Xuân Hoàng",
    15: "Lương Văn Hùng", 16: "Huỳnh Kim Luân", 17: "Trần Hiệp Hòa", 18: "Nguyễn Thanh Hải",
    21: "Trần Văn Đức", 22: "Võ Viết Trang", 23: "Trần Quang Phương", 24: "Trầm Tấn Hùng",
    25: "Phạm Văn Có", 26: "Lê Tuân", 27: "Lê Tuấn Kiệt", 28: "Phùng Trung Tín",
    31: "Võ Trọng Sĩ", 32: "Phạm Văn Mai", 33: "Đỗ Lê Anh Tú", 34: "Nguyễn Vĩnh Bảo Kh",
    35: "Nguyễn Việt Toàn Nhân", 36: "Trương Trọng Nhân", 37: "Đặng Anh Phương",
    41: "Trần Quốc Tuấn", 42: "Vũ Hoàng", 43: "Dương Quốc Thông", 44: "Huỳnh Ngọc Binh",
    45: "Hoàng Anh Vũ", 46: "Phan Thành Tín", 47: "Nguyễn Tấn Lợi"
}


# --- CÁC HÀM TIỆN ÍCH ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()


def create_pie_chart(total_collected, total_debt):
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    if total_collected <= 0 and total_debt <= 0:
        ax.text(0.5, 0.5, "Không có dữ liệu.", ha='center', va='center');
        ax.axis('off');
        return fig
    labels, sizes, colors = [], [], []
    total_collected, total_debt = round(total_collected), round(total_debt)
    if total_collected > 0:
        labels.append(f'Đã Thu\n({total_collected:,.0f})');
        sizes.append(total_collected);
        colors.append('lightgreen')
    if total_debt > 0:
        labels.append(f'Còn Nợ\n({total_debt:,.0f})');
        sizes.append(total_debt);
        colors.append('lightcoral')
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.8, shadow=False)
    ax.axis('equal');
    fig.tight_layout();
    return fig


def create_team_analysis_chart(df):
    df_chart = df.copy()
    df_chart.sort_values(by='% Đạt', ascending=False, inplace=True)
    df_chart['Tồn'] = df_chart['TongPhatSinh'] - df_chart['ThucThu']
    labels = df_chart.index
    thuc_thu_values = df_chart['ThucThu']
    ton_values = df_chart['Tồn']
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, thuc_thu_values, label='Thực Thu', color='cornflowerblue')
    ax.bar(labels, ton_values, bottom=thuc_thu_values, label='Còn Nợ', color='salmon')
    ax.set_ylabel('Số Tiền');
    ax.set_title('Phân Tích Phát Sinh và Thực Thu', fontsize=14, weight='bold')
    ax.legend();
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda val, p: f'{val:,.0f}'))
    plt.xticks(rotation=75, ha='right');
    fig.tight_layout()
    return fig


# === HÀM HỖ TRỢ SẮP XẾP BẢNG THEO LOGIC CŨ ===
def custom_machine_sort_key(row):
    try:
        may = int(row['May'])
        last_machines = {18, 28, 37, 47}
        group_id = may // 10
        is_last_machine = may in last_machines
        order_in_group = 0 if is_last_machine else may
        return (group_id, order_in_group)
    except:
        return (99, 99)


def show():
    st.header("Phân Tích Theo Tổ Máy")
    st.subheader("Tùy chọn Phân tích")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        team_options = {"Tất cả các Tổ": None, "Tổ 1": 1, "Tổ 2": 2, "Tổ 3": 3, "Tổ 4": 4}
        team_selection = st.selectbox("Chọn Tổ Máy", options=list(team_options.keys()))
        team_filter_val = team_options[team_selection]
    with col2:
        year_filter = st.number_input("Năm Phân Tích", 2020, datetime.now().year, datetime.now().year)
    with col3:
        period_filter = st.number_input("Kỳ Phân Tích", 1, 12, datetime.now().month)
    with col4:
        st.write("");
        st.write("")
        if st.button("Tải & Phân Tích Dữ Liệu", type="primary", use_container_width=True):
            with st.spinner("Đang tải dữ liệu..."):
                st.session_state.ghi_team_df = get_ghi_team_analysis_data(team_filter_val, year_filter, period_filter)
                st.session_state.ghi_team_filters = {"year": year_filter, "period": period_filter}
                if 'ghi_outstanding_invoices_df' in st.session_state: del st.session_state.ghi_outstanding_invoices_df
                if 'selected_machine_info' in st.session_state: del st.session_state.selected_machine_info

    if 'ghi_team_df' in st.session_state and not st.session_state.ghi_team_df.empty:
        df_team_original = st.session_state.ghi_team_df.copy()

        # === KHÔI PHỤC LẠI LOGIC SẮP XẾP CŨ ===
        df_team_original['sort_key'] = df_team_original.apply(custom_machine_sort_key, axis=1)
        df_team = df_team_original.sort_values(by='sort_key').drop(columns=['sort_key'])

        df_team['Tên Nhân Viên'] = df_team['May'].map(EMPLOYEE_MAP).fillna("Không xác định")
        df_team['Xem HĐ Nợ'] = False

        df_display = df_team.copy()
        cols_to_format = ['SoLuongBanGhi', 'TongPhatSinh', 'SoLuongThuDuoc', 'ThucThu']
        for col in cols_to_format:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")

        st.divider()
        st.subheader(
            f"Kết quả Phân tích - {team_selection} - Kỳ {st.session_state.ghi_team_filters['period']}/{st.session_state.ghi_team_filters['year']}")

        col_res1, col_res2 = st.columns([3, 2], gap="large")
        with col_res1:
            st.write("###### Bảng tổng hợp (Chọn ô để xem chi tiết HĐ nợ)")
            edited_df = st.data_editor(df_display, key="team_analysis_summary_table",
                                       column_order=(
                                       "Xem HĐ Nợ", "May", "Tên Nhân Viên", "SoLuongBanGhi", "TongPhatSinh",
                                       "SoLuongThuDuoc", "ThucThu", "% Đạt"),
                                       column_config={"Xem HĐ Nợ": st.column_config.CheckboxColumn(default=False),
                                                      "May": st.column_config.TextColumn(disabled=True),
                                                      "Tên Nhân Viên": st.column_config.TextColumn(disabled=True),
                                                      "SoLuongBanGhi": st.column_config.TextColumn("SL Bản Ghi",
                                                                                                   disabled=True),
                                                      "TongPhatSinh": st.column_config.TextColumn("Tổng Phát Sinh",
                                                                                                  disabled=True),
                                                      "SoLuongThuDuoc": st.column_config.TextColumn("SL Thu Được",
                                                                                                    disabled=True),
                                                      "ThucThu": st.column_config.TextColumn("Thực Thu", disabled=True),
                                                      "% Đạt": st.column_config.ProgressColumn("% Đạt", format="%.1f%%",
                                                                                               min_value=0,
                                                                                               max_value=100)},
                                       use_container_width=True, hide_index=True)

            selected_rows = edited_df[edited_df["Xem HĐ Nợ"]]
            if not selected_rows.empty:
                selected_row = selected_rows.iloc[0]
                machine_id = int(selected_row["May"])

                original_row = df_team[df_team['May'] == machine_id].iloc[0]
                tong_phat_sinh = original_row["TongPhatSinh"]
                thuc_thu = original_row["ThucThu"]

                current_filters = st.session_state.ghi_team_filters
                with st.spinner(f"Đang tải HĐ nợ cho Máy {machine_id}..."):
                    st.session_state.ghi_outstanding_invoices_df = get_ghi_outstanding_invoices_for_team(machine_id,
                                                                                                         current_filters[
                                                                                                             'year'],
                                                                                                         current_filters[
                                                                                                             'period'])
                    st.session_state.selected_machine_info = {"id": machine_id, "tong_phat_sinh": tong_phat_sinh,
                                                              "thuc_thu": thuc_thu}

                # === THAY ĐỔI QUAN TRỌNG TẠI ĐÂY ===
                # Đặt trạng thái cho radio button ở trang GHI
                st.session_state.last_ghi_subpage = "Phân Tích Theo Tổ Máy"

                # Chuyển trang
                st.switch_page("pages/_chi_tiet_hd_no.py")

        with col_res2:
            st.write("###### Biểu đồ so sánh Phát sinh và Thực thu")
            chart_df = df_team.copy()
            chart_df = chart_df.set_index('Tên Nhân Viên')
            fig_team = create_team_analysis_chart(chart_df)
            st.pyplot(fig_team)

    if 'ghi_outstanding_invoices_df' in st.session_state:
        df_invoices = st.session_state.ghi_outstanding_invoices_df
        machine_info = st.session_state.selected_machine_info
        st.divider()
        st.subheader(f"Chi tiết Hóa đơn còn nợ - Máy {machine_info['id']}")

        if df_invoices.empty:
            st.warning("Không tìm thấy hóa đơn nào còn nợ cho nhân viên này trong kỳ đã chọn.")
        else:
            summary_cols = st.columns([2, 1], gap="large")
            with summary_cols[0]:
                st.write("###### Tóm tắt Tỷ lệ")
                tong_no = df_invoices['TONGCONG'].sum()
                tong_phat_sinh_nv = machine_info['tong_phat_sinh']
                da_thu = machine_info['thuc_thu']
                metric_cols = st.columns(3)
                metric_cols[0].metric("Tổng Phát Sinh", f"{tong_phat_sinh_nv:,.0f}")
                metric_cols[1].metric("Còn Nợ", f"{tong_no:,.0f}")
                metric_cols[2].metric("Đã Thu", f"{da_thu:,.0f}")
            with summary_cols[1]:
                st.write("###### Biểu đồ")
                pie_fig = create_pie_chart(da_thu, tong_no)
                st.pyplot(pie_fig)

            st.markdown("---")
            st.write("###### Danh sách hóa đơn")
            excel_data = to_excel(df_invoices)
            st.download_button(label="📥 Tải Excel (DS Nợ)", data=excel_data,
                               file_name=f"HĐ_No_May_{machine_info['id']}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            df_display_invoices = df_invoices.copy()
            for col in df_display_invoices.columns:
                if 'int' in str(df_display_invoices[col].dtype) or 'float' in str(df_display_invoices[col].dtype):
                    df_display_invoices[col] = df_display_invoices[col].apply(
                        lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            st.dataframe(df_display_invoices, use_container_width=True)

    elif 'ghi_team_df' not in st.session_state:
        st.info("Chọn các tùy chọn và nhấn nút để xem phân tích.")