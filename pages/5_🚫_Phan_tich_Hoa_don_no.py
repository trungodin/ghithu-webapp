import streamlit as st
import pandas as pd
import sys
import os
import math

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm backend
from backend.analysis_logic import (
    run_outstanding_by_year_analysis,
    run_outstanding_by_period_count_analysis,
    fetch_outstanding_details_by_year,
    fetch_outstanding_customers_by_period_count
)

# --- Cấu hình trang ---
st.set_page_config(page_title="Phân tích Hóa đơn nợ", page_icon="🚫", layout="wide")
st.title("🚫 Phân tích Hóa đơn Nợ")

# --- Khởi tạo session state ---
if 'outstanding_details_page' not in st.session_state:
    st.session_state.outstanding_details_page = 1

# --- Bố cục Tab ---
tab_by_year, tab_by_period_count = st.tabs(["Thống kê theo Năm", "Thống kê theo Số Kỳ Nợ"])

# --- Tab 1: Thống kê theo Năm (Đã hoàn thiện) ---
with tab_by_year:
    st.header("Thống kê Hóa đơn còn nợ theo Năm Hóa đơn")
    if st.button("Tải Thống kê theo Năm"):
        with st.spinner("Đang tải dữ liệu..."):
            try:
                st.session_state.outstanding_by_year_df = run_outstanding_by_year_analysis()
                st.session_state.outstanding_details_page = 1
                if 'outstanding_detail_data' in st.session_state:
                    del st.session_state.outstanding_detail_data
            except Exception as e:
                st.error("Lỗi khi tải dữ liệu HĐ nợ theo năm.")
                st.exception(e)

    df_by_year = st.session_state.get('outstanding_by_year_df')
    if df_by_year is not None and not df_by_year.empty:
        st.dataframe(df_by_year.rename(columns={'NamHoaDon': 'Năm HĐ', 'SoLuongHoaDonNo': 'Số Lượng HĐ Nợ',
                                                'TongCongNo': 'Tổng Cộng Nợ'}).style.format(
            {'Số Lượng HĐ Nợ': '{:,}', 'Tổng Cộng Nợ': '{:,.0f}'}), use_container_width=True)
        st.divider()

        st.subheader("Xem chi tiết HĐ nợ của một năm")
        col1, col2 = st.columns([1, 2])
        with col1:
            years = df_by_year['NamHoaDon'].unique().tolist()
            selected_year = st.selectbox("Chọn năm:", options=years, key="year_select_for_detail")
        with col2:
            page_size = st.number_input("Số dòng mỗi trang:", min_value=50, max_value=500, value=100, step=50,
                                        key="page_size_for_year")

        if st.button("Xem chi tiết năm"):
            st.session_state.outstanding_details_page = 1
            with st.spinner(f"Đang tải chi tiết HĐ nợ năm {selected_year}..."):
                try:
                    detail_df, total_rows = fetch_outstanding_details_by_year(selected_year, page_number=1,
                                                                              page_size=page_size)
                    st.session_state.outstanding_detail_data = {'df': detail_df, 'total_rows': total_rows,
                                                                'page_size': page_size, 'selected_year': selected_year}
                except Exception as e:
                    st.error(f"Lỗi khi tải chi tiết năm {selected_year}.");
                    st.exception(e)

    detail_data = st.session_state.get('outstanding_detail_data')
    if detail_data:
        df_detail = detail_data['df']
        total_rows = detail_data['total_rows']
        page_size = detail_data['page_size']
        current_page = st.session_state.outstanding_details_page
        selected_year_title = detail_data['selected_year']
        total_pages = math.ceil(total_rows / page_size) if page_size > 0 else 1

        st.markdown(f"#### Chi tiết hóa đơn nợ cho năm {selected_year_title} (Tổng cộng: {total_rows:,} HĐ)")
        st.dataframe(df_detail.rename(
            columns={'DanhBa': 'Danh Bạ', 'TENKH': 'Tên KH', 'SoNha': 'Số Nhà', 'Duong': 'Đường', 'NamHD': 'Năm HĐ',
                     'Ky': 'Kỳ', 'GiaBieu': 'Giá Biểu', 'TongCong': 'Tổng Cộng'}).style.format(
            {'Tổng Cộng': '{:,.0f}'}), use_container_width=True)

        st.write("")
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        if p_col1.button("Trang trước", disabled=(current_page <= 1)):
            st.session_state.outstanding_details_page -= 1
            st.rerun()
        p_col2.markdown(f"<div style='text-align: center;'>Trang **{current_page}** / **{total_pages}**</div>",
                        unsafe_allow_html=True)
        if p_col3.button("Trang sau", disabled=(current_page >= total_pages)):
            st.session_state.outstanding_details_page += 1
            st.rerun()

        if 'last_loaded_page' not in st.session_state or st.session_state.last_loaded_page != current_page:
            with st.spinner(f"Đang tải trang {current_page}..."):
                new_page_df, _ = fetch_outstanding_details_by_year(selected_year_title, page_number=current_page,
                                                                   page_size=page_size)
                st.session_state.outstanding_detail_data['df'] = new_page_df
                st.session_state.last_loaded_page = current_page
                st.rerun()

