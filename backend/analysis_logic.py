import pandas as pd
import numpy as np
import logging
from datetime import date, datetime
import sys
import os

# Giúp Python tìm thấy các module ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from backend import data_sources
from functools import reduce # <<< Thêm import này ở đầu file backend/analysis_logic.py


# === HÀM TIỆN ÍCH MỚI ĐỂ ĐỊNH DẠNG NGÀY ===
def format_date_with_vietnamese_weekday(date_obj):
    """
    Chuyển đổi một đối tượng ngày thành chuỗi có dạng 'T2-dd/mm/yyyy'.
    """
    # Nếu không phải là đối tượng ngày (ví dụ: chuỗi 'Tổng cộng'), trả về nguyên bản
    if not isinstance(date_obj, (date, pd.Timestamp)):
        return str(date_obj)

    # Mapping từ thứ của Python (Thứ 2 = 0) sang tiếng Việt
    weekday_map = {
        0: 'T2', 1: 'T3', 2: 'T4', 3: 'T5', 4: 'T6', 5: 'T7', 6: 'CN'
    }
    weekday_str = weekday_map.get(date_obj.weekday(), '')
    date_str = date_obj.strftime('%d/%m/%Y')

    return f"{weekday_str} - {date_str}"


# ==========================================

# ==============================================================================
# LOGIC CHO TAB 1: DASHBOARD
# ==============================================================================
def fetch_dashboard_data():
    """Lấy và xử lý dữ liệu cho dashboard."""
    # (Hàm này được giữ lại từ phiên bản gốc của bạn)
    try:
        logging.info("Bắt đầu lấy dữ liệu cho Dashboard...")
        sql_hoadon = f"SELECT DANHBA, TONGCONG, NAM, KY, SOHOADON FROM {config.TABLE_SOURCE} WHERE NGAYGIAI IS NULL"
        dtypes_hoadon = {'DANHBA': str, 'SOHOADON': str}
        df_hoadon = data_sources.fetch_dataframe('f_Select_SQL_Thutien', sql_hoadon, dtypes=dtypes_hoadon)
        sql_kh = "SELECT DanhBa, GB FROM KhachHang"
        dtypes_kh = {'DanhBa': str, 'GB': str}
        df_kh = data_sources.fetch_dataframe('f_Select_SQL_Doc_so', sql_kh, dtypes=dtypes_kh)
        if not df_hoadon.empty and not df_kh.empty:
            df_kh = df_kh.rename(columns={'DanhBa': 'DANHBA'})
            df_kh['DANHBA'] = df_kh['DANHBA'].str.zfill(11)
            df_hoadon['DANHBA'] = df_hoadon['DANHBA'].str.zfill(11)
            df_merged = pd.merge(df_hoadon, df_kh, on='DANHBA', how='left')
        else:
            df_merged = df_hoadon
        if df_merged.empty: return {}
        sohoadon_list = df_merged['SOHOADON'].dropna().unique().tolist()
        if sohoadon_list:
            df_bgw = data_sources._get_bgw_invoices(sohoadon_list)
            if not df_bgw.empty:
                shdon_to_exclude = df_bgw['SHDon'].astype(str).str.strip().unique()
                df_merged = df_merged[~df_merged['SOHOADON'].astype(str).str.strip().isin(shdon_to_exclude)]
        if df_merged.empty: return {}
        df_merged['TONGCONG'] = pd.to_numeric(df_merged['TONGCONG'], errors='coerce').fillna(0)
        total_debt = df_merged['TONGCONG'].sum()
        total_debtors = df_merged['DANHBA'].nunique()
        debtor_counts = df_merged.groupby('DANHBA').size()
        debtors_over_3_periods = (debtor_counts >= 3).sum()
        debt_by_gb = df_merged.groupby('GB')['TONGCONG'].sum().sort_values(ascending=False).head(10)
        df_merged['KY_NAM_DT'] = pd.to_datetime(df_merged['NAM'].astype(str) + '-' + df_merged['KY'].astype(str).str.zfill(2) + '-01', errors='coerce')
        debt_over_time = df_merged.groupby(pd.Grouper(key='KY_NAM_DT', freq='M'))['TONGCONG'].sum()
        debt_over_time = debt_over_time[debt_over_time.index.year >= date.today().year - 2]
        results = {'total_debt': total_debt, 'total_debtors': total_debtors, 'debtors_over_3_periods': debtors_over_3_periods, 'debt_by_gb': debt_by_gb, 'debt_over_time': debt_over_time}
        logging.info("✅ Hoàn thành lấy dữ liệu Dashboard.")
        return results
    except Exception as e:
        logging.error(f"❌ Lỗi trong fetch_dashboard_data: {e}", exc_info=True); raise

# ==============================================================================
# LOGIC CHO TAB 2: BÁO CÁO TUẦN (Google Sheet)
# ==============================================================================
# (Các hàm này được giữ lại từ phiên bản gốc của bạn)
def _report_prepare_initial_data():
    db_df, on_off_df = data_sources.get_sheet_data_for_report()
    if config.DB_COL_KY_NAM in db_df.columns:
        db_df[config.DB_COL_DANH_BO] = db_df[config.DB_COL_DANH_BO].astype(str).str.strip().str.zfill(11)
        db_df[config.DB_COL_KY_NAM] = db_df[config.DB_COL_KY_NAM].astype(str).str.split(',')
        db_df = db_df.explode(config.DB_COL_KY_NAM).reset_index(drop=True)
        db_df[config.DB_COL_KY_NAM] = db_df[config.DB_COL_KY_NAM].str.strip()
        split_ky_nam = db_df[config.DB_COL_KY_NAM].str.split('/', expand=True)
        if not split_ky_nam.empty:
            db_df['ky'] = split_ky_nam[0].str.strip().str.zfill(2)
            db_df['nam'] = split_ky_nam[1].str.strip()
    for df, col in [(db_df, config.DB_COL_NGAY_GIAO), (on_off_df, config.ON_OFF_COL_NGAY_KHOA),
                    (on_off_df, config.ON_OFF_COL_NGAY_MO)]:
        if col in df.columns:
            clean_col = df[col].astype(str).str.strip()
            df[f'{col}_chuan_hoa'] = pd.to_datetime(clean_col, format=config.DATE_FORMAT_1, errors='coerce').fillna(
                pd.to_datetime(clean_col, format=config.DATE_FORMAT_2, errors='coerce'))
    for col, df in [(config.DB_COL_ID, db_df), (config.ON_OFF_COL_ID, on_off_df), (config.DB_COL_NHOM, db_df),
                    (config.ON_OFF_COL_NHOM_KHOA, on_off_df)]:
        if col in df.columns: df[col] = df[col].astype(str).str.strip()
    return db_df, on_off_df

def _report_enrich_data(df):
    hoadon_details_df = pd.DataFrame()
    danhba_list = df[config.DB_COL_DANH_BO].dropna().unique().tolist()
    if danhba_list:
        formatted_danhba_list = "','".join(map(str, danhba_list))
        sql_details = (f"SELECT {config.API_COL_DANHBA}, {config.API_COL_KY}, {config.API_COL_NAM}, "
                       f"{config.API_COL_SOHOADON}, {config.API_COL_NGAYGIAI} "
                       f"FROM HoaDon WHERE {config.API_COL_DANHBA} IN ('{formatted_danhba_list}')")
        dtypes = {config.API_COL_DANHBA: str, config.API_COL_KY: str, config.API_COL_NAM: str}
        hoadon_details_df = data_sources.fetch_dataframe('f_Select_SQL_Thutien', sql_details, dtypes=dtypes)
    if not hoadon_details_df.empty:
        hoadon_details_df = hoadon_details_df.rename(columns={'KY': 'ky', 'NAM': 'nam', config.API_COL_DANHBA: config.DB_COL_DANH_BO})
        for col, zfill_val in [(config.DB_COL_DANH_BO, 11), ('ky', 2)]:
            hoadon_details_df[col] = hoadon_details_df[col].astype(str).str.strip().str.zfill(zfill_val)
        hoadon_details_df['nam'] = hoadon_details_df['nam'].astype(str).str.strip()
        df = pd.merge(df, hoadon_details_df, on=[config.DB_COL_DANH_BO, 'ky', 'nam'], how='left')
    df['NGAYGIAI_DT_raw'] = pd.to_datetime(df.get(config.API_COL_NGAYGIAI), errors='coerce')
    sohoadon_list = df[df['SOHOADON'].notna()]['SOHOADON'].unique().tolist()
    if sohoadon_list:
        bgw_dates_df = data_sources.fetch_bgw_payment_dates(sohoadon_list)
        if not bgw_dates_df.empty:
            df = pd.merge(df, bgw_dates_df, on='SOHOADON', how='left')
            if 'NgayThanhToan_BGW' in df.columns:
                df = df.rename(columns={'NgayThanhToan_BGW': 'NgayThanhToan_BGW_DT'})
    return df

