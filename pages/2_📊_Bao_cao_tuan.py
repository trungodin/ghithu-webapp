# GhithuWebApp/pages/2_📊_Bao_cao_tuan.py

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
import sys
import os
from matplotlib.figure import Figure

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Bây giờ mới import các module của dự án
from backend.analysis_logic import run_weekly_report_analysis
from backend.pdf_generator import create_pdf_report
import config

# --- Cấu hình trang ---
st.set_page_config(
    page_title="Báo cáo Công tác Tuần",
    page_icon="📊",
    layout="wide"
)


# --- Các hàm Helper ---
def create_pie_chart(pie_data, group_name):
    """Tạo biểu đồ tròn tỷ lệ hoàn thành."""
    # === THAY ĐỔI TẠI ĐÂY: Giảm figsize từ (4, 3.5) xuống (3, 2.3) ===
    fig = Figure(figsize=(2,1.2), dpi=100)
    
    if not pie_data or not pie_data.get('sizes'):
        return fig

    ax = fig.add_subplot(111)
    labels, sizes = pie_data['labels'], pie_data['sizes']
    colors, explode = ['#4CAF50', '#F44336'], (0.05, 0)
    
    if sum(sizes) > 0:
        ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', 
               shadow=False, startangle=90, textprops={'fontsize': 9}) # Giảm cỡ chữ một chút
        ax.axis('equal')
        ax.set_title(f"Tỷ lệ Hoàn thành: {group_name}", weight='bold', fontsize=11) # Giảm cỡ chữ tiêu đề
    else:
        ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center', fontsize=12)
        ax.axis('off')
        
    fig.tight_layout(pad=0.1) # Điều chỉnh khoảng cách
    return fig


def to_excel(dfs_dict: dict) -> bytes:
    """Xuất một dict các DataFrame thành file Excel trong bộ nhớ."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    processed_data = output.getvalue()
    return processed_data


# --- Giao diện Sidebar để nhập liệu ---

with st.sidebar:
    st.header("📊 Tùy chọn Báo cáo")
    # Sử dụng form để nhóm các input
    with st.form(key='report_params_form'):
        # Mặc định ngày bắt đầu là ngày đầu của tháng hiện tại
        first_day_of_month = date.today().replace(day=1)
        start_date = st.date_input("Từ ngày", value=first_day_of_month)
        end_date = st.date_input("Đến ngày", value=date.today())

        # Cập nhật ngày thanh toán cuối cùng dựa trên ngày kết thúc
        payment_deadline = st.date_input(
            "Ngày TT cuối cùng",
            value=end_date + timedelta(days=7)
        )

        selected_group = st.selectbox(
            "Chọn nhóm",
            options=config.GROUP_OPTIONS,
            index=0
        )

        submit_button = st.form_submit_button(label="Chạy Phân Tích")

# --- Xử lý logic khi người dùng nhấn nút ---

if submit_button:
    # Chuyển đổi ngày tháng sang chuỗi đúng định dạng
    start_date_str = start_date.strftime("%d/%m/%Y")
    end_date_str = end_date.strftime("%d/%m/%Y")
    payment_deadline_str = payment_deadline.strftime("%d/%m/%Y")

    # Hiển thị spinner trong khi xử lý
    with st.spinner(f"Đang phân tích dữ liệu cho nhóm '{selected_group}'... Vui lòng chờ."):
        try:
            # Gọi hàm xử lý từ backend
            report_results = run_weekly_report_analysis(
                start_date_str,
                end_date_str,
                selected_group,
                payment_deadline_str
            )
            # Lưu kết quả vào session state để tái sử dụng
            st.session_state['weekly_report_results'] = report_results
            if "error" in report_results:
                st.error(report_results["error"])

        except Exception as e:
            st.session_state['weekly_report_results'] = None
            st.error("Đã có lỗi xảy ra trong quá trình phân tích.")
            st.exception(e)

# --- Hiển thị kết quả ---

st.title("📊 Báo cáo Công tác Tuần")

# Kiểm tra xem có kết quả trong session state không
if 'weekly_report_results' in st.session_state and st.session_state['weekly_report_results']:
    results = st.session_state['weekly_report_results']

    if "error" in results:
        # st.error(results["error"]) # Đã hiển thị lỗi ở trên
        pass
    else:
        # --- Khu vực tiêu đề và xuất file ---
        st.subheader(f"Kết quả phân tích từ {results['start_date_str']} đến {results['end_date_str']}")

        # Thêm bộ lọc và các nút download
        col1, col2, col3, col4 = st.columns([2, 1, 1, 4])
        with col1:
            status_filter = st.selectbox(
                "Lọc để xuất file:",
                options=["Tất cả Tình trạng", "Chưa Thanh Toán", "Đã Thanh Toán", "Khóa nước"],
                key="status_filter"
            )

        # Logic lọc dữ liệu trước khi xuất
        export_dfs = results.get('exportable_dfs', {}).copy()
        if status_filter != "Tất cả Tình trạng":
            details_df = export_dfs.get('Chi_Tiet_Da_Giao')
            if details_df is not None and not details_df.empty:
                filtered_details = details_df[details_df['Tình Trạng Nợ'] == status_filter]
                export_dfs['Chi_Tiet_Da_Giao'] = filtered_details

        with col2:
            st.download_button(
                label="📥 Tải Excel",
                data=to_excel(export_dfs),
                file_name=f"BaoCaoTuan_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )

        with col3:
            # Chuẩn bị dữ liệu cho PDF
            pdf_data_for_export = {
                'start_date_str': results['start_date_str'],
                'end_date_str': results['end_date_str'],
                'selected_group': results['selected_group'],
                'tables': {
                    'BẢNG TỔNG HỢP:': export_dfs.get('Tong_Hop_Nhom', pd.DataFrame()),
                    'BẢNG THỐNG KÊ CHI TIẾT:': export_dfs.get('Thong_Ke_Khoa_Mo', pd.DataFrame())
                }
            }
            success, pdf_bytes = create_pdf_report(pdf_data_for_export)
            if success:
                st.download_button(
                    "📕 Tải PDF",
                    data=pdf_bytes,
                    file_name=f"BaoCaoCongTacTuan_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                )

        st.divider()

        # --- Hiển thị Bảng tổng hợp và Thống kê ---
        summary_df = results.get('summary_df', pd.DataFrame())
        stats_df = results.get('stats_df', pd.DataFrame())

        if not summary_df.empty:
            st.markdown("### Bảng tổng hợp")
            st.dataframe(summary_df, use_container_width=True)

        if not stats_df.empty:
            st.markdown("### Bảng thống kê chi tiết")
            st.dataframe(stats_df, use_container_width=True)

        st.divider()

        # --- Hiển thị Biểu đồ ---
        pie_chart_data = results.get('pie_chart_data', {})
        if pie_chart_data:
            st.markdown("### Tỷ lệ hoàn thành")
            # Tạo các cột để biểu đồ không bị quá lớn
            cols = st.columns(len(pie_chart_data))
            for i, (group_name, data) in enumerate(pie_chart_data.items()):
                with cols[i]:
                    fig = create_pie_chart(data, group_name)
                    st.pyplot(fig)

        # --- Hiển thị Bảng chi tiết ---
        details_df = results.get('details_df', pd.DataFrame())
        if not details_df.empty:
            st.markdown("### Danh sách chi tiết đã giao")
            st.dataframe(details_df, use_container_width=True)
else:
    st.info("Vui lòng chọn các tham số trong thanh sidebar bên trái và nhấn 'Chạy Phân Tích' để xem báo cáo.")
