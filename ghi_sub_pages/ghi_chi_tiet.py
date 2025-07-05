# File: ghi_sub_pages/ghi_chi_tiet.py

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
from matplotlib.figure import Figure

# Thêm đường dẫn của thư mục gốc để có thể import từ 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.analysis_logic import get_ghi_bo_loc_data, get_ghi_chi_tiet_data, get_ghi_chart_data


# --- HÀM VẼ BIỂU ĐỒ ---
def create_analysis_chart(df, group_by_column_display):
    """Vẽ biểu đồ phân tích từ DataFrame đã được tổng hợp."""
    if df.empty:
        st.warning(f"Không có dữ liệu để vẽ biểu đồ theo {group_by_column_display}.")
        return None

    fig = Figure(figsize=(10, 6))
    ax = fig.add_subplot(111)

    # Giới hạn 20 giá trị đầu để biểu đồ không quá dày đặc
    df_sorted = df.sort_values(by='RecordCount', ascending=False).head(20)

    categories = df_sorted.iloc[:, 0].astype(str)
    record_counts = df_sorted['RecordCount']

    ax.bar(categories, record_counts, color='skyblue', label='Số lượng bản ghi')
    ax.set_ylabel('Số Lượng Bản Ghi')
    ax.set_title(f'Phân tích theo {group_by_column_display} (Top 20)', fontsize=14)
    ax.tick_params(axis='x', rotation=45, labelsize=9)
    ax.grid(True, linestyle='--', alpha=0.6)

    # Thêm nhãn số lượng trên mỗi cột
    for i, v in enumerate(record_counts):
        ax.text(i, v + (record_counts.max() * 0.01), str(v), ha='center', va='bottom', fontsize=8)

    fig.tight_layout()
    return fig