def _report_process_final_data(df, unpaid_debt_details, latest_period, payment_deadline_str):
    main_tz = df['NGAYGIAI_DT_raw'].dt.tz
    if 'NgayThanhToan_BGW_DT' in df.columns:
        bgw_not_na_mask = df['NgayThanhToan_BGW_DT'].notna()
        if bgw_not_na_mask.any():
            bgw_col = df.loc[bgw_not_na_mask, 'NgayThanhToan_BGW_DT']
            if pd.api.types.is_datetime64_any_dtype(bgw_col) and bgw_col.dt.tz is not None:
                df.loc[bgw_not_na_mask, 'NgayThanhToan_BGW_DT'] = bgw_col.dt.tz_convert(main_tz)
            else:
                df.loc[bgw_not_na_mask, 'NgayThanhToan_BGW_DT'] = bgw_col.dt.tz_localize(main_tz, ambiguous='infer')
        df['NGAYGIAI_DT'] = df['NgayThanhToan_BGW_DT'].fillna(df['NGAYGIAI_DT_raw'])
    else:
        df['NGAYGIAI_DT'] = df['NGAYGIAI_DT_raw']
    conditions = [
        df[config.DB_COL_TINH_TRANG].astype(str).str.strip().str.upper() == 'KHOÁ NƯỚC',
        df['NGAYGIAI_DT'].notna()
    ]
    choices = ['Khóa nước', 'Đã Thanh Toán']
    df['Tình Trạng Nợ'] = np.select(conditions, choices, default='Chưa Thanh Toán')
    df['ky_nam chưa thanh toán'] = df[config.DB_COL_DANH_BO].map(unpaid_debt_details).fillna('')
    is_unpaid_now = df['Tình Trạng Nợ'] == 'Chưa Thanh Toán'
    unpaid_periods = df['ky_nam chưa thanh toán'].astype(str).str.strip()
    paid_in_system = (unpaid_periods == '') | ((latest_period is not None) & (unpaid_periods == latest_period))
    df.loc[is_unpaid_now & paid_in_system, 'Tình Trạng Nợ'] = 'Đã Thanh Toán'
    deadline_naive = pd.to_datetime(payment_deadline_str, dayfirst=True) + pd.Timedelta(days=1, seconds=-1)
    if main_tz is not None:
        deadline = deadline_naive.tz_localize(main_tz)
    else:
        deadline = deadline_naive
    late_payment_mask = df['NGAYGIAI_DT'].notna() & (df['NGAYGIAI_DT'] > deadline)
    df.loc[late_payment_mask, 'Tình Trạng Nợ'] = 'Chưa Thanh Toán'
    df.loc[late_payment_mask, 'NGAYGIAI_DT'] = pd.NaT
    return df

def _report_build_summary(processed_df, selected_group):
    if processed_df.empty: return pd.DataFrame()
    processed_df['Ngày Giao'] = processed_df[f'{config.DB_COL_NGAY_GIAO}_chuan_hoa'].dt.date
    daily_customer_summary = processed_df.drop_duplicates(
        subset=['Ngày Giao', config.DB_COL_NHOM, config.DB_COL_DANH_BO]).copy()
    daily_summary_df = daily_customer_summary.groupby([config.DB_COL_NHOM, 'Ngày Giao']).agg(
        So_Luong=(config.DB_COL_DANH_BO, 'count'),
        Da_Thanh_Toan=('Tình Trạng Nợ', lambda s: (s == 'Đã Thanh Toán').sum()),
        So_Luong_Khoa=('is_locked', 'sum')
    ).reset_index()
    if daily_summary_df.empty: return pd.DataFrame()
    daily_summary_df = daily_summary_df.sort_values(by=[config.DB_COL_NHOM, 'Ngày Giao'])
    daily_summary_df['Phan_Tram_Hoan_Thanh'] = "0.00%"
    mask_sl_not_zero = daily_summary_df['So_Luong'] > 0
    daily_summary_df.loc[mask_sl_not_zero, 'Phan_Tram_Hoan_Thanh'] = (
            ((daily_summary_df['Da_Thanh_Toan'] + daily_summary_df['So_Luong_Khoa']) /
             daily_summary_df['So_Luong']) * 100
    ).apply(lambda x: f"{x:.2f}%")
    total_so_luong = daily_summary_df['So_Luong'].sum()
    total_da_thanh_toan = daily_summary_df['Da_Thanh_Toan'].sum()
    total_so_luong_khoa = daily_summary_df['So_Luong_Khoa'].sum()
    total_phan_tram_val = (
            (total_da_thanh_toan + total_so_luong_khoa) / total_so_luong * 100) if total_so_luong > 0 else 0
    total_row = pd.DataFrame([{'Ngày Giao': 'Tổng cộng', 'So_Luong': total_so_luong,
                               'Da_Thanh_Toan': total_da_thanh_toan, 'So_Luong_Khoa': total_so_luong_khoa,
                               'Phan_Tram_Hoan_Thanh': f"{total_phan_tram_val:.2f}%"}])
    total_row[config.DB_COL_NHOM] = ''
    final_summary_df = pd.concat([daily_summary_df, total_row], ignore_index=True)
    final_summary_df['Ngày Giao'] = final_summary_df['Ngày Giao'].apply(
        lambda x: x.strftime('%d/%m/%Y') if isinstance(x, date) else x)
    final_summary_df = final_summary_df.rename(columns={
        config.DB_COL_NHOM: 'Nhóm', 'Ngày Giao': 'Ngày Giao', 'So_Luong': 'Số Lượng',
        'Da_Thanh_Toan': 'Đã Thanh Toán', 'So_Luong_Khoa': 'Số Lượng Khóa',
        'Phan_Tram_Hoan_Thanh': '% Hoàn thành'})
    if selected_group != "Tất cả các nhóm":
        final_summary_df = final_summary_df.drop(columns=['Nhóm'])
    return final_summary_df

def _report_build_details(processed_df):
    agg_funcs = {
        'Tên KH': (config.DB_COL_TEN_KH, 'first'), 'Số nhà': (config.DB_COL_SO_NHA, 'first'),
        'Đường': (config.DB_COL_TEN_DUONG, 'first'), 'Tổng kỳ': (config.DB_COL_TONG_KY, 'first'),
        'Tổng tiền': (config.DB_COL_TONG_TIEN, 'first'),
        'Kỳ năm': (config.DB_COL_KY_NAM, lambda s: ', '.join(s.dropna().unique())),
        'KỲ chưa TT': ('ky_nam chưa thanh toán', 'first'), 'Hộp': (config.DB_COL_HOP_BV, 'first'),
        'Đợt': (config.DB_COL_DOT, 'first'), 'GB': (config.DB_COL_GB, 'first'),
        'Tình Trạng Nợ': ('Tình Trạng Nợ', 'first'), 'Ngày TT': ('NGAYGIAI_DT', 'max'),'Ghi chú': (config.DB_COL_GHI_CHU, 'first')}
    final_df = processed_df.groupby(config.DB_COL_DANH_BO).agg(**agg_funcs).reset_index()
    final_df['Ngày TT'] = final_df['Ngày TT'].dt.strftime('%d/%m/%Y').fillna('')
    final_df = final_df.rename(columns={config.DB_COL_DANH_BO: 'Danh bạ'})
    display_order = ['Danh bạ', 'Tên KH', 'Tình Trạng Nợ', 'Ngày TT', 'KỲ chưa TT', 'Số nhà', 'Đường',
                     'Tổng kỳ', 'Tổng tiền', 'Kỳ năm', 'GB', 'Đợt', 'Hộp','Ghi chú']
    return final_df[[col for col in display_order if col in final_df.columns]]


