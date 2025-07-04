# File: pages/2_📁_THU.py

import streamlit as st
import sys
import os

# Thêm đường dẫn đến thư mục sub_pages để Python có thể tìm thấy các module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các trang con dưới dạng module
from sub_pages import bao_cao_tuan
from sub_pages import loc_du_lieu_ton
from sub_pages import phan_tich_doanh_thu
from sub_pages import phan_tich_hoa_don_no
from sub_pages import phan_tich_thu_ho

# --- Giao diện chính ---
st.set_page_config(layout="wide")

# Tạo một dictionary để quản lý các trang
# Tên hiển thị : hàm show() tương ứng
PAGES = {
    "1_🔍_Lọc dữ liệu tồn": loc_du_lieu_ton,
    "2_📊_Báo cáo tuần": bao_cao_tuan,
    "3_📈_Phân tích Doanh thu": phan_tich_doanh_thu,
    "4_🚫_Phân tích Hóa đơn nợ": phan_tich_hoa_don_no,
    "5_💳_Phân tích Thu hộ": phan_tich_thu_ho
}

# Sử dụng expander để tạo mục lớn "THU"
with st.sidebar.expander("💳 THU TIỀN", expanded=True):
    # Dùng radio button để chọn trang con
    selection = st.radio("Chọn chức năng:", list(PAGES.keys()))

# Lấy ra module của trang được chọn
page = PAGES[selection]

# Gọi hàm show() của module đó để hiển thị nội dung trang
page.show()