import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm logic chúng ta đã thêm vào
from backend.analysis_logic import get_main_data, get_analysis_data

# --- Cấu hình trang ---
st.set_page_config(page_title="Phân tích Thu Hộ", page_icon="💳", layout="wide")
st.title("💳 Dashboard Phân Tích Thu Hộ")


# --- Các hàm tiện ích ---

@st.cache_data(ttl=3600)  # Cache trong 1 giờ
def cached_get_main_data(from_date, to_date):
    """Lấy và cache dữ liệu cho bảng chính."""
    return get_main_data(from_date, to_date)


@st.cache_data(ttl=3600)
def cached_get_analysis_data():
    """Lấy và cache dữ liệu cho bảng phân tích tồn."""
    return get_analysis_data()


def to_excel(df):
    """Chuyển đổi DataFrame sang file Excel trong bộ nhớ."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='BaoCaoThuHo')
    processed_data = output.getvalue()
    return processed_data


def create_revenue_chart(df):
    """
    Hàm để vẽ biểu đồ doanh thu bằng Matplotlib với các tùy chỉnh.
    """
    # 1. Chuẩn bị dữ liệu
    df_chart = df.copy()
    total_revenue = df_chart['Tổng cộng'].sum()

    # 2. Tạo biểu đồ
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df_chart.index, df_chart['Tổng cộng'], color='#89CFF0')

    # 3. Thêm nhãn phần trăm lên trên mỗi cột
    if total_revenue > 0:
        for bar in bars:
            height = bar.get_height()
            percentage = 100 * height / total_revenue
            ax.annotate(f'{percentage:.2f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, weight='bold')

    # 4. Định dạng trục Y với dấu phẩy hàng ngàn
    formatter = mticker.FuncFormatter(lambda x, p: f'{x:,.0f}')
    ax.yaxis.set_major_formatter(formatter)

    # 5. Tùy chỉnh các chi tiết khác của biểu đồ
    ax.set_title('Biểu Đồ Doanh Thu', fontsize=16, weight='bold', pad=20)
    ax.set_ylabel('Tổng cộng (VND)', fontsize=12)
    plt.xticks(rotation=80, ha='right')
    fig.tight_layout()  # Tự động điều chỉnh để không bị cắt chữ

    return fig


# --- Vùng bộ lọc ---
st.subheader("Tùy chọn xem dữ liệu")
today = datetime.now()
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    from_date = st.date_input("Từ ngày", value=today, key="from_date_thuho")
with col2:
    to_date = st.date_input("Đến ngày", value=today, key="to_date_thuho")

# --- Lấy và xử lý dữ liệu ---
main_df = pd.DataFrame()
analysis_data = {}

# Chuyển ngày sang định dạng chuỗi YYYY-MM-DD cho hàm backend
from_date_str = from_date.strftime('%Y-%m-%d')
to_date_str = to_date.strftime('%Y-%m-%d')

try:
    with st.spinner("Đang tải dữ liệu..."):
        main_df = cached_get_main_data(from_date_str, to_date_str)
        analysis_data = cached_get_analysis_data()
except Exception as e:
    st.error(f"Lỗi khi tải dữ liệu: {e}")

# --- Bố cục hiển thị ---
left_col, right_col = st.columns([3, 2], gap="large")

# Cột bên trái: CHỈ CÒN LẠI Bảng tổng hợp
with left_col:
    st.subheader("Bảng Tổng Hợp Doanh Thu")

    if not main_df.empty:
        # Nút xuất Excel
        excel_data_export = main_df.copy()
        excel_data_export['Tổng cộng'] = pd.to_numeric(excel_data_export['Tổng cộng'], errors='coerce')
        excel_data_export['Tổng hoá đơn'] = pd.to_numeric(excel_data_export['Tổng hoá đơn'], errors='coerce')
        excel_to_download = to_excel(excel_data_export)

        st.download_button(
            label="📥 Xuất Excel",
            data=excel_to_download,
            file_name=f"BaoCaoThuHo_{from_date_str}_den_{to_date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Định dạng lại bảng để hiển thị trên web
        df_display = main_df.copy()
        df_display['Tổng cộng'] = pd.to_numeric(df_display['Tổng cộng'], errors='coerce').fillna(0).apply(
            lambda x: f"{int(x):,}")
        df_display['Tổng hoá đơn'] = pd.to_numeric(df_display['Tổng hoá đơn'], errors='coerce').fillna(0).apply(
            lambda x: f"{int(x):,}")

        table_height = (len(df_display) + 1) * 35 + 3

        st.dataframe(
            df_display,
            column_config={
                "Tổng cộng": st.column_config.TextColumn("Tổng Cộng (VND)"),
                "Tổng hoá đơn": st.column_config.TextColumn("Tổng Hóa Đơn"),
                "Tỷ lệ (%)": st.column_config.NumberColumn("Tỷ lệ", format="%.2f%%"),
            },
            use_container_width=True,
            hide_index=True,
            height=table_height
        )
    else:
        st.warning("Không có dữ liệu cho khoảng thời gian đã chọn.")

# Cột bên phải: Phân tích tồn VÀ Biểu đồ
with right_col:
    st.subheader("Phân Tích Tồn")
    if analysis_data:
        for key, value in analysis_data.items():
            st.metric(label=key, value=f"{int(value):,}")
    else:
        st.info("Không có dữ liệu phân tích tồn.")

    # === TOÀN BỘ CODE BIỂU ĐỒ ĐÃ ĐƯỢC DỜI SANG ĐÂY ===
    st.subheader("Biểu Đồ Doanh Thu")

    if not main_df.empty:
        chart_df = main_df[main_df['Ngân Hàng'] != 'Tổng cộng'].copy()
        chart_df['Tổng cộng'] = pd.to_numeric(chart_df['Tổng cộng'], errors='coerce').fillna(0)
        chart_df = chart_df.sort_values(by='Tổng cộng', ascending=False)
        chart_df = chart_df.set_index('Ngân Hàng')

        fig = create_revenue_chart(chart_df)
        st.pyplot(fig)
    # =======================================================