def _report_build_stats(processed_df, on_off_df, start_date_str, end_date_str, selected_group):
    start_date = pd.to_datetime(start_date_str, dayfirst=True).date()
    end_date = pd.to_datetime(end_date_str, dayfirst=True).date()
    ids_da_giao = processed_df[config.DB_COL_ID].dropna().unique().tolist()
    on_off_subset_df = on_off_df[on_off_df[config.ON_OFF_COL_ID].isin(ids_da_giao)].copy()

    khoa_df = on_off_subset_df.dropna(subset=[f'{config.ON_OFF_COL_NGAY_KHOA}_chuan_hoa']).copy()
    khoa_df['Ngày'] = khoa_df[f'{config.ON_OFF_COL_NGAY_KHOA}_chuan_hoa'].dt.date
    khoa_df_filtered = khoa_df[(khoa_df['Ngày'] >= start_date) & (khoa_df['Ngày'] <= end_date)]

    bang_khoa = pd.DataFrame()
    if not khoa_df_filtered.empty and config.ON_OFF_COL_KIEU_KHOA in khoa_df_filtered.columns:
        try:
            bang_khoa = pd.pivot_table(
                khoa_df_filtered,
                index=['Ngày', config.ON_OFF_COL_NHOM_KHOA],
                columns=config.ON_OFF_COL_KIEU_KHOA,
                values=config.ON_OFF_COL_ID,
                aggfunc='count',
                fill_value=0
            ).reset_index()

            # === THAY ĐỔI TIÊU ĐỀ TẠI ĐÂY ===
            rename_dict = {
                'Khóa van từ': 'Khoá từ',
                'Khóa van bấm chì': 'Khóa van',
                'Khóa nút bít': 'Khóa NB'  # <-- Đã sửa tại đây
            }
            bang_khoa.rename(columns=rename_dict, inplace=True)

        except Exception as e:
            logging.error(f"Lỗi khi pivot bảng khóa: {e}")
            bang_khoa = pd.DataFrame()

    expected_lock_cols = ['Khoá từ', 'Khóa van', 'Khóa NB']  # <-- Cập nhật tên mới
    for col in expected_lock_cols:
        if col not in bang_khoa.columns:
            bang_khoa[col] = 0

    # ... (Phần code xử lý Mở và Thanh Toán không đổi) ...
    mo_df = on_off_subset_df.dropna(subset=[f'{config.ON_OFF_COL_NGAY_MO}_chuan_hoa']).copy();
    mo_df['Ngày'] = mo_df[f'{config.ON_OFF_COL_NGAY_MO}_chuan_hoa'].dt.date
    mo_df_filtered = mo_df[(mo_df['Ngày'] >= start_date) & (mo_df['Ngày'] <= end_date)];
    bang_mo = pd.DataFrame()
    if not mo_df_filtered.empty: bang_mo = mo_df_filtered.groupby(
        ['Ngày', config.ON_OFF_COL_NHOM_KHOA]).size().reset_index(name='Số Lượng Mở')
    payments_df = processed_df[
        (processed_df['Tình Trạng Nợ'] == 'Đã Thanh Toán') & (processed_df['NGAYGIAI_DT'].notna())].copy()
    payments_df['Ngày'] = payments_df['NGAYGIAI_DT'].dt.date;
    payments_df_filtered = payments_df[(payments_df['Ngày'] >= start_date) & (payments_df['Ngày'] <= end_date)]
    payments_summary = pd.DataFrame()
    if not payments_df_filtered.empty: payments_summary = payments_df_filtered.groupby(
        ['Ngày', config.DB_COL_NHOM]).agg(count_col=(config.DB_COL_DANH_BO, 'nunique')).reset_index().rename(
        columns={'count_col': 'Thanh toán ngày', config.DB_COL_NHOM: config.ON_OFF_COL_NHOM_KHOA})

    # Gộp các bảng lại
    from functools import reduce
    dfs_to_merge = [df for df in [bang_khoa, bang_mo, payments_summary] if not df.empty]
    if not dfs_to_merge: return pd.DataFrame()
    bang_thong_ke = reduce(
        lambda left, right: pd.merge(left, right, on=['Ngày', config.ON_OFF_COL_NHOM_KHOA], how='outer'), dfs_to_merge)

    all_cols = expected_lock_cols + ['Số Lượng Mở', 'Thanh toán ngày']
    for col in all_cols:
        if col not in bang_thong_ke.columns:
            bang_thong_ke[col] = 0
    bang_thong_ke[all_cols] = bang_thong_ke[all_cols].fillna(0).astype(int)

    total_row_dict = {'Ngày': 'Tổng cộng'}
    for col in all_cols:
        total_row_dict[col] = bang_thong_ke[col].sum()
    if config.ON_OFF_COL_NHOM_KHOA in bang_thong_ke.columns:
        total_row_dict[config.ON_OFF_COL_NHOM_KHOA] = ''
    total_row = pd.DataFrame([total_row_dict])

    bang_thong_ke = bang_thong_ke.sort_values(by=['Ngày'])
    bang_thong_ke = pd.concat([bang_thong_ke, total_row], ignore_index=True)

    bang_thong_ke = bang_thong_ke.rename(columns={config.ON_OFF_COL_NHOM_KHOA: 'Nhóm'})
    if selected_group != "Tất cả các nhóm" and 'Nhóm' in bang_thong_ke.columns:
        bang_thong_ke = bang_thong_ke.drop(columns=['Nhóm'])
    bang_thong_ke['Ngày'] = bang_thong_ke['Ngày'].apply(format_date_with_vietnamese_weekday)

    # Sắp xếp lại thứ tự cột với tên mới
    final_order = ['Ngày', 'Khoá từ', 'Khóa van', 'Khóa NB', 'Số Lượng Mở', 'Thanh toán ngày']
    if 'Nhóm' in bang_thong_ke.columns:
        final_order.insert(1, 'Nhóm')

    existing_final_cols = [col for col in final_order if col in bang_thong_ke.columns]
    bang_thong_ke = bang_thong_ke[existing_final_cols]

    return bang_thong_ke

# Hàm chính cho báo cáo tuần
def run_weekly_report_analysis(start_date_str, end_date_str, selected_group, payment_deadline_str):
    logging.info(f"Bắt đầu chạy 'Báo cáo Tuần': {start_date_str}, {end_date_str}, {selected_group}")
    try:
        db_df, on_off_df = _report_prepare_initial_data()
        start_date = pd.to_datetime(start_date_str, dayfirst=True)
        end_date = pd.to_datetime(end_date_str, dayfirst=True)

        mask = (db_df[f'{config.DB_COL_NGAY_GIAO}_chuan_hoa'].dt.date >= start_date.date()) & \
               (db_df[f'{config.DB_COL_NGAY_GIAO}_chuan_hoa'].dt.date <= end_date.date())
        danh_sach_chi_tiet_df = db_df[mask].copy()

        if selected_group != "Tất cả các nhóm":
            danh_sach_chi_tiet_df = danh_sach_chi_tiet_df[danh_sach_chi_tiet_df[config.DB_COL_NHOM] == selected_group]

        if danh_sach_chi_tiet_df.empty:
            return {'error': "Không có dữ liệu để phân tích cho ngày và nhóm đã chọn."}

        unpaid_debt_details, latest_period = data_sources.fetch_unpaid_debt_details()
        processed_df = _report_enrich_data(danh_sach_chi_tiet_df)
        locked_ids = set(on_off_df[on_off_df[config.ON_OFF_COL_ID].notna()][config.ON_OFF_COL_ID])
        processed_df['is_locked'] = processed_df[config.DB_COL_ID].isin(locked_ids)
        processed_df = _report_process_final_data(processed_df, unpaid_debt_details, latest_period, payment_deadline_str)

        summary_df = _report_build_summary(processed_df, selected_group)
        details_df = _report_build_details(processed_df)
        stats_df = _report_build_stats(processed_df, on_off_df, start_date_str, payment_deadline_str, selected_group)

        pie_chart_data = {}
        groups_to_chart = [selected_group] if selected_group != "Tất cả các nhóm" else processed_df[config.DB_COL_NHOM].unique().tolist()
        for group_name in groups_to_chart:
            group_df = processed_df[processed_df[config.DB_COL_NHOM] == group_name]
            so_luong = group_df[config.DB_COL_DANH_BO].nunique()
            unique_customers_in_group = group_df.drop_duplicates(subset=[config.DB_COL_DANH_BO])
            da_thanh_toan = (unique_customers_in_group['Tình Trạng Nợ'] == 'Đã Thanh Toán').sum()
            so_luong_khoa = unique_customers_in_group['is_locked'].sum()
            hoan_thanh = da_thanh_toan + so_luong_khoa
            chua_hoan_thanh = so_luong - hoan_thanh
            if so_luong > 0:
                pie_chart_data[group_name] = {'labels': ['Hoàn thành', 'Chưa hoàn thành'],
                                              'sizes': [hoan_thanh, chua_hoan_thanh]}
        results = {
            'start_date_str': start_date_str, 'end_date_str': end_date_str, 'selected_group': selected_group,
            'payment_deadline_str': payment_deadline_str, 'summary_df': summary_df, 'stats_df': stats_df,
            'details_df': details_df, 'pie_chart_data': pie_chart_data,
            'exportable_dfs': {'Tong_Hop_Nhom': summary_df, 'Thong_Ke_Khoa_Mo': stats_df,
                               'Chi_Tiet_Da_Giao': details_df}
        }
        logging.info("✅ Hoàn thành 'Báo cáo Tuần'.")
        return results
    except Exception as e:
        detailed_error = f"❌ Lỗi trong run_weekly_report_analysis: {e}"
        logging.error(detailed_error, exc_info=True)
        raise

