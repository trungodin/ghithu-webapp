import streamlit as st
import pandas as pd
import sys
import os
import math
import io

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm backend
from backend.analysis_logic import (
    run_outstanding_by_year_analysis,
    run_outstanding_by_period_count_analysis,
    fetch_outstanding_details_by_year,
    fetch_outstanding_customers_by_period_count
)

def show():
    # --- Cấu hình trang ---
    st.set_page_config(page_title="Phân tích Hóa đơn nợ", page_icon="🚫", layout="wide")
    st.title("🚫 Phân tích Hóa đơn Nợ")


    # ... (Hàm to_excel và khởi tạo session_state không đổi) ...
    @st.cache_data
    def to_excel(df: pd.DataFrame) -> bytes:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        return output.getvalue()


    if 'outstanding_details_page' not in st.session_state:
        st.session_state.outstanding_details_page = 1

    # --- Bố cục Tab ---
    tab_by_year, tab_by_period_count = st.tabs(["Thống kê theo Năm", "Thống kê theo Số Kỳ Nợ"])

    with tab_by_year:
        # ... (Nội dung của tab này giữ nguyên không đổi) ...
        st.header("Thống kê Hóa đơn còn nợ theo Năm Hóa đơn")
        if st.button("Tải Thống kê theo Năm"):
            with st.spinner("Đang tải dữ liệu..."):
                try:
                    st.session_state.outstanding_by_year_df = run_outstanding_by_year_analysis()
                    st.session_state.outstanding_details_page = 1
                    if 'outstanding_detail_data' in st.session_state: del st.session_state.outstanding_detail_data
                except Exception as e:
                    st.error("Lỗi khi tải dữ liệu HĐ nợ theo năm."); st.exception(e)

        df_by_year = st.session_state.get('outstanding_by_year_df')
        if df_by_year is not None and not df_by_year.empty:
            total_row_year = pd.DataFrame([{'NamHoaDon': 'Tổng cộng',
                                            'SoLuongHoaDonNo': df_by_year['SoLuongHoaDonNo'].sum(),
                                            'TongCongNo': df_by_year['TongCongNo'].sum()}])
            df_by_year_with_total = pd.concat([df_by_year.astype({'NamHoaDon': object}), total_row_year], ignore_index=True)
            st.dataframe(df_by_year_with_total.rename(columns={'NamHoaDon': 'Năm HĐ', 'SoLuongHoaDonNo': 'Số Lượng HĐ Nợ',
                                                               'TongCongNo': 'Tổng Cộng Nợ'}).style.format(
                {'Số Lượng HĐ Nợ': '{:,}', 'Tổng Cộng Nợ': '{:,.0f}'}), use_container_width=True)
            st.divider()
            st.subheader("Xem chi tiết HĐ nợ của một năm")
            col1, col2 = st.columns([1, 2]);
            with col1:
                years = df_by_year['NamHoaDon'].unique().tolist();
                selected_year = st.selectbox("Chọn năm:", options=years)
            with col2:
                page_size = st.number_input("Số dòng mỗi trang:", min_value=50, max_value=5000, value=100, step=50)
            if st.button("Xem chi tiết năm"):
                st.session_state.outstanding_details_page = 1
                with st.spinner(f"Đang tải chi tiết HĐ nợ năm {selected_year}..."):
                    try:
                        detail_df, total_rows = fetch_outstanding_details_by_year(selected_year, page_number=1,
                                                                                  page_size=page_size)
                        st.session_state.outstanding_detail_data = {'df': detail_df, 'total_rows': total_rows,
                                                                    'page_size': page_size, 'selected_year': selected_year}
                    except Exception as e:
                        st.error(f"Lỗi khi tải chi tiết năm {selected_year}."); st.exception(e)

        detail_data = st.session_state.get('outstanding_detail_data')
        if detail_data:
            df_detail = detail_data['df'];
            total_rows = detail_data['total_rows'];
            page_size = detail_data['page_size']
            current_page = st.session_state.outstanding_details_page;
            selected_year_title = detail_data['selected_year']
            total_pages = math.ceil(total_rows / page_size) if page_size > 0 else 1
            st.markdown(f"#### Chi tiết hóa đơn nợ cho năm {selected_year_title} (Tổng cộng: {total_rows:,} HĐ)")
            if not df_detail.empty:
                excel_data = to_excel(df_detail)
                st.download_button(label=f"📥 Tải Excel (Trang {current_page})", data=excel_data,
                                   file_name=f"ChiTiet_HD_No_{selected_year_title}_Trang_{current_page}.xlsx")
            st.dataframe(df_detail.rename(
                columns={'DanhBa': 'Danh Bạ', 'TENKH': 'Tên KH', 'SoNha': 'Số Nhà', 'Duong': 'Đường', 'NamHD': 'Năm HĐ',
                         'Ky': 'Kỳ', 'GiaBieu': 'Giá Biểu', 'TongCong': 'Tổng Cộng'}).style.format(
                {'Tổng Cộng': '{:,.0f}'}), use_container_width=True)
            st.write("");
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            if p_col1.button("Trang trước",
                             disabled=(current_page <= 1)): st.session_state.outstanding_details_page -= 1; st.rerun()
            p_col2.markdown(f"<div style='text-align: center;'>Trang **{current_page}** / **{total_pages}**</div>",
                            unsafe_allow_html=True)
            if p_col3.button("Trang sau", disabled=(
                    current_page >= total_pages)): st.session_state.outstanding_details_page += 1; st.rerun()
            if 'last_loaded_page' not in st.session_state or st.session_state.last_loaded_page != current_page:
                with st.spinner(f"Đang tải trang {current_page}..."):
                    new_page_df, _ = fetch_outstanding_details_by_year(selected_year_title, page_number=current_page,
                                                                       page_size=page_size)
                    st.session_state.outstanding_detail_data['df'] = new_page_df;
                    st.session_state.last_loaded_page = current_page
                    st.rerun()

    with tab_by_period_count:
        st.header("Thống kê Danh bạ nợ theo Số lượng kỳ")
        if st.button("Tải Thống kê theo Số Kỳ Nợ"):
            with st.spinner("Đang tải dữ liệu..."):
                try:
                    st.session_state.outstanding_by_period_df = run_outstanding_by_period_count_analysis()
                    if 'outstanding_customer_df' in st.session_state: del st.session_state.outstanding_customer_df
                except Exception as e:
                    st.error("Lỗi khi tải dữ liệu HĐ nợ theo số kỳ."); st.exception(e)

        df_by_period = st.session_state.get('outstanding_by_period_df')
        if df_by_period is not None and not df_by_period.empty:
            total_row_period = pd.DataFrame([{'KyNo': 'Tổng cộng', 'SoLuongDanhBa': df_by_period['SoLuongDanhBa'].sum(),
                                              'TongCongTheoKyNo': df_by_period['TongCongTheoKyNo'].sum()}])
            df_by_period_with_total = pd.concat([df_by_period.astype({'KyNo': object}), total_row_period],
                                                ignore_index=True)
            st.dataframe(df_by_period_with_total.rename(columns={'KyNo': 'Số Kỳ Nợ', 'SoLuongDanhBa': 'Số Lượng DB',
                                                                 'TongCongTheoKyNo': 'Tổng Nợ Tương Ứng'}).style.format(
                {'Số Lượng DB': '{:,}', 'Tổng Nợ Tương Ứng': '{:,.0f}'}), use_container_width=True)
            st.divider()

            st.subheader("Xem chi tiết Danh bạ theo số kỳ nợ")

            # === THAY ĐỔI BỘ LỌC TẠI ĐÂY ===
            with st.container(border=True):
                col1_filter, col2_filter, col3_filter = st.columns([1, 1, 3])

                with col1_filter:
                    operator = st.selectbox("Điều kiện:", options=['=', '>', '>=', '<', '<='])
                with col2_filter:
                    ky_no_value = st.number_input("Nhập số kỳ nợ:", min_value=1, value=3, step=1)
                with col3_filter:
                    st.write("")  # Thêm khoảng trống để nút thẳng hàng
                    st.write("")
                    if st.button("Xem chi tiết danh bạ"):
                        with st.spinner(f"Đang tải chi tiết các DB nợ có số kỳ {operator} {ky_no_value}..."):
                            try:
                                # Gọi hàm backend đã được cập nhật
                                customer_detail_df = fetch_outstanding_customers_by_period_count(operator, ky_no_value)
                                st.session_state.outstanding_customer_df = customer_detail_df
                                st.session_state.selected_ky_no_for_detail = f"{operator} {ky_no_value}"  # Cập nhật tiêu đề
                            except Exception as e:
                                st.error(f"Lỗi khi tải chi tiết cho điều kiện: {operator} {ky_no_value}.");
                                st.exception(e)

        # Hiển thị bảng chi tiết danh bạ nếu có
        df_customer_detail = st.session_state.get('outstanding_customer_df')
        if df_customer_detail is not None:
            ky_for_title = st.session_state.get('selected_ky_no_for_detail')
            st.markdown(f"#### Tóm tắt theo Đợt cho các Danh bạ nợ có số kỳ {ky_for_title}")
            if not df_customer_detail.empty:
                # ... (Code tóm tắt theo đợt và hiển thị chi tiết không đổi) ...
                summary_by_dot = df_customer_detail.groupby('DOT').agg(SoLuong=('DanhBa', 'count'), TongCong=(
                'TongCongNoCuaDanhBa', 'sum')).reset_index().rename(
                    columns={'DOT': 'Đợt', 'SoLuong': 'Số lượng DB', 'TongCong': 'Tổng cộng'})
                summary_by_dot['DOT_numeric'] = pd.to_numeric(summary_by_dot['Đợt'], errors='coerce');
                summary_by_dot = summary_by_dot.sort_values(by='DOT_numeric').drop(columns=['DOT_numeric'])
                total_row_dot = pd.DataFrame([{'Đợt': 'Tổng cộng', 'Số lượng DB': summary_by_dot['Số lượng DB'].sum(),
                                               'Tổng cộng': summary_by_dot['Tổng cộng'].sum()}])
                summary_by_dot_with_total = pd.concat([summary_by_dot, total_row_dot], ignore_index=True)
                excel_data_dot = to_excel(summary_by_dot_with_total);
                st.download_button(label="📥 Tải Excel (Tóm tắt Đợt)", data=excel_data_dot,
                                   file_name=f"TomTat_TheoDot_No_{ky_for_title}_ky.xlsx")
                st.dataframe(summary_by_dot_with_total.style.format({'Số lượng DB': '{:,}', 'Tổng cộng': '{:,.0f}'}),
                             use_container_width=True)
                st.divider()

                st.markdown(f"#### Danh sách chi tiết các danh bạ nợ có số kỳ {ky_for_title}")
                excel_data_detail = to_excel(df_customer_detail);
                st.download_button(label="📥 Tải Excel (DS Danh bạ)", data=excel_data_detail,
                                   file_name=f"ChiTiet_DB_No_{ky_for_title}_ky.xlsx")
                st.dataframe(df_customer_detail.rename(
                    columns={'DanhBa': 'Danh Bạ', 'TenKH': 'Tên Khách Hàng', 'SoNha': 'Số Nhà', 'Duong': 'Đường',
                             'SoKyNoThucTe': 'Số Kỳ Nợ', 'TongCongNoCuaDanhBa': 'Tổng Nợ', 'DOT': 'Đợt',
                             'GB': 'Giá Biểu'}).style.format({'Tổng Nợ': '{:,.0f}'}), use_container_width=True)
            else:
                st.warning("Không có danh bạ nào thỏa mãn điều kiện.")