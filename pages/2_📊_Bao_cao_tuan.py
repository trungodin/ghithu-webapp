import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
import sys
import os
from matplotlib.figure import Figure

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm backend
from backend.analysis_logic import run_weekly_report_analysis
from backend.pdf_generator import create_pdf_report, create_detailed_list_pdf
import config

# --- Cấu hình trang ---
st.set_page_config(
    page_title="Báo cáo Công tác Tuần",
    page_icon="📊",
    layout="wide"
)


# --- Hàm tiện ích ---
def style_debt_status(status):
    """
    Trả về một chuỗi CSS để tô màu cho từng trạng thái nợ.
    """
    if status == 'Đã Thanh Toán':
        return 'color: lightgreen; font-weight: bold;'
    elif status == 'Chưa Thanh Toán':
        return 'color: salmon; font-weight: bold;'
    elif status == 'Khóa nước':
        return 'color: orange; font-weight: bold;'
    return ''


@st.cache_data
def to_excel(dfs_dict: dict) -> bytes:
    """Xuất một dict các DataFrame thành file Excel trong bộ nhớ."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def create_pie_chart(pie_data, group_name):
    """Tạo biểu đồ tròn tỷ lệ hoàn thành."""
    fig = Figure(figsize=(3, 2.3), dpi=100)
    if not pie_data or not pie_data.get('sizes'): return fig
    ax = fig.add_subplot(111);
    labels, sizes = pie_data['labels'], pie_data['sizes']
    colors, explode = ['#4CAF50', '#F44336'], (0.05, 0)
    if sum(sizes) > 0:
        ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=False, startangle=90,
               textprops={'fontsize': 9})
        ax.axis('equal');
        ax.set_title(f"Tỷ lệ Hoàn thành: {group_name}", weight='bold', fontsize=11)
    else:
        ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center', fontsize=12);
        ax.axis('off')
    fig.tight_layout(pad=0.1);
    return fig


# --- Giao diện Sidebar để nhập liệu ---
with st.sidebar:
    st.header("📊 Tùy chọn Báo cáo")
    with st.form(key='report_params_form'):
        first_day_of_month = date.today().replace(day=1)
        start_date = st.date_input("Từ ngày", value=first_day_of_month)
        end_date = st.date_input("Đến ngày", value=date.today())
        payment_deadline = st.date_input("Ngày TT cuối cùng", value=end_date + timedelta(days=7))
        selected_group = st.selectbox("Chọn nhóm", options=config.GROUP_OPTIONS, index=0)
        submit_button = st.form_submit_button(label="Chạy Phân Tích")

# --- Xử lý logic khi người dùng nhấn nút ---
if submit_button:
    start_date_str = start_date.strftime("%d/%m/%Y")
    end_date_str = end_date.strftime("%d/%m/%Y")
    payment_deadline_str = payment_deadline.strftime("%d/%m/%Y")
    with st.spinner(f"Đang phân tích dữ liệu cho nhóm '{selected_group}'... Vui lòng chờ."):
        try:
            # Chạy hàm phân tích từ backend
            report_results = run_weekly_report_analysis(start_date_str, end_date_str, selected_group,
                                                        payment_deadline_str)
            st.session_state['weekly_report_results'] = report_results
            if "error" in report_results:
                st.error(report_results["error"])
        except Exception as e:
            st.session_state['weekly_report_results'] = None
            st.error("Đã có lỗi xảy ra trong quá trình phân tích.");
            st.exception(e)

# --- Hiển thị kết quả ---
st.title("📊 Báo cáo Công tác Tuần")

if 'weekly_report_results' in st.session_state and st.session_state['weekly_report_results']:
    results = st.session_state['weekly_report_results']
    if "error" in results:
        st.error(results["error"])
    else:
        st.subheader(f"Kết quả phân tích từ {results['start_date_str']} đến {results['end_date_str']}")

        # --- LOGIC LỌC VÀ CÁC NÚT BẤM ĐÃ SỬA ---
        details_df_original = results.get('details_df', pd.DataFrame())

        col1, col2, col3, col4, _ = st.columns([2, 1.2, 1.2, 1.5, 3])
        with col1:
            status_filter = st.selectbox("Lọc để xuất file:",
                                         options=["Tất cả Tình trạng", "Chưa Thanh Toán", "Đã Thanh Toán", "Khóa nước"],
                                         key="status_filter")

        # Lọc dữ liệu MỘT LẦN DUY NHẤT để dùng chung
        if status_filter != "Tất cả Tình trạng":
            df_filtered = details_df_original[details_df_original['Tình Trạng Nợ'].str.strip() == status_filter].copy()
        else:
            df_filtered = details_df_original.copy()

        export_dfs = results.get('exportable_dfs', {}).copy()
        export_dfs['Chi_Tiet_Da_Giao'] = df_filtered  # Cập nhật lại sheet chi tiết trong dict xuất excel

        with col2:
            st.download_button(label="📥 Tải Excel", data=to_excel(export_dfs),
                               file_name=f"BaoCaoTuan_{date.today().strftime('%Y%m%d')}.xlsx")
        with col3:
            pdf_data_for_export = {'start_date_str': results['start_date_str'], 'end_date_str': results['end_date_str'],
                                   'selected_group': results['selected_group'],
                                   'tables': {'BẢNG TỔNG HỢP:': export_dfs.get('Tong_Hop_Nhom', pd.DataFrame()),
                                              'BẢNG THỐNG KÊ CHI TIẾT:': export_dfs.get('Thong_Ke_Khoa_Mo',
                                                                                        pd.DataFrame())}}
            success, pdf_bytes = create_pdf_report(pdf_data_for_export)
            if success: st.download_button("📕 Tải PDF BC Tuần", data=pdf_bytes,
                                           file_name=f"BaoCaoCongTacTuan_{date.today().strftime('%Y%m%d')}.pdf")

        with col4:
            if not df_filtered.empty:
                df_for_pdf = df_filtered.copy()
                df_for_pdf.insert(0, 'STT', range(1, len(df_for_pdf) + 1))

                final_pdf_cols = ['STT', 'Danh bạ', 'Tên KH', 'Số nhà', 'Đường', 'Tổng kỳ', 'Tổng tiền', 'Kỳ năm', 'GB',
                                  'Đợt', 'Hộp', 'Ghi chú']
                existing_cols = [col for col in final_pdf_cols if col in df_for_pdf.columns]
                df_report = df_for_pdf[existing_cols]

                df_report_styled = df_report.astype(str)
                if 'Tổng tiền' in df_report_styled.columns:
                    df_report_styled['Tổng tiền'] = pd.to_numeric(df_report['Tổng tiền'], errors='coerce').fillna(
                        0).apply(lambda x: f"{x:,.0f}")

                bold_rows_idx = df_report[df_report['GB'].astype(str) == '31'].index
                for idx in bold_rows_idx:
                    if idx in df_report_styled.index:
                        for col_name in df_report_styled.columns:
                            df_report_styled.loc[idx, col_name] = f"<b>{df_report_styled.loc[idx, col_name]}</b>"

                report_title = f"DANH SÁCH KHÁCH HÀNG {status_filter.upper()}"
                if status_filter == "Tất cả Tình trạng": report_title = "DANH SÁCH KHÁCH HÀNG CHI TIẾT"

                success, pdf_bytes = create_detailed_list_pdf(report_title, df_report_styled)
                if success:
                    st.download_button(label="📄 Tải PDF Chi tiết", data=pdf_bytes,
                                       file_name=f"DSKH_{status_filter.replace(' ', '_')}_{date.today().strftime('%Y%m%d')}.pdf")

        st.divider()

        # --- Hiển thị các bảng và biểu đồ ---
        summary_df = results.get('summary_df', pd.DataFrame())
        if not summary_df.empty:
            st.markdown("### Bảng tổng hợp");
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

        left_col, right_col = st.columns([1, 2])
        with left_col:
            pie_chart_data = results.get('pie_chart_data', {})
            if pie_chart_data:
                st.markdown("### Tỷ lệ hoàn thành")
                for group_name, data in pie_chart_data.items():
                    fig = create_pie_chart(data, group_name);
                    st.pyplot(fig)
        with right_col:
            stats_df = results.get('stats_df', pd.DataFrame())
            if not stats_df.empty:
                st.markdown("### Bảng thống kê chi tiết");
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
        st.divider()

        details_df = results.get('details_df', pd.DataFrame())
        if not details_df.empty:
            st.markdown("### Danh sách chi tiết đã giao")

            df_to_display = details_df.copy()

            # Ép kiểu các cột có thể chứa cả số và chữ thành dạng văn bản
            for col in ['Danh bạ', 'Tên KH', 'Số nhà', 'Đường', 'Kỳ năm', 'GB', 'Đợt', 'Hộp', '']:
                if col in df_to_display.columns:
                    df_to_display[col] = df_to_display[col].astype(str)

            # Áp dụng tô màu và định dạng số
            st.dataframe(
                df_to_display.style.map(
                    style_debt_status,
                    subset=['Tình Trạng Nợ']
                ).format(
                    {'Tổng tiền': '{:,.0f}'}
                ),
                use_container_width=True,
                hide_index=True
            )
else:
    st.info("Vui lòng chọn các tham số trong thanh sidebar bên trái và nhấn 'Chạy Phân Tích' để xem báo cáo.")