# ==============================================================================
# LOGIC CHO TAB 3: LỌC DỮ LIỆU TỒN & GỬI DS (Google Sheet)
# ==============================================================================
def run_debt_filter_analysis(params):
    """
    Lấy và xử lý dữ liệu tồn.
    Tương đương DebtAnalysisWorker.
    """
    logging.info(f"Bắt đầu chạy 'Lọc Dữ liệu Tồn' với các tham số: {params}")
    try:
        p = params
        string_dtypes = {'DanhBa': str, 'DANHBA': str, 'MLT2': str, 'DOT': str, 'SOHOADON': str, 'CodeMoi': str}

        sql_docso = f"SELECT DanhBa, CodeMoi, CoCu FROM DocSo WHERE Nam = {p['nam']} AND Ky = {p['ky']}"
        df_docso = data_sources.fetch_dataframe('f_Select_SQL_Doc_so', sql_docso, dtypes=string_dtypes)
        if not df_docso.empty: df_docso['DanhBa'] = df_docso['DanhBa'].str.zfill(11)

        sql_hoadon_base = f"SELECT DANHBA, GB, TONGCONG, KY, NAM, TENKH, SO, DUONG, SOHOADON, DOT FROM HoaDon WHERE NGAYGIAI IS NULL AND NAM <= {p['nam']}"
        if p['dot_filter']:
            dot_in_clause = ", ".join(map(str, p['dot_filter']))
            sql_hoadon_base += f" AND DOT IN ({dot_in_clause})"
        df_hoadon = data_sources.fetch_dataframe('f_Select_SQL_Thutien', sql_hoadon_base, dtypes=string_dtypes)

        if df_hoadon.empty:
            return pd.DataFrame()

        df_hoadon['DANHBA'] = df_hoadon['DANHBA'].str.zfill(11)
        df_hoadon['TONGCONG'] = pd.to_numeric(df_hoadon['TONGCONG'], errors='coerce').fillna(0)

        sql_kh = "SELECT DanhBa, MLT2, SoMoi, SoThan, Hieu, HopBaoVe, SDT FROM KhachHang"
        df_kh = data_sources.fetch_dataframe('f_Select_SQL_Doc_so', sql_kh, dtypes=string_dtypes)
        if not df_kh.empty: df_kh['DanhBa'] = df_kh['DanhBa'].str.zfill(11)

        merged_df = pd.merge(df_hoadon, df_kh, left_on='DANHBA', right_on='DanhBa', how='left')
        merged_df = pd.merge(merged_df, df_docso, left_on='DANHBA', right_on='DanhBa', how='left', suffixes=('', '_docso'))

        if p['exclude_codemoi']:
            merged_df['CodeMoi'] = merged_df['CodeMoi'].str.strip().str.upper()
            merged_df = merged_df[~merged_df['CodeMoi'].isin(p['exclude_codemoi'])]

        sohoadon_list = merged_df['SOHOADON'].dropna().unique().tolist()
        if sohoadon_list:
            df_bgw = data_sources._get_bgw_invoices(sohoadon_list)
            if not df_bgw.empty:
                shdon_to_exclude = df_bgw['SHDon'].astype(str).str.strip().unique()
                merged_df = merged_df[~merged_df['SOHOADON'].astype(str).str.strip().isin(shdon_to_exclude)]

        hoadon_chua_tra = merged_df.copy()

        hoadon_chua_tra['KY_NAM'] = hoadon_chua_tra['KY'].astype(str).str.zfill(2) + '/' + hoadon_chua_tra['NAM'].astype(str)
        grouping_keys = ['DANHBA', 'TENKH', 'SO', 'DUONG', 'GB', 'DOT', 'MLT2', 'SoMoi', 'SoThan', 'Hieu', 'CodeMoi', 'CoCu', 'HopBaoVe', 'SDT']
        existing_grouping_keys = [key for key in grouping_keys if key in hoadon_chua_tra.columns]

        aggregated_df = hoadon_chua_tra.groupby(existing_grouping_keys, dropna=False).agg(
            TONGCONG=('TONGCONG', 'sum'),
            TONGKY=('DANHBA', 'size'),
            KY_NAM=('KY_NAM', lambda x: ','.join(sorted(x.unique())))
        ).reset_index()
        final_df = aggregated_df[
            (aggregated_df['TONGKY'] >= p['min_tongky']) & (aggregated_df['TONGCONG'] >= p['min_tongcong'])]

        df_sheet = data_sources.fetch_worksheet_as_df(config.ON_OFF_SHEET)
        if not df_sheet.empty and config.ON_OFF_COL_DANH_BA in df_sheet.columns and config.ON_OFF_COL_TINH_TRANG in df_sheet.columns:
            df_sheet[config.ON_OFF_COL_DANH_BA] = df_sheet[config.ON_OFF_COL_DANH_BA].astype(str).str.strip().str.zfill(11)
            df_sheet[config.ON_OFF_COL_TINH_TRANG] = df_sheet[config.ON_OFF_COL_TINH_TRANG].astype(str).str.strip()
            df_sheet_to_merge = df_sheet[[config.ON_OFF_COL_DANH_BA, config.ON_OFF_COL_TINH_TRANG]].drop_duplicates(subset=[config.ON_OFF_COL_DANH_BA], keep='last')
            result_df = pd.merge(final_df, df_sheet_to_merge, left_on='DANHBA', right_on=config.ON_OFF_COL_DANH_BA, how='left')
            statuses_to_exclude = ['đang khóa', 'đang khoá', 'đã hủy']
            temp_status_col = result_df[config.ON_OFF_COL_TINH_TRANG].str.lower().fillna('')
            result_df = result_df[~temp_status_col.isin(statuses_to_exclude)]
            if config.ON_OFF_COL_DANH_BA in result_df.columns:
                result_df = result_df.drop(columns=[config.ON_OFF_COL_DANH_BA, config.ON_OFF_COL_TINH_TRANG])
        else:
            result_df = final_df.copy()

        limit = params.get('limit')
        if limit and limit > 0 and 'TONGCONG' in result_df.columns:
            result_df = result_df.sort_values(by='TONGCONG', ascending=False).head(limit)

        if 'MLT2' in result_df.columns and 'DOT' in result_df.columns:
            result_df = result_df.sort_values(by=['MLT2', 'DOT'])

        desired_column_order = ['DANHBA', 'GB', 'TONGCONG', 'TONGKY', 'KY_NAM', 'TENKH', 'SO', 'DUONG', 'MLT2',
                                'SoMoi', 'DOT', 'CodeMoi', 'SoThan', 'Hieu', 'CoCu', 'HopBaoVe', 'SDT']
        existing_columns_in_order = [col for col in desired_column_order if col in result_df.columns]
        final_result = result_df[existing_columns_in_order] if existing_columns_in_order else pd.DataFrame()
        logging.info("✅ Hoàn thành 'Lọc Dữ liệu Tồn'.")
        return final_result

    except Exception as e:
        detailed_error = f"❌ Lỗi trong run_debt_filter_analysis: {e}"
        logging.error(detailed_error, exc_info=True)
        raise