# --- Tab 2: Thống kê theo Số Kỳ Nợ (Đã được thêm code đầy đủ) ---
with tab_by_period_count:
    st.header("Thống kê Danh bạ nợ theo Số lượng kỳ")
    if st.button("Tải Thống kê theo Số Kỳ Nợ"):
        with st.spinner("Đang tải dữ liệu..."):
            try:
                st.session_state.outstanding_by_period_df = run_outstanding_by_period_count_analysis()
                if 'outstanding_customer_df' in st.session_state:
                    del st.session_state.outstanding_customer_df
            except Exception as e:
                st.error("Lỗi khi tải dữ liệu HĐ nợ theo số kỳ.")
                st.exception(e)

    df_by_period = st.session_state.get('outstanding_by_period_df')
    if df_by_period is not None:
        if df_by_period.empty:
            st.warning("Không có dữ liệu hóa đơn nợ.")
        else:
            st.dataframe(df_by_period.rename(columns={'KyNo': 'Số Kỳ Nợ', 'SoLuongDanhBa': 'Số Lượng DB',
                                                      'TongCongTheoKyNo': 'Tổng Nợ Tương Ứng'}).style.format(
                {'Số Lượng DB': '{:,}', 'Tổng Nợ Tương Ứng': '{:,.0f}'}), use_container_width=True)
            st.divider()

            st.subheader("Xem chi tiết Danh bạ theo số kỳ nợ")
            ky_no_options = df_by_period['KyNo'].unique().tolist()
            selected_ky_no = st.selectbox("Chọn số kỳ nợ:", options=ky_no_options)
            if st.button("Xem chi tiết danh bạ"):
                with st.spinner(f"Đang tải chi tiết các DB nợ {selected_ky_no} kỳ..."):
                    try:
                        customer_detail_df = fetch_outstanding_customers_by_period_count(selected_ky_no)
                        st.session_state.outstanding_customer_df = customer_detail_df
                        st.session_state.selected_ky_no_for_detail = selected_ky_no
                    except Exception as e:
                        st.error(f"Lỗi khi tải chi tiết cho {selected_ky_no} kỳ nợ.")
                        st.exception(e)

    if st.session_state.get('outstanding_customer_df') is not None:
        ky_for_title = st.session_state.get('selected_ky_no_for_detail')
        st.markdown(f"#### Chi tiết các danh bạ nợ {ky_for_title} kỳ")
        st.dataframe(st.session_state.outstanding_customer_df.rename(
            columns={'DanhBa': 'Danh Bạ', 'TenKH': 'Tên Khách Hàng', 'SoNha': 'Số Nhà', 'Duong': 'Đường',
                     'SoKyNoThucTe': 'Số Kỳ Nợ', 'TongCongNoCuaDanhBa': 'Tổng Nợ', 'DOT': 'Đợt',
                     'GB': 'Giá Biểu'}).style.format({'Tổng Nợ': '{:,.0f}'}), use_container_width=True)