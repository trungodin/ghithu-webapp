# GhithuWebApp/backend/data_sources.py

import gspread
import pandas as pd
import requests
import io
import html
import logging
import diskcache
import sys
import os

# Giúp Python tìm thấy file config ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Khởi tạo cache, lưu trong thư mục 'api_cache'
# Dữ liệu trong cache sẽ hết hạn sau 3600 giây (1 giờ)
CACHE = diskcache.Cache('api_cache')

def resource_path(relative_path):
    """ Lấy đường dẫn tuyệt đối đến tài nguyên, hoạt động cho cả môi trường dev và PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(base_path, relative_path)


def _build_soap_request(function_name, sql_query):
    """Xây dựng nội dung của một SOAP request một cách an toàn."""
    soap_body_template = """<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body><{function_name} xmlns="http://tempuri.org/"><m_sql>{sql_command}</m_sql><m_function_name /><m_user>{user}</m_user></{function_name}></s:Body>
    </s:Envelope>"""
    escaped_sql_command = html.escape(sql_query)
    return soap_body_template.format(
        function_name=function_name,
        sql_command=escaped_sql_command,
        user=config.API_USER
    )

def _get_bgw_invoices(sohoadon_list, function_name='f_Select_SQL_Nganhang'):
    """
    Hàm riêng để lấy danh sách hóa đơn đã tồn tại trong BGW theo từng phần (chunk).
    """
    if not sohoadon_list:
        return pd.DataFrame()

    all_bgw_dfs = []
    chunk_size = 500
    for i in range(0, len(sohoadon_list), chunk_size):
        chunk = sohoadon_list[i:i + chunk_size]
        formatted_chunk_list = "', '".join(map(str, chunk))
        sql_bgw_chunk = f"SELECT {config.API_COL_SHDON_BGW} FROM BGW_HD WHERE {config.API_COL_SHDON_BGW} IN ('{formatted_chunk_list}')"
        df_bgw_chunk = fetch_dataframe(function_name, sql_bgw_chunk) # fetch_dataframe đã được cache
        if not df_bgw_chunk.empty:
            all_bgw_dfs.append(df_bgw_chunk)

    if not all_bgw_dfs:
        return pd.DataFrame()

    return pd.concat(all_bgw_dfs, ignore_index=True)

@CACHE.memoize(expire=3600)
def execute_sql_query(function_name, sql_query):
    """Gửi một truy vấn SQL đến SOAP API."""
    logging.info(f"Đang thực thi truy vấn API (function: {function_name})...")
    soap_body = _build_soap_request(function_name, sql_query)
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'"http://tempuri.org/{function_name}"',
        'Host': config.API_URL.split('//')[1].split('/')[0],
    }
    try:
        response = requests.post(
            config.API_URL,
            data=soap_body.encode('utf-8'),
            headers=headers,
            timeout=config.API_TIMEOUT
        )
        response.raise_for_status()
        logging.info("✅ Truy vấn API thành công.")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi kết nối API: {e}", exc_info=True)
        raise ConnectionError(f"Lỗi kết nối API: {e}")


def fetch_dataframe(function_name, sql_query, dtypes=None):
    """Thực thi truy vấn và chuyển kết quả XML thành một DataFrame của Pandas."""
    xml_response = execute_sql_query(function_name, sql_query)
    try:
        # Sử dụng 'lxml' một cách tường minh
        df = pd.read_xml(io.StringIO(xml_response), xpath=".//diffgr:diffgram/NewDataSet/Table1",
                           namespaces={"diffgr": "urn:schemas-microsoft-com:xml-diffgram-v1"}, dtype=dtypes,
                           parse_dates=False, parser='lxml')
        logging.info(f"Phân tích XML thành DataFrame thành công, có {len(df)} dòng.")
        return df
    except (ValueError, KeyError):
        logging.warning(f"Không có dữ liệu trả về từ API cho function '{function_name}'.")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Lỗi khi phân tích XML: {e}", exc_info=True)
        raise ValueError(f"Lỗi khi phân tích XML: {e}")


def fetch_worksheet_as_df(worksheet_name):
    """
    Kết nối đến Google Sheet và đọc dữ liệu từ một worksheet cụ thể theo tên.
    """
    try:
        logging.info(f"Đang đọc dữ liệu từ Google Sheet, worksheet: '{worksheet_name}'...")

        # Logic xác thực không đổi
        if "gcp_service_account" in st.secrets:
            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        else:
            credentials_path = resource_path(config.SERVICE_ACCOUNT_FILE)
            gc = gspread.service_account(filename=credentials_path)

        # === THAY ĐỔI CÁCH MỞ FILE ===
        # Ưu tiên mở bằng URL từ secrets khi deploy
        if "google_sheet" in st.secrets and "url" in st.secrets["google_sheet"]:
            logging.info("Mở Google Sheet bằng URL từ Secrets...")
            spreadsheet = gc.open_by_url(st.secrets["google_sheet"]["url"])
        # Nếu không, dùng cách cũ (mở bằng tên) cho localhost
        else:
            logging.info("Mở Google Sheet bằng tên từ file config...")
            spreadsheet = gc.open(config.SHEET_NAME)

        worksheet = spreadsheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        logging.info(f"✅ Đọc thành công {len(records)} dòng từ worksheet '{worksheet_name}'.")
        return pd.DataFrame(records)
    except Exception as e:
        logging.error(f"Lỗi khi đọc worksheet '{worksheet_name}': {e}", exc_info=True)
        raise ConnectionError(
            f"Lỗi: Không tìm thấy hoặc không thể đọc worksheet '{worksheet_name}'. Vui lòng kiểm tra file log.")


def get_sheet_data_for_report():
    """
    Lấy dữ liệu sheet cho chức năng Báo cáo Tuần.
    """
    db_df = fetch_worksheet_as_df(config.DB_SHEET)
    on_off_df = fetch_worksheet_as_df(config.ON_OFF_SHEET)
    return db_df, on_off_df

def fetch_unpaid_debt_details():
    """Lấy chi tiết các hóa đơn chưa được giải trừ từ hệ thống (Dùng cho App 1)."""
    try:
        sql_hoadon = (
            f"SELECT {config.API_COL_DANHBA}, {config.API_COL_SOHOADON}, "
            f"{config.API_COL_KY}, {config.API_COL_NAM} "
            f"FROM HoaDon WHERE {config.API_COL_NGAYGIAI} IS NULL"
        )
        dtypes = {config.API_COL_DANHBA: str, config.API_COL_SOHOADON: str, config.API_COL_KY: str, config.API_COL_NAM: str}
        df_hoadon = fetch_dataframe('f_Select_SQL_Thutien', sql_hoadon, dtypes=dtypes)

        if df_hoadon.empty:
            return {}, None

        df_hoadon = df_hoadon.rename(columns={
            config.API_COL_DANHBA: 'DANHBA', config.API_COL_SOHOADON: 'SOHOADON',
            config.API_COL_KY: 'KY', config.API_COL_NAM: 'NAM'
        })
        temp_date = pd.to_datetime(df_hoadon['NAM'] + '-' + df_hoadon['KY'] + '-01', errors='coerce')
        latest_date = temp_date.max()
        latest_period_str = latest_date.strftime('%m/%Y') if pd.notna(latest_date) else None
        sohoadon_list = df_hoadon['SOHOADON'].dropna().unique().tolist()
        df_bgw = _get_bgw_invoices(sohoadon_list)
        if not df_bgw.empty:
            df_bgw = df_bgw.rename(columns={config.API_COL_SHDON_BGW: 'SHDon'})
            shdon_to_exclude = set(df_bgw['SHDon'].astype(str).str.strip())
            hoadon_chua_tra = df_hoadon[~df_hoadon['SOHOADON'].astype(str).str.strip().isin(shdon_to_exclude)].copy()
        else:
            hoadon_chua_tra = df_hoadon.copy()
        if hoadon_chua_tra.empty:
            return {}, latest_period_str
        hoadon_chua_tra['ky_nam'] = hoadon_chua_tra['KY'].str.zfill(2) + '/' + hoadon_chua_tra['NAM']
        unpaid_details = (
            hoadon_chua_tra.groupby('DANHBA')['ky_nam']
            .apply(lambda x: ','.join(sorted(x.unique())))
            .to_dict()
        )
        return unpaid_details, latest_period_str
    except Exception as e:
        logging.error(f"Lỗi khi lấy chi tiết dữ liệu nợ: {e}", exc_info=True)
        return {}, None

def fetch_bgw_payment_dates(sohoadon_list):
    """Lấy ngày thanh toán từ BGW_HD cho một danh sách số hóa đơn cụ thể."""
    if not sohoadon_list:
        return pd.DataFrame()

    all_bgw_dfs = []
    chunk_size = 500
    for i in range(0, len(sohoadon_list), chunk_size):
        chunk = sohoadon_list[i:i + chunk_size]
        formatted_chunk_list = "', '".join(map(str, chunk))
        sql_query = (f"SELECT {config.API_COL_SHDON_BGW}, {config.API_COL_NGAYTT_BGW} "
                     f"FROM BGW_HD WHERE {config.API_COL_SHDON_BGW} IN ('{formatted_chunk_list}')")
        df_chunk = fetch_dataframe('f_Select_SQL_Nganhang', sql_query, dtypes={config.API_COL_SHDON_BGW: str})
        if not df_chunk.empty:
            all_bgw_dfs.append(df_chunk)
    if not all_bgw_dfs:
        return pd.DataFrame()
    bgw_df = pd.concat(all_bgw_dfs, ignore_index=True)
    bgw_df = bgw_df.rename(columns={
        config.API_COL_SHDON_BGW: 'SOHOADON',
        config.API_COL_NGAYTT_BGW: 'NgayThanhToan_BGW'
    })
    bgw_df['NgayThanhToan_BGW'] = pd.to_datetime(bgw_df['NgayThanhToan_BGW'], errors='coerce')
    return bgw_df.dropna(subset=['SOHOADON', 'NgayThanhToan_BGW'])


def append_df_to_worksheet(df_to_append, worksheet_name):
    """Ghi các dòng từ một DataFrame vào cuối một worksheet."""
    if df_to_append.empty:
        logging.warning("DataFrame để ghi xuống rỗng, không thực hiện hành động nào.")
        return 0, "Không có dữ liệu để gửi."

    try:
        num_rows_to_add = len(df_to_append)
        logging.info(f"Chuẩn bị ghi {num_rows_to_add} dòng xuống worksheet '{worksheet_name}'...")

        # Logic xác thực không đổi
        if "gcp_service_account" in st.secrets:
            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        else:
            credentials_path = resource_path(config.SERVICE_ACCOUNT_FILE)
            gc = gspread.service_account(filename=credentials_path)

        # === THAY ĐỔI CÁCH MỞ FILE ===
        if "google_sheet" in st.secrets and "url" in st.secrets["google_sheet"]:
            logging.info("Mở Google Sheet bằng URL từ Secrets...")
            spreadsheet = gc.open_by_url(st.secrets["google_sheet"]["url"])
        else:
            logging.info("Mở Google Sheet bằng tên từ file config...")
            spreadsheet = gc.open(config.SHEET_NAME)

        # Phần còn lại của hàm giữ nguyên
        worksheet = spreadsheet.worksheet(worksheet_name)
        existing_data = worksheet.get_all_values()
        next_row_index = len(existing_data) + 1
        worksheet.add_rows(num_rows_to_add)
        final_df = df_to_append.reindex(columns=config.DB_SHEET_FINAL_COLUMNS)
        rows_to_append = final_df.astype(str).values.tolist()
        start_cell = f'B{next_row_index}'
        worksheet.update(start_cell, rows_to_append, value_input_option='USER_ENTERED')
        logging.info(f"✅ Ghi thành công {len(rows_to_append)} dòng mới.")
        return len(rows_to_append), f"Gửi thành công {len(rows_to_append)} khách hàng."

    except Exception as e:
        logging.error(f"Lỗi khi ghi dữ liệu xuống worksheet '{worksheet_name}': {e}", exc_info=True)
        error_msg = f"Lỗi khi gửi dữ liệu: {e}\n\nXem chi tiết trong app_log.txt"
        return 0, error_msg