# ==============================================================================
# LOGIC GỬI DỮ LIỆU LÊN SHEET
# ==============================================================================
def prepare_and_send_to_sheet(selected_df, assign_group, assign_date_str):
    """
    Chuẩn bị dữ liệu và gọi hàm gửi lên Google Sheet.
    Tương đương SheetAppendWorker.
    """
    try:
        df = selected_df.copy()
        # Xử lý các cột hiện có
        if 'HopBaoVe' in df.columns:
            df['HopBaoVe'] = df['HopBaoVe'].fillna(False).astype(bool).astype(int)
        if 'SoMoi' in df.columns:
            df['SoMoi'] = df['SoMoi'].fillna('')

        # === KHÔI PHỤC LẠI VIỆC TẠO CỘT STT ===
        df.insert(0, 'STT', range(1, len(df) + 1))

        # Tạo các cột khác
        df['nhom'] = assign_group
        df['ngay_giao_ds'] = assign_date_str
        today_str_for_id = datetime.now().strftime('%d%m%Y')
        df['ID'] = df['DANHBA'] + '-' + today_str_for_id

        base_url = "https://capnuocbenthanh.com/tra-cuu/?code="
        df['tra_cuu_no'] = base_url + df['DANHBA']

        # Mapping bao gồm cả cột STT
        column_mapping = {
            'DANHBA': 'danh_bo', 'SO': 'so_nha', 'SoMoi': 'DCTT', 'DUONG': 'ten_duong',
            'TENKH': 'ten_kh', 'TONGKY': 'tong_ky', 'TONGCONG': 'tong_tien',
            'KY_NAM': 'ky_nam', 'GB': 'GB', 'DOT': 'DOT', 'HopBaoVe': 'hop_bv',
            'SoThan': 'so_than', 'nhom': 'nhom', 'ngay_giao_ds': 'ngay_giao_ds',
            'ID': 'ID', 'STT': 'STT',
            'tra_cuu_no': 'tra_cuu_no'
        }
        df_to_send = df.rename(columns=column_mapping)

        # Gọi hàm gửi sheet
        return data_sources.append_df_to_worksheet(df_to_send, config.DB_SHEET)

    except Exception as e:
        logging.error(f"Lỗi khi chuẩn bị dữ liệu để gửi: {e}", exc_info=True)
        return 0, f"Lỗi khi chuẩn bị dữ liệu: {e}"


# Thêm hàm này vào cuối file backend/analysis_logic.py

