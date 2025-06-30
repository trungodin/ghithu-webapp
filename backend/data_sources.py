import gspread
import pandas as pd
import requests
import io
import html
import logging
import diskcache
import sys
import os
import streamlit as st
from streamlit.errors import StreamlitAPIException  # Import thêm lỗi này

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

CACHE = diskcache.Cache('api_cache')


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


# ... các hàm _build_soap_request, execute_sql_query, fetch_dataframe không đổi ...
def _build_soap_request(function_name, sql_query):
    soap_body_template = """<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body><{function_name} xmlns="http://tempuri.org/"><m_sql>{sql_command}</m_sql><m_function_name /><m_user>{user}</m_user></{function_name}></s:Body>
    </s:Envelope>"""
    escaped_sql_command = html.escape(sql_query)
    return soap_body_template.format(
        function_name=function_name, sql_command=escaped_sql_command, user=config.API_USER)


@CACHE.memoize(expire=3600)
def execute_sql_query(function_name, sql_query):
    soap_body = _build_soap_request(function_name, sql_query)
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'"http://tempuri.org/{function_name}"',
        'Host': config.API_URL.split('//')[1].split('/')[0],
    }
    try:
        response = requests.post(
            config.API_URL, data=soap_body.encode('utf-8'), headers=headers, timeout=config.API_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Lỗi kết nối API: {e}")


def fetch_dataframe(function_name, sql_query, dtypes=None):
    xml_response = execute_sql_query(function_name, sql_query)
    try:
        df = pd.read_xml(io.StringIO(xml_response), xpath=".//diffgr:diffgram/NewDataSet/Table1",
                         namespaces={"diffgr": "urn:schemas-microsoft-com:xml-diffgram-v1"}, dtype=dtypes,
                         parse_dates=False, parser='lxml')
        return df
    except (ValueError, KeyError):
        return pd.DataFrame()
    except Exception as e:
        raise ValueError(f"Lỗi khi phân tích XML: {e}")


def _get_gspread_client():
    """Hàm helper để lấy client gspread, ưu tiên secrets."""
    try:
        # Thử đọc từ st.secrets trước.
        creds = st.secrets["gcp_service_account"]
        logging.info("Sử dụng credentials từ Streamlit Secrets.")
        return gspread.service_account_from_dict(creds)
    except (StreamlitAPIException, KeyError):
        # Nếu lỗi, chuyển sang đọc từ file cho môi trường local.
        logging.info("Không tìm thấy secrets, sử dụng file credentials cho local.")
        credentials_path = resource_path(config.SERVICE_ACCOUNT_FILE)
        return gspread.service_account(filename=credentials_path)


def _open_spreadsheet(gc):
    """Hàm helper để mở spreadsheet, ưu tiên URL từ secrets."""
    try:
        # Thử mở bằng URL từ secrets
        url = st.secrets["google_sheet"]["url"]
        logging.info("Mở Google Sheet bằng URL từ Secrets.")
        return gc.open_by_url(url)
    except (StreamlitAPIException, KeyError):
        # Nếu lỗi, mở bằng tên từ file config cho local
        logging.info("Không tìm thấy URL secret, mở Google Sheet bằng tên từ file config.")
        return gc.open(config.SHEET_NAME)


# === SỬA LẠI CÁC HÀM ĐỌC/GHI SHEET ===
def fetch_worksheet_as_df(worksheet_name):
    try:
        logging.info(f"Đang đọc dữ liệu từ Google Sheet, worksheet: '{worksheet_name}'...")
        gc = _get_gspread_client()
        spreadsheet = _open_spreadsheet(gc)
        worksheet = spreadsheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        logging.info(f"✅ Đọc thành công {len(records)} dòng từ worksheet '{worksheet_name}'.")
        return pd.DataFrame(records)
    except Exception as e:
        logging.error(f"Lỗi khi đọc worksheet '{worksheet_name}': {e}", exc_info=True)
        raise ConnectionError(
            f"Lỗi: Không tìm thấy hoặc không thể đọc worksheet '{worksheet_name}'. Vui lòng kiểm tra file log.")


def append_df_to_worksheet(df_to_append, worksheet_name):
    if df_to_append.empty:
        return 0, "Không có dữ liệu để gửi."
    try:
        logging.info(f"Chuẩn bị ghi {len(df_to_append)} dòng xuống worksheet '{worksheet_name}'...")
        gc = _get_gspread_client()
        spreadsheet = _open_spreadsheet(gc)
        worksheet = spreadsheet.worksheet(worksheet_name)

        # Phần còn lại giữ nguyên
        existing_data = worksheet.get_all_values()
        next_row_index = len(existing_data) + 1
        worksheet.add_rows(len(df_to_append))
        final_df = df_to_append.reindex(columns=config.DB_SHEET_FINAL_COLUMNS)
        rows_to_append = final_df.astype(str).values.tolist()
        start_cell = f'B{next_row_index}'
        worksheet.update(start_cell, rows_to_append, value_input_option='USER_ENTERED')
        logging.info(f"✅ Ghi thành công {len(rows_to_append)} dòng mới.")
        return len(rows_to_append), f"Gửi thành công {len(rows_to_append)} khách hàng."
    except Exception as e:
        logging.error(f"Lỗi khi ghi dữ liệu xuống worksheet '{worksheet_name}': {e}", exc_info=True)
        return 0, f"Lỗi khi gửi dữ liệu: {e}\n\nXem chi tiết trong app_log.txt"


# ... các hàm còn lại giữ nguyên ...
def get_sheet_data_for_report():
    db_df = fetch_worksheet_as_df(config.DB_SHEET)
    on_off_df = fetch_worksheet_as_df(config.ON_OFF_SHEET)
    return db_df, on_off_df


def fetch_unpaid_debt_details():
    try:
        sql_hoadon = (f"SELECT {config.API_COL_DANHBA}, {config.API_COL_SOHOADON}, "
                      f"{config.API_COL_KY}, {config.API_COL_NAM} "
                      f"FROM HoaDon WHERE {config.API_COL_NGAYGIAI} IS NULL")
        df_hoadon = fetch_dataframe('f_Select_SQL_Thutien', sql_hoadon,
                                    dtypes={'DANHBA': str, 'SOHOADON': str, 'KY': str, 'NAM': str})
        if df_hoadon.empty: return {}, None
        df_hoadon = df_hoadon.rename(columns={'DANHBA': 'DANHBA', 'SOHOADON': 'SOHOADON', 'KY': 'KY', 'NAM': 'NAM'})
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
        if hoadon_chua_tra.empty: return {}, latest_period_str
        hoadon_chua_tra['ky_nam'] = hoadon_chua_tra['KY'].str.zfill(2) + '/' + hoadon_chua_tra['NAM']
        unpaid_details = (
            hoadon_chua_tra.groupby('DANHBA')['ky_nam'].apply(lambda x: ','.join(sorted(x.unique()))).to_dict())
        return unpaid_details, latest_period_str
    except Exception as e:
        return {}, None


def _get_bgw_invoices(sohoadon_list, function_name='f_Select_SQL_Nganhang'):
    if not sohoadon_list: return pd.DataFrame()
    all_bgw_dfs = []
    for i in range(0, len(sohoadon_list), 500):
        chunk = sohoadon_list[i:i + 500]
        formatted_chunk_list = "', '".join(map(str, chunk))
        sql_bgw_chunk = f"SELECT {config.API_COL_SHDON_BGW} FROM BGW_HD WHERE {config.API_COL_SHDON_BGW} IN ('{formatted_chunk_list}')"
        df_bgw_chunk = fetch_dataframe(function_name, sql_bgw_chunk)
        if not df_bgw_chunk.empty: all_bgw_dfs.append(df_bgw_chunk)
    if not all_bgw_dfs: return pd.DataFrame()
    return pd.concat(all_bgw_dfs, ignore_index=True)


def fetch_bgw_payment_dates(sohoadon_list):
    if not sohoadon_list: return pd.DataFrame()
    all_bgw_dfs = []
    for i in range(0, len(sohoadon_list), 500):
        chunk = sohoadon_list[i:i + 500]
        formatted_chunk_list = "', '".join(map(str, chunk))
        sql_query = (f"SELECT {config.API_COL_SHDON_BGW}, {config.API_COL_NGAYTT_BGW} "
                     f"FROM BGW_HD WHERE {config.API_COL_SHDON_BGW} IN ('{formatted_chunk_list}')")
        df_chunk = fetch_dataframe('f_Select_SQL_Nganhang', sql_query, dtypes={config.API_COL_SHDON_BGW: str})
        if not df_chunk.empty: all_bgw_dfs.append(df_chunk)
    if not all_bgw_dfs: return pd.DataFrame()
    bgw_df = pd.concat(all_bgw_dfs, ignore_index=True)
    bgw_df = bgw_df.rename(
        columns={config.API_COL_SHDON_BGW: 'SOHOADON', config.API_COL_NGAYTT_BGW: 'NgayThanhToan_BGW'})
    bgw_df['NgayThanhToan_BGW'] = pd.to_datetime(bgw_df['NgayThanhToan_BGW'], errors='coerce')
    return bgw_df.dropna(subset=['SOHOADON', 'NgayThanhToan_BGW'])