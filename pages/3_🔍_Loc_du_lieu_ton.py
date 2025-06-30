import streamlit as st
import pandas as pd
from datetime import date, datetime
import time
import sys
import os

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Bây giờ mới import các module của dự án
from backend.analysis_logic import run_debt_filter_analysis, prepare_and_send_to_sheet
import config

# --- Cấu hình trang ---
st.set_page_config(
    page_title="Lọc Dữ liệu Tồn",
    page_icon="🔍",
    layout="wide"
)

# --- Khởi tạo session state ---
if 'debt_filter_results' not in st.session_state:
    st.session_state.debt_filter_results = None
if 'select_all_toggle' not in st.session_state:
    st.session_state.select_all_toggle = False


# --- Hàm callback để xử lý sự kiện "Chọn tất cả"
def toggle_all_rows():
    """Được gọi khi checkbox 'Chọn tất cả' thay đổi trạng thái."""
    if st.session_state.debt_filter_results is not None:
        new_state = st.session_state.get('select_all_toggle', False)
        st.session_state.debt_filter_results['_is_selected'] = new_state

# --- Giao diện ---
st.title("🔍 Lọc Dữ liệu Tồn & Gửi Danh sách")
st.markdown("Sử dụng các bộ lọc dưới đây để truy vấn danh sách khách hàng nợ tồn từ hệ thống.")

# --- Form Nhập liệu cho bộ lọc ---
with st.form("debt_filter_form"):
    st.subheader("Tùy chọn Lọc Dữ liệu")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nam = st.number_input("Năm", value=date.today().year, min_value=2020, max_value=2099, step=1)
        ky = st.number_input("Kỳ", value=date.today().month, min_value=1, max_value=12, step=1)
    with col2:
        min_tongky = st.number_input("Tổng Kỳ >=", value=2, min_value=1, step=1)
        min_tongcong = st.number_input(
            "Tổng Cộng >=",
            value=None,  # Để trống để placeholder có thể hiển thị
            min_value=0,
            step=100000, # Tăng bước nhảy cho các số lớn
            placeholder="Ví dụ: 10000000",
            help="Nhập số tiền không cần dấu phẩy hoặc dấu chấm."
        )
    with col3:
        dot_filter_str = st.text_input("Chỉ lấy Đợt (cách nhau bởi dấu phẩy)", placeholder="VD: 1,2,15,20")
        limit = st.number_input("Giới hạn Top (0 là không giới hạn)", value=100, min_value=0, step=1)
    with col4:
        exclude_codemoi_str = st.text_input("Loại trừ CodeMoi (cách nhau bởi dấu phẩy)", value="K, N, 66, K2")

    submitted = st.form_submit_button("Lọc dữ liệu")

# --- Xử lý logic khi nhấn nút lọc ---
if submitted:
    st.session_state.select_all_toggle = False
    with st.spinner("Đang truy vấn dữ liệu tồn..."):
        try:
            start_time = time.time()
            dot_filter = [int(d.strip()) for d in dot_filter_str.split(',') if d.strip().isdigit()]
            exclude_codemoi = [c.strip().upper() for c in exclude_codemoi_str.split(',') if c.strip()]
            
            # === THÊM LOGIC XỬ LÝ CHO GIÁ TRỊ RỖNG ===
            # Nếu người dùng không nhập gì, coi như giá trị là 0
            min_tongcong_value = min_tongcong if min_tongcong is not None else 0

            params = {
                'nam': nam, 'ky': ky, 'min_tongky': min_tongky, 
                'min_tongcong': min_tongcong_value, # <-- Dùng giá trị đã qua xử lý
                'exclude_codemoi': exclude_codemoi, 'dot_filter': dot_filter, 
                'limit': limit if limit > 0 else None
            }
            
            result_df = run_debt_filter_analysis(params)

            if not result_df.empty:
                result_df.insert(0, "_is_selected", False)
            
            st.session_state.debt_filter_results = result_df
            st.session_state.query_time = time.time() - start_time
            st.toast(f"Tìm thấy {len(result_df)} kết quả!")
        except Exception as e:
            st.error("Lỗi khi lọc dữ liệu.")
            st.exception(e)
            st.session_state.debt_filter_results = None