def run_yearly_revenue_analysis_from_db(start_year, end_year, den_ngay_giai_filter):
    logging.info(f"Bắt đầu Phân tích Doanh thu Năm (DB) cho {start_year}-{end_year}, đến ngày {den_ngay_giai_filter}")
    try:
        den_ngay_giai_str = den_ngay_giai_filter.strftime('%Y-%m-%d'); nhanvien_giai_column = 'NV_GIAI'; value_to_exclude_nv_giai = 'NKD'
        full_query = f"""
            WITH TermA_CTE AS (SELECT hd_a.{config.BILLING_YEAR_COLUMN} AS Nam_A, SUM(hd_a.{config.SUM_VALUE_COLUMN}) AS Sum_A_tongcong_bd FROM {config.TABLE_SOURCE} hd_a WHERE hd_a.{config.BILLING_YEAR_COLUMN} >= {start_year} AND hd_a.{config.BILLING_YEAR_COLUMN} <= {end_year} AND (hd_a.{nhanvien_giai_column} <> '{value_to_exclude_nv_giai}' OR hd_a.{nhanvien_giai_column} IS NULL) AND hd_a.{config.SUM_VALUE_COLUMN} IS NOT NULL GROUP BY hd_a.{config.BILLING_YEAR_COLUMN}),
            TermB_CTE AS (SELECT hd_b.{config.BILLING_YEAR_COLUMN} AS Nam_B, SUM(hd_b.{config.SUM_VALUE_COLUMN} - hd_b.{config.ORIGINAL_SUM_COLUMN}) AS Sum_B_adjustment FROM {config.TABLE_SOURCE} hd_b WHERE hd_b.{config.BILLING_YEAR_COLUMN} >= {start_year} AND hd_b.{config.BILLING_YEAR_COLUMN} <= {end_year} AND YEAR(hd_b.{config.PAYMENT_DATE_COLUMN}) = hd_b.{config.BILLING_YEAR_COLUMN} AND hd_b.{config.PAYMENT_DATE_COLUMN} IS NOT NULL AND CAST(hd_b.{config.PAYMENT_DATE_COLUMN} AS DATE) <= '{den_ngay_giai_str}' AND hd_b.{config.SUM_VALUE_COLUMN} IS NOT NULL AND hd_b.{config.ORIGINAL_SUM_COLUMN} IS NOT NULL GROUP BY hd_b.{config.BILLING_YEAR_COLUMN}),
            ThucThu_CTE AS (SELECT t.{config.BILLING_YEAR_COLUMN} AS Nam_TT, SUM(t.{config.ORIGINAL_SUM_COLUMN}) AS ActualThucThu FROM {config.TABLE_SOURCE} t WHERE t.{config.BILLING_YEAR_COLUMN} >= {start_year} AND t.{config.BILLING_YEAR_COLUMN} <= {end_year} AND t.{config.PAYMENT_DATE_COLUMN} IS NOT NULL AND CAST(t.{config.PAYMENT_DATE_COLUMN} AS DATE) <= '{den_ngay_giai_str}' AND t.{config.BILLING_YEAR_COLUMN} = YEAR(t.{config.PAYMENT_DATE_COLUMN}) AND (t.{nhanvien_giai_column} <> '{value_to_exclude_nv_giai}' OR t.{nhanvien_giai_column} IS NULL) AND t.{config.ORIGINAL_SUM_COLUMN} IS NOT NULL GROUP BY t.{config.BILLING_YEAR_COLUMN})
            SELECT a.Nam_A AS Nam, (ISNULL(a.Sum_A_tongcong_bd, 0) - ISNULL(b.Sum_B_adjustment, 0)) AS TongDoanhThu, ISNULL(tt.ActualThucThu, 0) AS TongThucThu FROM TermA_CTE a LEFT JOIN ThucThu_CTE tt ON a.Nam_A = tt.Nam_TT LEFT JOIN TermB_CTE b ON a.Nam_A = b.Nam_B WHERE a.Nam_A IS NOT NULL ORDER BY a.Nam_A;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', full_query)
        final_columns = ['Nam', 'TongDoanhThu', 'TongThucThu', 'Tồn Thu', '% Đạt']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        df_result['Nam'] = pd.to_numeric(df_result['Nam'], errors='coerce').fillna(0).astype(int); df_result['TongDoanhThu'] = pd.to_numeric(df_result['TongDoanhThu'], errors='coerce').fillna(0); df_result['TongThucThu'] = pd.to_numeric(df_result['TongThucThu'], errors='coerce').fillna(0)
        df_result['Tồn Thu'] = df_result['TongDoanhThu'] - df_result['TongThucThu']
        df_result['% Đạt'] = np.where(df_result['TongDoanhThu'] != 0, (df_result['TongThucThu'] / df_result['TongDoanhThu']) * 100, 0.0)
        for col in final_columns:
            if col not in df_result.columns: df_result[col] = 0
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_yearly_revenue_analysis_from_db: {e}", exc_info=True); raise




def run_yearly_revenue_analysis_from_db_DEBUG(start_year, end_year):
    """
    Hàm DEBUG: Chạy truy vấn đơn giản nhất có thể để kiểm tra dữ liệu.
    """
    logging.info(f"--- CHẠY Ở CHẾ ĐỘ DEBUG ---")
    try:
        # Truy vấn đơn giản nhất: Chỉ đếm số hóa đơn và tổng tiền theo năm đã chọn.
        # Không có bất kỳ điều kiện phức tạp nào khác.
        debug_query = f"""
            SELECT 
                {config.BILLING_YEAR_COLUMN} as Nam,
                COUNT(*) as SoLuongHoaDon,
                SUM({config.ORIGINAL_SUM_COLUMN}) as TongTien
            FROM {config.TABLE_SOURCE}
            WHERE {config.BILLING_YEAR_COLUMN} >= {start_year} AND {config.BILLING_YEAR_COLUMN} <= {end_year}
            GROUP BY {config.BILLING_YEAR_COLUMN}
            ORDER BY {config.BILLING_YEAR_COLUMN};
        """
        logging.info(f"DEBUG SQL: {debug_query}")

        # Gọi API với câu lệnh SQL đơn giản
        df_debug = data_sources.fetch_dataframe('f_Select_SQL_Thutien', debug_query)

        # Trả về trực tiếp để xem kết quả thô
        return df_debug

    except Exception as e:
        logging.error(f"Lỗi trong hàm DEBUG: {e}", exc_info=True)
        raise

# Thêm hàm này vào cuối file backend/analysis_logic.py

def run_monthly_analysis_from_db(selected_year):
    """
    Lấy dữ liệu chi tiết theo từng Kỳ/Tháng của một năm đã chọn.
    Tương đương với KyDataQueryWorker.
    """
    logging.info(f"Bắt đầu Phân tích theo Kỳ cho năm {selected_year}")

    try:
        # Câu lệnh SQL được chuyển thể từ KyDataQueryWorker
        full_query_ky = f"""
            WITH DoanhThuTheoKy AS (
                SELECT 
                    {config.PERIOD_COLUMN} AS KyDT, 
                    SUM({config.SUM_VALUE_COLUMN}) AS DoanhThuKyCalc 
                FROM {config.TABLE_SOURCE} 
                WHERE {config.BILLING_YEAR_COLUMN} = {selected_year}
                  AND {config.PERIOD_COLUMN} IS NOT NULL 
                  AND {config.SUM_VALUE_COLUMN} IS NOT NULL 
                GROUP BY {config.PERIOD_COLUMN}
            ), 
            ThucThuTheoThang AS (
                SELECT 
                    MONTH({config.PAYMENT_DATE_COLUMN}) AS ThangTT,
                    SUM({config.ORIGINAL_SUM_COLUMN}) AS ThucThuThangCalc 
                FROM {config.TABLE_SOURCE} 
                WHERE 
                    {config.BILLING_YEAR_COLUMN} = YEAR({config.PAYMENT_DATE_COLUMN})
                    AND {config.PERIOD_COLUMN} = MONTH({config.PAYMENT_DATE_COLUMN})
                    AND YEAR({config.PAYMENT_DATE_COLUMN}) = {selected_year}
                    AND {config.ORIGINAL_SUM_COLUMN} IS NOT NULL 
                GROUP BY MONTH({config.PAYMENT_DATE_COLUMN})
            )
            SELECT 
                COALESCE(dtk.KyDT, ttth.ThangTT) AS Ky, 
                ISNULL(dtk.DoanhThuKyCalc, 0) AS TongDoanhThuKy, 
                ISNULL(ttth.ThucThuThangCalc, 0) AS TongThucThuThang 
            FROM DoanhThuTheoKy dtk 
            FULL OUTER JOIN ThucThuTheoThang ttth ON dtk.KyDT = ttth.ThangTT 
            WHERE COALESCE(dtk.KyDT, ttth.ThangTT) IS NOT NULL 
            ORDER BY Ky;
        """

        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', full_query_ky)

        if df_result.empty:
            return pd.DataFrame(columns=['Ky', 'TongDoanhThuKy', 'TongThucThuThang', 'Tồn Thu', '% Đạt'])

        # Xử lý hậu kỳ
        df_result['Ky'] = pd.to_numeric(df_result['Ky'], errors='coerce').fillna(0).astype(int)
        df_result['TongDoanhThuKy'] = pd.to_numeric(df_result['TongDoanhThuKy'], errors='coerce').fillna(0)
        df_result['TongThucThuThang'] = pd.to_numeric(df_result['TongThucThuThang'], errors='coerce').fillna(0)

        df_result['Tồn Thu'] = df_result['TongDoanhThuKy'] - df_result['TongThucThuThang']
        df_result['% Đạt'] = np.where(
            df_result['TongDoanhThuKy'] != 0,
            (df_result['TongThucThuThang'] / df_result['TongDoanhThuKy']) * 100,
            0.0
        )

        logging.info(f"✅ Hoàn thành Phân tích theo Kỳ cho năm {selected_year}.")
        return df_result

    except Exception as e:
        logging.error(f"❌ Lỗi trong run_monthly_analysis_from_db: {e}", exc_info=True)
        raise


def run_daily_analysis_from_db(selected_year, selected_ky):
    """
    Lấy dữ liệu chi tiết theo từng Ngày của một Kỳ/Năm đã chọn.
    Tương đương với DailyDataQueryWorker.
    """
    logging.info(f"Bắt đầu Phân tích theo Ngày cho năm {selected_year}, kỳ {selected_ky}")

    try:
        # Câu lệnh SQL được chuyển thể từ DailyDataQueryWorker
        query = f"""
            WITH RelevantDaysInKy AS (
                SELECT DISTINCT CAST({config.PAYMENT_DATE_COLUMN} AS DATE) AS NgayKyRelevant 
                FROM {config.TABLE_SOURCE} H_KY
                WHERE 
                    YEAR(H_KY.{config.PAYMENT_DATE_COLUMN}) = {selected_year} 
                    AND MONTH(H_KY.{config.PAYMENT_DATE_COLUMN}) = {selected_ky} 
                    AND H_KY.{config.PERIOD_COLUMN} = {selected_ky}
            ), 
            DailyAggregates AS (
                SELECT 
                    CAST({config.PAYMENT_DATE_COLUMN} AS DATE) AS NgayGiaiAgg,
                    COUNT(DISTINCT {config.SOHOADON_COLUMN}) AS TotalInvoicesForDate,
                    SUM({config.ORIGINAL_SUM_COLUMN}) AS TotalCongForDate
                FROM {config.TABLE_SOURCE} 
                WHERE {config.ORIGINAL_SUM_COLUMN} IS NOT NULL
                    AND {config.SOHOADON_COLUMN} IS NOT NULL
                GROUP BY CAST({config.PAYMENT_DATE_COLUMN} AS DATE)
            )
            SELECT 
                rdk.NgayKyRelevant AS NgayGiaiNgan,
                ISNULL(da.TotalInvoicesForDate, 0) AS SoLuongHoaDon,
                ISNULL(da.TotalCongForDate, 0) AS TongCongNgay
            FROM RelevantDaysInKy rdk 
            LEFT JOIN DailyAggregates da ON rdk.NgayKyRelevant = da.NgayGiaiAgg 
            ORDER BY rdk.NgayKyRelevant;
        """

        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)

        if not df_result.empty:
            df_result['NgayGiaiNgan'] = pd.to_datetime(df_result['NgayGiaiNgan'], errors='coerce')

        logging.info(f"✅ Hoàn thành Phân tích theo Ngày cho năm {selected_year}, kỳ {selected_ky}.")
        return df_result

    except Exception as e:
        logging.error(f"❌ Lỗi trong run_daily_analysis_from_db: {e}", exc_info=True)
        raise

# ==============================================================================
# LOGIC CHO TAB 4: PHÂN TÍCH DOANH THU (CSDL)
# ==============================================================================
def run_yearly_revenue_analysis_from_db(start_year, end_year, den_ngay_giai_filter):
    logging.info(f"Bắt đầu Phân tích Doanh thu Năm (DB) cho {start_year}-{end_year}, đến ngày {den_ngay_giai_filter}")
    try:
        den_ngay_giai_str = den_ngay_giai_filter.strftime('%Y-%m-%d'); nhanvien_giai_column = 'NV_GIAI'; value_to_exclude_nv_giai = 'NKD'
        full_query = f"""
            WITH TermA_CTE AS (SELECT hd_a.{config.BILLING_YEAR_COLUMN} AS Nam_A, SUM(hd_a.{config.SUM_VALUE_COLUMN}) AS Sum_A_tongcong_bd FROM {config.TABLE_SOURCE} hd_a WHERE hd_a.{config.BILLING_YEAR_COLUMN} >= {start_year} AND hd_a.{config.BILLING_YEAR_COLUMN} <= {end_year} AND (hd_a.{nhanvien_giai_column} <> '{value_to_exclude_nv_giai}' OR hd_a.{nhanvien_giai_column} IS NULL) AND hd_a.{config.SUM_VALUE_COLUMN} IS NOT NULL GROUP BY hd_a.{config.BILLING_YEAR_COLUMN}),
            TermB_CTE AS (SELECT hd_b.{config.BILLING_YEAR_COLUMN} AS Nam_B, SUM(hd_b.{config.SUM_VALUE_COLUMN} - hd_b.{config.ORIGINAL_SUM_COLUMN}) AS Sum_B_adjustment FROM {config.TABLE_SOURCE} hd_b WHERE hd_b.{config.BILLING_YEAR_COLUMN} >= {start_year} AND hd_b.{config.BILLING_YEAR_COLUMN} <= {end_year} AND YEAR(hd_b.{config.PAYMENT_DATE_COLUMN}) = hd_b.{config.BILLING_YEAR_COLUMN} AND hd_b.{config.PAYMENT_DATE_COLUMN} IS NOT NULL AND CAST(hd_b.{config.PAYMENT_DATE_COLUMN} AS DATE) <= '{den_ngay_giai_str}' AND hd_b.{config.SUM_VALUE_COLUMN} IS NOT NULL AND hd_b.{config.ORIGINAL_SUM_COLUMN} IS NOT NULL GROUP BY hd_b.{config.BILLING_YEAR_COLUMN}),
            ThucThu_CTE AS (SELECT t.{config.BILLING_YEAR_COLUMN} AS Nam_TT, SUM(t.{config.ORIGINAL_SUM_COLUMN}) AS ActualThucThu FROM {config.TABLE_SOURCE} t WHERE t.{config.BILLING_YEAR_COLUMN} >= {start_year} AND t.{config.BILLING_YEAR_COLUMN} <= {end_year} AND t.{config.PAYMENT_DATE_COLUMN} IS NOT NULL AND CAST(t.{config.PAYMENT_DATE_COLUMN} AS DATE) <= '{den_ngay_giai_str}' AND t.{config.BILLING_YEAR_COLUMN} = YEAR(t.{config.PAYMENT_DATE_COLUMN}) AND (t.{nhanvien_giai_column} <> '{value_to_exclude_nv_giai}' OR t.{nhanvien_giai_column} IS NULL) AND t.{config.ORIGINAL_SUM_COLUMN} IS NOT NULL GROUP BY t.{config.BILLING_YEAR_COLUMN})
            SELECT a.Nam_A AS Nam, (ISNULL(a.Sum_A_tongcong_bd, 0) - ISNULL(b.Sum_B_adjustment, 0)) AS TongDoanhThu, ISNULL(tt.ActualThucThu, 0) AS TongThucThu FROM TermA_CTE a LEFT JOIN ThucThu_CTE tt ON a.Nam_A = tt.Nam_TT LEFT JOIN TermB_CTE b ON a.Nam_A = b.Nam_B WHERE a.Nam_A IS NOT NULL ORDER BY a.Nam_A;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', full_query)
        final_columns = ['Nam', 'TongDoanhThu', 'TongThucThu', 'Tồn Thu', '% Đạt']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        df_result['Nam'] = pd.to_numeric(df_result['Nam'], errors='coerce').fillna(0).astype(int)
        df_result['TongDoanhThu'] = pd.to_numeric(df_result['TongDoanhThu'], errors='coerce').fillna(0)
        df_result['TongThucThu'] = pd.to_numeric(df_result['TongThucThu'], errors='coerce').fillna(0)
        df_result['Tồn Thu'] = df_result['TongDoanhThu'] - df_result['TongThucThu']
        df_result['% Đạt'] = np.where(df_result['TongDoanhThu'] != 0, (df_result['TongThucThu'] / df_result['TongDoanhThu']) * 100, 0.0)
        for col in final_columns:
            if col not in df_result.columns: df_result[col] = 0
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_yearly_revenue_analysis_from_db: {e}", exc_info=True); raise

