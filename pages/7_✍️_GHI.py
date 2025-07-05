# File: pages/7_✍️_GHI.py

import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ghi_sub_pages import ghi_chi_tiet, phan_tich_nam_ky, phan_tich_to_may

st.set_page_config(layout="wide")

PAGES = {
    "Dữ Liệu Chi Tiết": ghi_chi_tiet,
    "Phân Tích Năm & Kỳ": phan_tich_nam_ky,
    "Phân Tích Theo Tổ Máy": phan_tich_to_may,
}
page_keys = list(PAGES.keys())

# === Quay lại logic dùng default_index ===
default_index = 0
if 'last_ghi_subpage' in st.session_state:
    try:
        default_index = page_keys.index(st.session_state.last_ghi_subpage)
    except ValueError:
        default_index = 0

with st.sidebar.expander("✍️ GHI DỮ LIỆU", expanded=True):
    # Không dùng key nữa, dùng index để đặt giá trị mặc định
    selection = st.radio("Chọn chức năng:", page_keys,
                         label_visibility="collapsed", index=default_index)

page = PAGES[selection]
page.show()