# --- Hiển thị kết quả và khu vực hành động ---
if st.session_state.debt_filter_results is not None:
    df = st.session_state.debt_filter_results
    
    st.divider()
    
    if df.empty:
        st.warning("Không tìm thấy dữ liệu nào phù hợp với điều kiện lọc của bạn.")
    else:
        # Đảm bảo cột gốc là kiểu số để tính toán
        df['TONGCONG'] = pd.to_numeric(df['TONGCONG'], errors='coerce').fillna(0).astype(int)
        
        # TẠO CỘT MỚI ĐỂ HIỂN THỊ VỚI ĐỊNH DẠNG CHUỖI
        df['Tổng Cộng Formatted'] = df['TONGCONG'].apply(lambda x: f"{x:,.0f} VND")

        st.subheader("Kết quả lọc")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
             st.metric("Số danh bạ tìm thấy", f"{len(df):,}")
        with col2:
             total_sum = int(df['TONGCONG'].sum())
             st.metric("Tổng cộng", {total_sum:,})
        with col3:
             st.metric("Thời gian truy vấn", f"{st.session_state.get('query_time', 0):.2f} giây")

        st.markdown("---")
        
        st.subheader("Gửi Danh sách đi xử lý")
        action_col1, action_col2, action_col3, action_col4 = st.columns([1.5, 1.5, 1.5, 2])
        
        with action_col1:
            assign_group = st.selectbox("Giao cho Nhóm", options=config.GROUP_OPTIONS[1:])
        with action_col2:
            assign_date = st.date_input("Ngày giao")
        with action_col3:
            selected_rows = df[df["_is_selected"]]
            disable_send_button = selected_rows.empty
            if st.button("Gửi DS đã chọn", type="primary", disabled=disable_send_button):
                with st.spinner(f"Đang gửi {len(selected_rows)} khách hàng cho nhóm {assign_group}..."):
                    try:
                        assign_date_str = assign_date.strftime("%d/%m/%Y")
                        # Khi gửi đi, loại bỏ các cột hiển thị thừa
                        df_to_send = selected_rows.drop(columns=["_is_selected", "Tổng Cộng Formatted"])
                        count, msg = prepare_and_send_to_sheet(df_to_send, assign_group, assign_date_str)
                        if count > 0:
                            st.success(msg)
                            st.session_state.debt_filter_results.loc[st.session_state.debt_filter_results["_is_selected"], "_is_selected"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error("Lỗi nghiêm trọng khi gửi dữ liệu.")
                        st.exception(e)
        
        with action_col4:
            st.checkbox(
                "Chọn / Bỏ chọn Tất cả", 
                key='select_all_toggle', 
                on_change=toggle_all_rows,
                help="Tích để chọn tất cả các dòng trong bảng, bỏ tích để hủy chọn."
            )

        st.markdown("Tích vào ô ở cột `_is_selected` để chọn khách hàng cần gửi.")
        
        display_columns_in_order = [
            "_is_selected", "DANHBA", "GB", "Tổng Cộng Formatted", "TONGKY", "KY_NAM", 
            "TENKH", "SO", "DUONG", "MLT2", "SoMoi", "DOT", "CodeMoi", "SoThan"
        ]
        
        final_columns_to_display = [col for col in display_columns_in_order if col in df.columns]

        edited_df = st.data_editor(
            df,
            column_order=final_columns_to_display,
            column_config={
                "_is_selected": st.column_config.CheckboxColumn("Chọn", default=False),
                "Tổng Cộng Formatted": st.column_config.TextColumn("Tổng Cộng"),
                "TONGCONG": None, # Ẩn cột số gốc
            },
            disabled=df.columns.drop("_is_selected"),
            use_container_width=True,
            height=500,
            key="data_editor_final"
        )
        
        if not edited_df.equals(st.session_state.debt_filter_results):
            st.session_state.debt_filter_results = edited_df
            st.rerun()
        if not edited_df.equals(st.session_state.debt_filter_results):
            st.session_state.debt_filter_results = edited_df
            st.rerun()