def run_monthly_analysis_from_db(selected_year):
    logging.info(f"Bắt đầu Phân tích theo Kỳ cho năm {selected_year}")
    try:
        full_query_ky = f"""
            WITH DoanhThuTheoKy AS (SELECT {config.PERIOD_COLUMN} AS KyDT, SUM({config.SUM_VALUE_COLUMN}) AS DoanhThuKyCalc FROM {config.TABLE_SOURCE} WHERE {config.BILLING_YEAR_COLUMN} = {selected_year} AND {config.PERIOD_COLUMN} IS NOT NULL AND {config.SUM_VALUE_COLUMN} IS NOT NULL GROUP BY {config.PERIOD_COLUMN}), 
            ThucThuTheoThang AS (SELECT MONTH({config.PAYMENT_DATE_COLUMN}) AS ThangTT, SUM({config.ORIGINAL_SUM_COLUMN}) AS ThucThuThangCalc FROM {config.TABLE_SOURCE} WHERE {config.BILLING_YEAR_COLUMN} = YEAR({config.PAYMENT_DATE_COLUMN}) AND {config.PERIOD_COLUMN} = MONTH({config.PAYMENT_DATE_COLUMN}) AND YEAR({config.PAYMENT_DATE_COLUMN}) = {selected_year} AND {config.ORIGINAL_SUM_COLUMN} IS NOT NULL GROUP BY MONTH({config.PAYMENT_DATE_COLUMN}))
            SELECT COALESCE(dtk.KyDT, ttth.ThangTT) AS Ky, ISNULL(dtk.DoanhThuKyCalc, 0) AS TongDoanhThuKy, ISNULL(ttth.ThucThuThangCalc, 0) AS TongThucThuThang FROM DoanhThuTheoKy dtk FULL OUTER JOIN ThucThuTheoThang ttth ON dtk.KyDT = ttth.ThangTT WHERE COALESCE(dtk.KyDT, ttth.ThangTT) IS NOT NULL ORDER BY Ky;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', full_query_ky)
        final_columns = ['Ky', 'TongDoanhThuKy', 'TongThucThuThang', 'Tồn Thu', '% Đạt']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        df_result['Ky'] = pd.to_numeric(df_result['Ky'], errors='coerce').fillna(0).astype(int)
        df_result['TongDoanhThuKy'] = pd.to_numeric(df_result['TongDoanhThuKy'], errors='coerce').fillna(0)
        df_result['TongThucThuThang'] = pd.to_numeric(df_result['TongThucThuThang'], errors='coerce').fillna(0)
        df_result['Tồn Thu'] = df_result['TongDoanhThuKy'] - df_result['TongThucThuThang']
        df_result['% Đạt'] = np.where(df_result['TongDoanhThuKy'] != 0, (df_result['TongThucThuThang'] / df_result['TongDoanhThuKy']) * 100, 0.0)
        for col in final_columns:
            if col not in df_result.columns: df_result[col] = 0
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_monthly_analysis_from_db: {e}", exc_info=True); raise

def run_daily_analysis_from_db(selected_year, selected_ky):
    logging.info(f"Bắt đầu Phân tích theo Ngày cho năm {selected_year}, kỳ {selected_ky}")
    try:
        query = f"""
            WITH RelevantDaysInKy AS (SELECT DISTINCT CAST({config.PAYMENT_DATE_COLUMN} AS DATE) AS NgayKyRelevant FROM {config.TABLE_SOURCE} H_KY WHERE YEAR(H_KY.{config.PAYMENT_DATE_COLUMN}) = {selected_year} AND MONTH(H_KY.{config.PAYMENT_DATE_COLUMN}) = {selected_ky} AND H_KY.{config.PERIOD_COLUMN} = {selected_ky}), 
            DailyAggregates AS (SELECT CAST({config.PAYMENT_DATE_COLUMN} AS DATE) AS NgayGiaiAgg, COUNT(DISTINCT {config.SOHOADON_COLUMN}) AS TotalInvoicesForDate, SUM({config.ORIGINAL_SUM_COLUMN}) AS TotalCongForDate FROM {config.TABLE_SOURCE} WHERE {config.ORIGINAL_SUM_COLUMN} IS NOT NULL AND {config.SOHOADON_COLUMN} IS NOT NULL GROUP BY CAST({config.PAYMENT_DATE_COLUMN} AS DATE))
            SELECT rdk.NgayKyRelevant AS NgayGiaiNgan, ISNULL(da.TotalInvoicesForDate, 0) AS SoLuongHoaDon, ISNULL(da.TotalCongForDate, 0) AS TongCongNgay FROM RelevantDaysInKy rdk LEFT JOIN DailyAggregates da ON rdk.NgayKyRelevant = da.NgayGiaiAgg ORDER BY rdk.NgayKyRelevant;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)
        final_columns = ['NgayGiaiNgan', 'SoLuongHoaDon', 'TongCongNgay']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        for col in final_columns:
            if col not in df_result.columns: df_result[col] = 0
        df_result['NgayGiaiNgan'] = pd.to_datetime(df_result['NgayGiaiNgan'], errors='coerce')
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_daily_analysis_from_db: {e}", exc_info=True); raise

