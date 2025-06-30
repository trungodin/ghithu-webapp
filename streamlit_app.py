import streamlit as st
import config
import logging
from streamlit.errors import StreamlitAPIException  # Import thêm lỗi này

# Thiết lập cơ bản cho logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def check_password():
    """Trả về True nếu người dùng đã đăng nhập, False nếu ngược lại."""

    def password_entered():
        # === SỬA LỖI LOGIC XÁC THỰC TẠI ĐÂY ===
        try:
            # Thử đọc từ st.secrets trước. Nếu file secrets không tồn tại, nó sẽ gây lỗi.
            correct_username = st.secrets["app_credentials"]["username"]
            correct_password = st.secrets["app_credentials"]["password"]
            logging.info("Sử dụng thông tin xác thực từ Streamlit Secrets.")
        except (StreamlitAPIException, KeyError):
            # Nếu có lỗi (tức là đang chạy local), chuyển sang đọc từ file config.
            logging.info("Không tìm thấy secrets, sử dụng thông tin xác thực từ config.py.")
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
st.set_page_config(page_title="Hệ thống Ghi Thu", page_icon="🔑", layout="wide")

if not check_password():
    st.stop()

st.title("Chào mừng đến với Hệ thống Hỗ trợ Ghi Thu! 👋")
st.sidebar.success("Bạn đã đăng nhập thành công.")
st.sidebar.image("https://i.imgur.com/2OfSnJB.png", width=150)

st.info(
    """
    **👈 Vui lòng chọn một chức năng từ thanh điều hướng bên trái để bắt đầu.**

    - **Dashboard**: Xem các chỉ số tổng quan về tình hình nợ tồn.
    - **Báo cáo tuần**: Tạo báo cáo công tác tuần dựa trên dữ liệu giao nhận.
    - **Lọc dữ liệu tồn**: Tìm kiếm, lọc các khách hàng nợ tồn và gửi danh sách đi xử lý.
    """
)