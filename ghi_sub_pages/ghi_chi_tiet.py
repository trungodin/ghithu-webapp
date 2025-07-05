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


def show():
    """Hàm để hiển thị nội dung của trang này."""
    st.set_page_config(page_title="Dữ Liệu Chi Tiết", layout="wide")
    st.header("Dữ liệu Đọc số Chi tiết")

    # Tải dữ liệu cho các bộ lọc
    filter_data = get_ghi_bo_loc_data()

    # --- Khối Bộ lọc được di chuyển từ sidebar vào đây ---
    # Dùng expander để có thể thu gọn/mở rộng
    with st.expander("⚙️ Bộ lọc Dữ liệu", expanded=True):

        # --- Hàng 1: Lọc theo thời gian ---
        st.write("##### Lọc theo Thời gian")
        time_cols = st.columns(4)
        with time_cols[0]:
            ky_from = st.number_input("Từ Kỳ", 1, 12, datetime.now().month, key="ky_from")
        with time_cols[1]:
            nam_from = st.number_input("Từ Năm", 2020, 2099, datetime.now().year, key="nam_from")
        with time_cols[2]:
            ky_to = st.number_input("Đến Kỳ (Tùy chọn)", 1, 12, None, placeholder="Để trống...", key="ky_to")
        with time_cols[3]:
            nam_to = st.number_input("Đến Năm (Tùy chọn)", 2020, 2099, None, placeholder="Để trống...", key="nam_to")

        st.markdown("---")

        # --- Hàng 2: Lọc theo thuộc tính số ---
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

        # --- Hàng 3: Lọc theo danh mục ---
        cat_cols = st.columns(5)
        with cat_cols[0]:
            cocu_filter = st.selectbox("Cỡ Cũ", ["Tất cả"] + filter_data.get('CoCu', []))
        with cat_cols[1]:
            dot_filter = st.selectbox("Đợt", ["Tất cả"] + filter_data.get('Dot', []))
        with cat_cols[2]:
            hieucu_filter = st.selectbox("Hiệu Cũ", ["Tất cả"] + filter_data.get('HieuCu', []))
        with cat_cols[3]:
            codemoi_filter = st.selectbox("Code Mới", ["Tất cả"] + filter_data.get('CodeMoi', []))
        with cat_cols[4]:
            hopbaove_filter = st.selectbox("Hộp Bảo Vệ", ["Tất cả"] + filter_data.get('HopBaoVe', []))

        st.markdown("---")

        # === THÊM MỚI: Ô NHẬP LIỆU CHO GIỚI HẠN DÒNG ===
        limit_rows = st.number_input("Giới hạn số dòng (nhập 0 để tải tất cả)", min_value=0, value=200, step=100)

        # Nút bấm tải dữ liệu
        run_button = st.button("Tải Dữ Liệu", type="primary", use_container_width=True)

    # --- Lưu các lựa chọn vào session_state khi nhấn nút ---
    if run_button:
        st.session_state.ghi_active_filters = {
            "ky_from": ky_from, "nam_from": nam_from, "ky_to": ky_to, "nam_to": nam_to,
            "gb_op": gb_operator, "gb_val": gb_value,
            "ttm_op": ttm_operator, "ttm_val": ttm_value,
            "ttl_op": ttl_operator, "ttl_val": ttl_value,
            "cocu": cocu_filter, "dot": dot_filter, "hieucu": hieucu_filter,
            "codemoi": codemoi_filter, "hopbaove": hopbaove_filter,
            "limit": limit_rows  # <<< Thêm giá trị giới hạn vào bộ lọc
        }
        if 'ghi_chi_tiet_df' in st.session_state: del st.session_state.ghi_chi_tiet_df
        if 'ghi_chart_df' in st.session_state: del st.session_state.ghi_chart_df

    # --- Hiển thị nội dung chính ---
    if 'ghi_active_filters' not in st.session_state:
        st.info("Sử dụng bộ lọc ở trên và nhấn 'Tải Dữ Liệu' để bắt đầu.")
    else:
        if 'ghi_chi_tiet_df' not in st.session_state:
            with st.spinner("Đang tải dữ liệu chi tiết..."):
                st.session_state.ghi_chi_tiet_df = get_ghi_chi_tiet_data(st.session_state.ghi_active_filters)

        df = st.session_state.ghi_chi_tiet_df
        st.success(f"Tìm thấy {len(df)} dòng dữ liệu.")
        st.dataframe(df, use_container_width=True, height=400)
        st.divider()

        st.header("Biểu đồ Phân tích")
        # (Phần code biểu đồ giữ nguyên)