# ==============================================================================
# LOGIC CHO TAB 5: PHÂN TÍCH HÓA ĐƠN NỢ (CSDL)
# ==============================================================================
def run_outstanding_by_year_analysis():
    logging.info("Bắt đầu Phân tích HĐ nợ theo Năm...")
    try:
        query = f"""
            SELECT {config.BILLING_YEAR_COLUMN} AS NamHoaDon, COUNT(DISTINCT {config.SOHOADON_COLUMN}) AS SoLuongHoaDonNo, SUM({config.SUM_VALUE_COLUMN}) AS TongCongNo
            FROM {config.TABLE_SOURCE} 
            WHERE {config.PAYMENT_DATE_COLUMN} IS NULL AND {config.SUM_VALUE_COLUMN} IS NOT NULL AND {config.SOHOADON_COLUMN} IS NOT NULL
            GROUP BY {config.BILLING_YEAR_COLUMN} ORDER BY {config.BILLING_YEAR_COLUMN} DESC;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)
        final_columns = ['NamHoaDon', 'SoLuongHoaDonNo', 'TongCongNo']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_outstanding_by_year_analysis: {e}", exc_info=True); raise

def run_outstanding_by_period_count_analysis():
    logging.info("Bắt đầu Phân tích HĐ nợ theo Số Kỳ Nợ...")
    try:
        query = f"""
            WITH DanhBaNoTheoSoKy AS (
                SELECT {config.INVOICE_ID_COLUMN} AS DanhBa_ID, COUNT(*) AS SoKyNoThucTe, SUM({config.ORIGINAL_SUM_COLUMN}) AS TongCongNoCuaDanhBa
                FROM {config.TABLE_SOURCE}
                WHERE {config.PAYMENT_DATE_COLUMN} IS NULL AND {config.ORIGINAL_SUM_COLUMN} IS NOT NULL AND {config.INVOICE_ID_COLUMN} IS NOT NULL
                GROUP BY {config.INVOICE_ID_COLUMN}
            )
            SELECT dbtns.SoKyNoThucTe AS KyNo, COUNT(dbtns.DanhBa_ID) AS SoLuongDanhBa, SUM(dbtns.TongCongNoCuaDanhBa) AS TongCongTheoKyNo
            FROM DanhBaNoTheoSoKy dbtns GROUP BY dbtns.SoKyNoThucTe ORDER BY dbtns.SoKyNoThucTe DESC;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)
        final_columns = ['KyNo', 'SoLuongDanhBa', 'TongCongTheoKyNo']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        return df_result[final_columns]
    except Exception as e:
        logging.error(f"❌ Lỗi trong run_outstanding_by_period_count_analysis: {e}", exc_info=True); raise

def fetch_outstanding_details_by_year(selected_year, page_number=1, page_size=100):
    logging.info(f"Đang tải chi tiết HĐ nợ cho năm {selected_year}, trang {page_number}, kích thước {page_size}...")
    try:
        offset = (page_number - 1) * page_size
        query = f"""
            WITH FilteredResults AS (
                SELECT {config.INVOICE_ID_COLUMN} AS DanhBa, TENKH, SO AS SoNha, DUONG AS Duong, {config.BILLING_YEAR_COLUMN} AS NamHD, {config.PERIOD_COLUMN} AS Ky, DOT, GB AS GiaBieu, {config.SUM_VALUE_COLUMN} AS TongCong
                FROM {config.TABLE_SOURCE} 
                WHERE {config.BILLING_YEAR_COLUMN} = {selected_year} AND {config.PAYMENT_DATE_COLUMN} IS NULL AND {config.SUM_VALUE_COLUMN} IS NOT NULL AND {config.INVOICE_ID_COLUMN} IS NOT NULL
            )
            SELECT *, COUNT(*) OVER() as TotalRows FROM FilteredResults ORDER BY DanhBa OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY;
        """
        df_page = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)
        total_rows = 0
        final_columns = ['DanhBa', 'TENKH', 'SoNha', 'Duong', 'NamHD', 'Ky', 'DOT', 'GiaBieu', 'TongCong']
        if not df_page.empty:
            total_rows = df_page['TotalRows'].iloc[0]
            df_page = df_page[final_columns]
            df_page['DanhBa'] = df_page['DanhBa'].astype(str).str.zfill(11)
        else:
            df_page = pd.DataFrame(columns=final_columns)
        return df_page, total_rows
    except Exception as e:
        logging.error(f"❌ Lỗi trong fetch_outstanding_details_by_year (paginated): {e}", exc_info=True); raise


def fetch_outstanding_customers_by_period_count(operator, value):
    """
    Lấy danh sách các danh bạ nợ dựa trên điều kiện so sánh số kỳ.
    """
    logging.info(f"Đang tải chi tiết các DB nợ có số kỳ {operator} {value}...")

    # Kiểm tra để đảm bảo toán tử là hợp lệ, tránh SQL Injection
    valid_operators = ['=', '>', '<', '>=', '<=']
    if operator not in valid_operators:
        raise ValueError("Toán tử so sánh không hợp lệ.")

    try:
        latest_criteria_column_sql = 'Ngay_NhanHD'
        # Câu lệnh SQL được cập nhật để nhận toán tử động
        query = f"""
            WITH DanhBaNoCounts AS (
                SELECT {config.INVOICE_ID_COLUMN} AS DanhBa_ID, COUNT(*) AS SoKyNoThucTe_Agg, SUM({config.ORIGINAL_SUM_COLUMN}) AS TongCongNoCuaDanhBa_Agg
                FROM {config.TABLE_SOURCE}
                WHERE {config.PAYMENT_DATE_COLUMN} IS NULL AND {config.ORIGINAL_SUM_COLUMN} IS NOT NULL AND {config.INVOICE_ID_COLUMN} IS NOT NULL
                GROUP BY {config.INVOICE_ID_COLUMN}
            ),
            FilteredDanhBa AS (
                SELECT DanhBa_ID, SoKyNoThucTe_Agg, TongCongNoCuaDanhBa_Agg FROM DanhBaNoCounts 
                WHERE SoKyNoThucTe_Agg {operator} {value}  -- <<< THAY ĐỔI QUAN TRỌNG Ở ĐÂY
            ),
            RankedInvoices AS (
                SELECT hd.{config.INVOICE_ID_COLUMN} AS DanhBa_ID_RI, hd.TenKH, hd.SO AS SoNha, hd.DUONG AS Duong, hd.DOT, hd.GB,
                ROW_NUMBER() OVER(PARTITION BY hd.{config.INVOICE_ID_COLUMN} ORDER BY hd.{latest_criteria_column_sql} DESC) as rn
                FROM {config.TABLE_SOURCE} hd
                WHERE hd.{config.PAYMENT_DATE_COLUMN} IS NULL AND hd.{config.INVOICE_ID_COLUMN} IN (SELECT f.DanhBa_ID FROM FilteredDanhBa f) 
            )
            SELECT
                fdb.DanhBa_ID AS DanhBa, COALESCE(ri.TenKH, '') AS TenKH, COALESCE(ri.SoNha, '') AS SoNha,
                COALESCE(ri.Duong, '') AS Duong, fdb.SoKyNoThucTe_Agg AS SoKyNoThucTe, 
                fdb.TongCongNoCuaDanhBa_Agg AS TongCongNoCuaDanhBa, COALESCE(ri.DOT, '') AS DOT,
                COALESCE(ri.GB, '') AS GB
            FROM FilteredDanhBa fdb LEFT JOIN RankedInvoices ri ON fdb.DanhBa_ID = ri.DanhBa_ID_RI AND ri.rn = 1 
            ORDER BY fdb.DanhBa_ID;
        """
        df_result = data_sources.fetch_dataframe('f_Select_SQL_Thutien', query)

        final_columns = ['DanhBa', 'TenKH', 'SoNha', 'Duong', 'SoKyNoThucTe', 'TongCongNoCuaDanhBa', 'DOT', 'GB']
        if df_result.empty: return pd.DataFrame(columns=final_columns)
        for col in final_columns:
            if col not in df_result.columns:
                if col in ['SoKyNoThucTe']:
                    df_result[col] = 0
                elif col in ['TongCongNoCuaDanhBa']:
                    df_result[col] = 0.0
                else:
                    df_result[col] = ''
        df_result = df_result[final_columns]
        df_result['DanhBa'] = df_result['DanhBa'].astype(str).str.zfill(11)
        return df_result
    except Exception as e:
        logging.error(f"❌ Lỗi trong fetch_outstanding_customers_by_period_count: {e}", exc_info=True)
        raise
