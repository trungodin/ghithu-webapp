# File: pages/7_✍️_GHI.py

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import streamlit as st  # <<< THÊM DÒNG NÀY VÀO

# Thêm đường dẫn của thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.analysis_logic import get_ghi_bo_loc_data, get_ghi_chi_tiet_data

# --- Cấu hình trang ---
st.set_page_config(page_title="Ghi Dữ Liệu Đọc Số", layout="wide")
st.title("✍️ Ghi và Phân tích Dữ liệu Đọc Số")

# Tải dữ liệu cho các bộ lọc (chỉ chạy 1 lần nhờ cache)
filter_data = get_ghi_bo_loc_data()

# --- Giao diện Sidebar chứa các bộ lọc ---
with st.sidebar:
    st.header("Bộ lọc Dữ liệu")

    # Lấy kỳ/năm mặc định là tháng/năm hiện tại
    current_year = datetime.now().year
    current_month = datetime.now().month

    ky_from = st.number_input("Kỳ", min_value=1, max_value=12, value=current_month)
    nam_from = st.number_input("Năm", min_value=2020, max_value=2099, value=current_year)

    st.markdown("---")

    # Các bộ lọc ComboBox
    cocu_filter = st.selectbox("Cỡ Cũ", ["Tất cả"] + filter_data.get('CoCu', []))
    dot_filter = st.selectbox("Đợt", ["Tất cả"] + filter_data.get('Dot', []))
    hieucu_filter = st.selectbox("Hiệu Cũ", ["Tất cả"] + filter_data.get('HieuCu', []))
    codemoi_filter = st.selectbox("Code Mới", ["Tất cả"] + filter_data.get('CodeMoi', []))
    hopbaove_filter = st.selectbox("Hộp Bảo Vệ", ["Tất cả"] + filter_data.get('HopBaoVe', []))

    run_button = st.button("Tải Dữ Liệu Chi Tiết", type="primary")

# --- Tạo các tab con ---
tab_chi_tiet, tab_nam_ky, tab_to_may = st.tabs([
    "Dữ Liệu Chi Tiết",
    "Phân Tích Năm & Kỳ",
    "Phân Tích Theo Tổ Máy"
])

# --- Xử lý logic và hiển thị cho Tab 1 ---
with tab_chi_tiet:
    st.header("Dữ liệu Đọc số Chi tiết")

    if run_button:
        # Tập hợp các lựa chọn của người dùng
        filters = {
            "ky_from": ky_from,
            "nam_from": nam_from,
            "cocu": cocu_filter if cocu_filter != "Tất cả" else None,
            "dot": dot_filter if dot_filter != "Tất cả" else None,
            "hieucu": hieucu_filter if hieucu_filter != "Tất cả" else None,
            "codemoi": codemoi_filter if codemoi_filter != "Tất cả" else None,
            "hopbaove": hopbaove_filter if hopbaove_filter != "Tất cả" else None,
        }

        # Gọi hàm backend để lấy dữ liệu
        with st.spinner("Đang tải dữ liệu chi tiết..."):
            # Tạm thời hàm backend chưa dùng hết các bộ lọc, sẽ cập nhật sau
            # Chúng ta lưu kết quả vào session_state để giữ lại dữ liệu
            st.session_state.ghi_chi_tiet_df = get_ghi_chi_tiet_data(filters)

    # Hiển thị bảng dữ liệu nếu nó tồn tại trong session state
    if 'ghi_chi_tiet_df' in st.session_state:
        df = st.session_state.ghi_chi_tiet_df
        st.success(f"Tìm thấy {len(df)} dòng dữ liệu.")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nhấn nút 'Tải Dữ Liệu Chi Tiết' ở thanh bên để bắt đầu.")

with tab_nam_ky:
    st.header("Phân Tích Sản Lượng Theo Năm & Kỳ")
    st.info("Chức năng này sẽ được tích hợp ở bước tiếp theo.")

with tab_to_may:
    st.header("Phân Tích Theo Tổ Máy")
    st.info("Chức năng này sẽ được tích hợp ở bước tiếp theo.")