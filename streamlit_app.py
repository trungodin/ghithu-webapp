# GhithuWebApp/streamlit_app.py

import streamlit as st
import config
import logging

# Thiết lập cơ bản cho logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def check_password():
    """Trả về True nếu người dùng đã đăng nhập, False nếu ngược lại."""

    def password_entered():
        # === THAY ĐỔI LOGIC XÁC THỰC ===
        # Ưu tiên đọc từ st.secrets khi triển khai
        if "app_credentials" in st.secrets:
            correct_username = st.secrets["app_credentials"]["username"]
            correct_password = st.secrets["app_credentials"]["password"]
        # Nếu không, dùng file config cho môi trường local
        else:
            correct_username = config.LOGIN_USERNAME
            correct_password = config.LOGIN_PASSWORD

        if (st.session_state["username"] == correct_username and
                st.session_state["password"] == correct_password):
            st.session_state["authenticated"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["authenticated"] = False

    # Phần còn lại của hàm giữ nguyên...
    if st.session_state.get("authenticated", False):
        return True

    with st.form("login_form"):
        st.text_input("Tên đăng nhập", key="username")
        st.text_input("Mật khẩu", type="password", key="password")
        st.form_submit_button("Đăng nhập", on_click=password_entered)

    if "authenticated" in st.session_state and not st.session_state.authenticated:
        st.error("😕 Tên đăng nhập hoặc mật khẩu không chính xác.")

    return False

# --- Giao diện chính của trang ---

st.set_page_config(
    page_title="Hệ thống Ghi Thu",
    page_icon="🔑",
    layout="wide"
)

# Kiểm tra mật khẩu
if not check_password():
    st.stop() # Dừng thực thi toàn bộ phần còn lại nếu chưa đăng nhập

# --- Nếu đã đăng nhập thành công, hiển thị phần bên dưới ---

st.title("Chào mừng đến với Hệ thống Hỗ trợ Ghi Thu! 👋")
st.sidebar.success("Bạn đã đăng nhập thành công.")
st.sidebar.image("https://i.imgur.com/2OfSnJB.png", width=150) # Bạn có thể thay bằng logo của mình

st.info(
    """
    **👈 Vui lòng chọn một chức năng từ thanh điều hướng bên trái để bắt đầu.**

    - **Dashboard**: Xem các chỉ số tổng quan về tình hình nợ tồn.
    - **Báo cáo tuần**: Tạo báo cáo công tác tuần dựa trên dữ liệu giao nhận.
    - **Lọc dữ liệu tồn**: Tìm kiếm, lọc các khách hàng nợ tồn và gửi danh sách đi xử lý.
    """
)