# --- HÀM CHÍNH ĐỂ HIỂN THỊ TRANG ---
def show():
    st.header("Dữ Liệu Chi Tiết")

    # Tải dữ liệu cho các bộ lọc
    filter_data = get_ghi_bo_loc_data()

    with st.expander("⚙️ Bộ lọc Dữ liệu", expanded=True):
        st.write("##### Lọc theo Thời gian")
        time_cols = st.columns(4)
        with time_cols[0]: ky_from = st.number_input("Từ Kỳ", 1, 12, datetime.now().month, key="ky_from")
        with time_cols[1]: nam_from = st.number_input("Từ Năm", 2020, 2099, datetime.now().year, key="nam_from")
        with time_cols[2]: ky_to = st.number_input("Đến Kỳ (Tùy chọn)", 1, 12, None, placeholder="Để trống...",
                                                   key="ky_to")
        with time_cols[3]: nam_to = st.number_input("Đến Năm (Tùy chọn)", 2020, 2099, None, placeholder="Để trống...",
                                                    key="nam_to")
        st.markdown("---")

        st.write("##### Lọc theo Thuộc tính")
        attr_cols = st.columns(3)
        with attr_cols[0]:
            gb_operator = st.selectbox("Giá Biểu (GB)", ["Tất cả", "=", ">", "<", ">=", "<="], key="gb_op")
            gb_value = st.text_input("Giá trị GB", placeholder="Nhập giá trị...", key="gb_val",
                                     label_visibility="collapsed")
        with attr_cols[1]:
            ttm_operator = st.selectbox("Tiêu Thụ Mới (TTM)", ["Tất cả", "=", ">", "<", ">=", "<="], key="ttm_op")
            ttm_value = st.number_input("Giá trị TTM", value=None, placeholder="Nhập số...", key="ttm_val",
                                        label_visibility="collapsed")
        with attr_cols[2]:
            ttl_operator = st.selectbox("Tiêu Thụ Lệch (TTL)", ["Tất cả", "=", ">", "<", ">=", "<="], key="ttl_op")
            ttl_value = st.number_input("Giá trị TTL", value=None, placeholder="Nhập số...", key="ttl_val",
                                        label_visibility="collapsed")

        cat_cols = st.columns(5)
        with cat_cols[0]: cocu_filter = st.selectbox("Cỡ Cũ", ["Tất cả"] + filter_data.get('CoCu', []))
        with cat_cols[1]: dot_filter = st.selectbox("Đợt", ["Tất cả"] + filter_data.get('Dot', []))
        with cat_cols[2]: hieucu_filter = st.selectbox("Hiệu Cũ", ["Tất cả"] + filter_data.get('HieuCu', []))
        with cat_cols[3]: codemoi_filter = st.selectbox("Code Mới", ["Tất cả"] + filter_data.get('CodeMoi', []))
        with cat_cols[4]: hopbaove_filter = st.selectbox("Hộp Bảo Vệ", ["Tất cả"] + filter_data.get('HopBaoVe', []))

        st.markdown("---")
        limit_rows = st.number_input("Giới hạn số dòng (nhập 0 để tải tất cả)", 0, 10000, 200, 100)
        run_button = st.button("Tải Dữ Liệu", type="primary", use_container_width=True)

    if run_button:
        st.session_state.ghi_active_filters = {
            "ky_from": ky_from, "nam_from": nam_from, "ky_to": ky_to, "nam_to": nam_to,
            "gb_op": gb_operator, "gb_val": gb_value, "ttm_op": ttm_operator, "ttm_val": ttm_value,
            "ttl_op": ttl_operator, "ttl_val": ttl_value, "cocu": cocu_filter, "dot": dot_filter,
            "hieucu": hieucu_filter, "codemoi": codemoi_filter, "hopbaove": hopbaove_filter,
            "limit": limit_rows
        }
        if 'ghi_chi_tiet_df' in st.session_state: del st.session_state.ghi_chi_tiet_df
        if 'ghi_chart_df' in st.session_state: del st.session_state.ghi_chart_df

    if 'ghi_active_filters' in st.session_state:
        if 'ghi_chi_tiet_df' not in st.session_state:
            with st.spinner("Đang tải dữ liệu chi tiết..."):
                st.session_state.ghi_chi_tiet_df = get_ghi_chi_tiet_data(st.session_state.ghi_active_filters)

        df = st.session_state.ghi_chi_tiet_df
        st.success(f"Tìm thấy {len(df)} dòng dữ liệu.")

        df_display = df.copy()
        if 'HopBaoVe' in df_display.columns:
            df_display['HopBaoVe'] = df_display['HopBaoVe'].apply(
                lambda x: '✔' if x == 1.0 else ('✘' if x == 0.0 else '')
            )

        def highlight_filtered_columns(row):
            highlight_style = 'background-color: #38424a;'
            default_style = ''
            styles = [default_style] * len(row)
            active_filters = st.session_state.get('ghi_active_filters', {})

            filter_to_column_map = {
                'gb_op': 'GB', 'ttm_op': 'TieuThuMoi', 'ttl_op': ['TieuThuMoi', 'TieuThuCu'],
                'cocu': 'CoCu', 'dot': 'Dot', 'hieucu': 'HieuCu', 'codemoi': 'CodeMoi', 'hopbaove': 'HopBaoVe'
            }

            for filter_key, column_name_or_list in filter_to_column_map.items():
                is_active = (active_filters.get(filter_key) and active_filters.get(filter_key) != "Tất cả")
                if filter_key in ['gb_op', 'ttm_op', 'ttl_op']:
                    is_active = is_active and (active_filters.get(
                        filter_key.replace('_op', '_val')) is not None and active_filters.get(
                        filter_key.replace('_op', '_val')) != '')

                if is_active:
                    if isinstance(column_name_or_list, list):
                        for col_name in column_name_or_list:
                            if col_name in row.index: styles[row.index.get_loc(col_name)] = highlight_style
                    else:
                        if column_name_or_list in row.index: styles[
                            row.index.get_loc(column_name_or_list)] = highlight_style
            return styles

        STYLING_CELL_LIMIT = 262144
        if df_display.size > STYLING_CELL_LIMIT:
            st.warning(
                f"⚠️ Dữ liệu quá lớn ({len(df_display):,} dòng) để tô màu. Bảng được hiển thị không có định dạng màu để đảm bảo hiệu suất.")
            st.dataframe(df_display, use_container_width=True, height=400)
        else:
            styled_df = df_display.style.apply(highlight_filtered_columns, axis=1).format("{:,.0f}", subset=["TongTien",
                                                                                                             "TieuThuMoi",
                                                                                                             "TieuThuCu"],
                                                                                          na_rep='')
            st.dataframe(styled_df, use_container_width=True, height=400)

        st.divider()
        st.header("Biểu đồ Phân tích")
        chart_col1, chart_col2, chart_col3, _ = st.columns([1, 1, 1, 2])
        chart_filters = {"GB": chart_col1, "CoCu": chart_col2, "HieuCu": chart_col3}

        for col, button_col in chart_filters.items():
            if button_col.button(f"BĐ theo {col}"):
                with st.spinner("Đang tổng hợp dữ liệu..."):
                    st.session_state.ghi_chart_df = get_ghi_chart_data(st.session_state.ghi_active_filters, col)
                    st.session_state.chart_title = col

        if 'ghi_chart_df' in st.session_state:
            fig = create_analysis_chart(st.session_state.ghi_chart_df, st.session_state.chart_title)
            if fig: st.pyplot(fig)
    else:
        st.info("Sử dụng bộ lọc ở trên và nhấn 'Tải Dữ Liệu' để xem chi tiết.")