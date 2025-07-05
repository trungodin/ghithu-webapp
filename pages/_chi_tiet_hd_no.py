# File: pages/_chi_tiet_hd_no.py

import streamlit as st
import pandas as pd
import sys
import os
import io
import matplotlib.pyplot as plt

# Thêm đường dẫn của thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# --- Các hàm tiện ích (sao chép từ trang phan_tich_to_may) ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
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


# --- Giao diện chính của trang ---
st.set_page_config(layout="wide")

# Kiểm tra xem có dữ liệu chi tiết trong session state không
if 'ghi_outstanding_invoices_df' not in st.session_state:
    st.error("Không có dữ liệu để hiển thị. Vui lòng quay lại trang 'GHI' và chọn một nhân viên.")
    if st.button("⬅️ Quay lại"):
        st.switch_page("pages/7_✍️_GHI.py")  # Điều hướng về trang THU
else:
    df_invoices = st.session_state.ghi_outstanding_invoices_df
    machine_info = st.session_state.selected_machine_info

    st.title(f"Chi tiết Hóa đơn còn nợ - Máy {machine_info['id']}")

    if st.button("⬅️ Quay lại trang Phân tích"):
        st.switch_page("pages/7_✍️_GHI.py")  # Thay đổi tùy theo tên file của bạn

    if df_invoices.empty:
        st.warning("Không tìm thấy hóa đơn nào còn nợ cho nhân viên này trong kỳ đã chọn.")
    else:
        # BỐ CỤC CHO PHẦN TÓM TẮT VÀ BIỂU ĐỒ TRÒN
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

        # BẢNG CHI TIẾT FULL WIDTH
        st.write("###### Danh sách hóa đơn")
        excel_data = to_excel(df_invoices)
        st.download_button(label="📥 Tải Excel (DS Nợ)", data=excel_data,
                           file_name=f"HĐ_No_May_{machine_info['id']}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        df_display_invoices = df_invoices.copy()
        for col in df_display_invoices.columns:
            if 'int' in str(df_display_invoices[col].dtype) or 'float' in str(df_display_invoices[col].dtype):
                df_display_invoices[col] = df_display_invoices[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

        st.dataframe(df_display_invoices, use_container_width=True)