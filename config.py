# -*- coding: utf-8 -*-


# ==============================================================================
# CẤU HÌNH API
# ==============================================================================
API_URL = 'http://14.161.13.194:8065/ws_Banggia.asmx'
API_USER = 'BENTHANH@194'
API_TIMEOUT = 180  # Thời gian chờ (giây)


# ==============================================================================
# CẤU HÌNH GOOGLE SHEETS
# ==============================================================================
SERVICE_ACCOUNT_FILE = 'chung_chi.json'
SHEET_NAME = 'Thông báo - Khoá nước'
DB_SHEET = 'database'
ON_OFF_SHEET = 'ON_OFF'


# ==============================================================================
# CẤU HÌNH TÊN CỘT TRONG GOOGLE SHEETS
# ==============================================================================
# --- Sheet 'database' ---
DB_COL_ID = 'ID'
DB_COL_DANH_BO = 'danh_bo'
DB_COL_NGAY_GIAO = 'ngay_giao_ds'
DB_COL_NHOM = 'nhom'
DB_COL_KY_NAM = 'ky_nam'
DB_COL_TEN_KH = 'ten_kh'
DB_COL_SO_NHA = 'so_nha'
DB_COL_DCTT = 'DCTT'
DB_COL_TEN_DUONG = 'ten_duong'
DB_COL_GB = 'GB'
DB_COL_DOT = 'DOT'
DB_COL_HOP_BV = 'hop_bv'
DB_COL_TONG_KY = 'tong_ky'
DB_COL_TONG_TIEN = 'tong_tien'
DB_COL_TINH_TRANG = 'tinh_trang'

# --- Sheet 'ON_OFF' ---
ON_OFF_COL_ID = 'id_tb'
ON_OFF_COL_DANH_BA = 'danh_ba' # <<< THÊM MỚI: Cột danh bạ trong sheet ON_OFF
ON_OFF_COL_TINH_TRANG = 'tinh_trang' # <<< THÊM MỚI: Cột tình trạng trong sheet ON_OFF
ON_OFF_COL_NGAY_KHOA = 'ngay_khoa'
ON_OFF_COL_NGAY_MO = 'ngay_mo'
ON_OFF_COL_NHOM_KHOA = 'nhom_khoa'


# ==============================================================================
# CẤU HÌNH TÊN CỘT TRONG DATABASE (API)
# ==============================================================================
API_COL_DANHBA = 'DANHBA'
API_COL_SOHOADON = 'SOHOADON'
API_COL_KY = 'KY'
API_COL_NAM = 'NAM'
API_COL_NGAYGIAI = 'NGAYGIAI'
API_COL_TONGCONG = 'TONGCONG' # <<< THÊM MỚI
API_COL_SHDON_BGW = 'SHDon'
API_COL_NGAYTT_BGW = 'NgayThanhToan' # Cột Ngày thanh toán trong BGW_HD


# ==============================================================================
# CẤU HÌNH KHÁC
# ==============================================================================
# Định dạng ngày tháng
DATE_FORMAT_1 = '%d/%m/%Y %H:%M:%S'
DATE_FORMAT_2 = '%d/%m/%Y'

# Danh sách nhân viên theo nhóm
STAFF_MAP = {
    "Sang Sơn": ["Nguyễn Minh Sang", "Đặng Ngọc Sơn"],
    "Thi Náo": ["Lê Quang Thi", "Nguyễn Văn Náo"]
}

# Các nhóm để lựa chọn trong ComboBox
GROUP_OPTIONS = ["Tất cả các nhóm", "Sang Sơn", "Thi Náo"]

# <<< ĐIỀU CHỈNH: Chuyển cột ID ra cuối
# Thứ tự các cột trong sheet 'database' để ghi dữ liệu xuống
DB_SHEET_FINAL_COLUMNS = [
    'STT', 'danh_bo', 'so_nha', 'DCTT', 'ten_duong', 'ten_kh', 'tong_ky',
    'tong_tien', 'ky_nam', 'GB', 'DOT', 'hop_bv', 'so_than', 'nhom', 'ngay_giao_ds', 'ID', 'tra_cuu_no'
]

# <<< THÊM MỚI: Cấu hình đăng nhập ứng dụng
# ==============================================================================
# Thay đổi username và password tại đây
LOGIN_USERNAME = 'trungodin'
LOGIN_PASSWORD = 'Nht@100982@'

# ==============================================================================
# CẤU HÌNH CÁC TÊN CỘT TRONG CSDL (CHO TAB PHÂN TÍCH DOANH THU)
# ==============================================================================
# Dựa trên code PyQt bạn đã cung cấp
SUM_VALUE_COLUMN = 'TONGCONG_BD'
ORIGINAL_SUM_COLUMN = 'TONGCONG'
BILLING_YEAR_COLUMN = 'NAM'
PAYMENT_DATE_COLUMN = 'NGAYGIAI'
PERIOD_COLUMN = 'KY'
INVOICE_ID_COLUMN = 'DANHBA'
SOHOADON_COLUMN = 'SOHOADON'
TABLE_SOURCE = "HoaDon"
