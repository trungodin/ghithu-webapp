# GhithuWebApp/backend/analysis_logic.py

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

# ==============================================================================
# LOGIC CHO DASHBOARD
# ==============================================================================
def fetch_dashboard_data():
    """
    Lấy và xử lý dữ liệu cho dashboard.
    Tương đương với DashboardWorker.
    """
    try:
        logging.info("Bắt đầu lấy dữ liệu cho Dashboard...")

        sql_hoadon = "SELECT DANHBA, TONGCONG, NAM, KY, SOHOADON FROM HoaDon WHERE NGAYGIAI IS NULL"
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

        if df_merged.empty:
            logging.warning("Không có dữ liệu nợ tồn nào sau khi xử lý.")
            return {}

        sohoadon_list = df_merged['SOHOADON'].dropna().unique().tolist()
        if sohoadon_list:
            df_bgw = data_sources._get_bgw_invoices(sohoadon_list)
            if not df_bgw.empty:
                shdon_to_exclude = df_bgw['SHDon'].astype(str).str.strip().unique()
                df_merged = df_merged[~df_merged['SOHOADON'].astype(str).str.strip().isin(shdon_to_exclude)]

        if df_merged.empty:
            logging.warning("Không còn dữ liệu nợ tồn sau khi đối soát BGW.")
            return {}

        df_merged['TONGCONG'] = pd.to_numeric(df_merged['TONGCONG'], errors='coerce').fillna(0)

        total_debt = df_merged['TONGCONG'].sum()
        total_debtors = df_merged['DANHBA'].nunique()
        debtor_counts = df_merged.groupby('DANHBA').size()
        debtors_over_3_periods = (debtor_counts >= 3).sum()

        debt_by_gb = df_merged.groupby('GB')['TONGCONG'].sum().sort_values(ascending=False).head(10)

        df_merged['KY_NAM_DT'] = pd.to_datetime(
            df_merged['NAM'].astype(str) + '-' + df_merged['KY'].astype(str).str.zfill(2) + '-01', errors='coerce')
        debt_over_time = df_merged.groupby(pd.Grouper(key='KY_NAM_DT', freq='M'))['TONGCONG'].sum()
        debt_over_time = debt_over_time[debt_over_time.index.year >= date.today().year - 2]

        results = {
            'total_debt': total_debt,
            'total_debtors': total_debtors,
            'debtors_over_3_periods': debtors_over_3_periods,
            'debt_by_gb': debt_by_gb,
            'debt_over_time': debt_over_time,
        }
        logging.info("✅ Hoàn thành lấy dữ liệu Dashboard.")
        return results

    except Exception as e:
        logging.error(f"❌ Lỗi trong fetch_dashboard_data: {e}", exc_info=True)
        raise

# ==============================================================================
# LOGIC CHO BÁO CÁO TUẦN
# ==============================================================================
# Các hàm con cho báo cáo tuần
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
        'Tình Trạng Nợ': ('Tình Trạng Nợ', 'first'), 'Ngày TT': ('NGAYGIAI_DT', 'max')}
    final_df = processed_df.groupby(config.DB_COL_DANH_BO).agg(**agg_funcs).reset_index()
    final_df['Ngày TT'] = final_df['Ngày TT'].dt.strftime('%d/%m/%Y').fillna('')
    final_df = final_df.rename(columns={config.DB_COL_DANH_BO: 'Danh bạ'})
    display_order = ['Danh bạ', 'Tên KH', 'Tình Trạng Nợ', 'Ngày TT', 'KỲ chưa TT', 'Số nhà', 'Đường',
                     'Tổng kỳ', 'Tổng tiền', 'Kỳ năm', 'GB', 'Đợt', 'Hộp']
    return final_df[[col for col in display_order if col in final_df.columns]]

def _report_build_stats(processed_df, on_off_df, start_date_str, end_date_str, selected_group):
    start_date = pd.to_datetime(start_date_str, dayfirst=True).date()
    end_date = pd.to_datetime(end_date_str, dayfirst=True).date()
    ids_da_giao = processed_df[config.DB_COL_ID].dropna().unique().tolist()
    on_off_subset_df = on_off_df[on_off_df[config.ON_OFF_COL_ID].isin(ids_da_giao)].copy()
    khoa_df = on_off_subset_df.dropna(subset=[f'{config.ON_OFF_COL_NGAY_KHOA}_chuan_hoa']).copy()
    khoa_df['Ngày'] = khoa_df[f'{config.ON_OFF_COL_NGAY_KHOA}_chuan_hoa'].dt.date
    khoa_df = khoa_df[(khoa_df['Ngày'] >= start_date) & (khoa_df['Ngày'] <= end_date)]
    bang_khoa = pd.DataFrame(columns=['Ngày', config.ON_OFF_COL_NHOM_KHOA, 'Số Lượng Khóa'])
    if not khoa_df.empty:
        bang_khoa = khoa_df.groupby(['Ngày', config.ON_OFF_COL_NHOM_KHOA]).size().reset_index(name='Số Lượng Khóa')
    source_mo_df = on_off_df.copy()
    if selected_group != "Tất cả các nhóm":
        source_mo_df = source_mo_df[source_mo_df[config.ON_OFF_COL_NHOM_KHOA] == selected_group]
    mo_df = source_mo_df.dropna(subset=[f'{config.ON_OFF_COL_NGAY_MO}_chuan_hoa']).copy()
    mo_df['Ngày'] = mo_df[f'{config.ON_OFF_COL_NGAY_MO}_chuan_hoa'].dt.date
    mo_df = mo_df[(mo_df['Ngày'] >= start_date) & (mo_df['Ngày'] <= end_date)]
    bang_mo = pd.DataFrame(columns=['Ngày', config.ON_OFF_COL_NHOM_KHOA, 'Số Lượng Mở'])
    if not mo_df.empty:
        bang_mo = mo_df.groupby(['Ngày', config.ON_OFF_COL_NHOM_KHOA]).size().reset_index(name='Số Lượng Mở')
    payments_df = processed_df[
        (processed_df['Tình Trạng Nợ'] == 'Đã Thanh Toán') & (processed_df['NGAYGIAI_DT'].notna())].copy()
    payments_df['Ngày'] = payments_df['NGAYGIAI_DT'].dt.date
    payments_df = payments_df[(payments_df['Ngày'] >= start_date) & (payments_df['Ngày'] <= end_date)]
    payments_summary = pd.DataFrame(columns=['Ngày', config.ON_OFF_COL_NHOM_KHOA, 'Thanh toán ngày'])
    if not payments_df.empty:
        payments_summary = payments_df.groupby(['Ngày', config.DB_COL_NHOM]).agg(
            count_col=(config.DB_COL_DANH_BO, 'nunique')
        ).reset_index().rename(columns={
            'count_col': 'Thanh toán ngày', config.DB_COL_NHOM: config.ON_OFF_COL_NHOM_KHOA})
    bang_thong_ke = pd.merge(bang_khoa, bang_mo, on=['Ngày', config.ON_OFF_COL_NHOM_KHOA], how='outer')
    bang_thong_ke = pd.merge(bang_thong_ke, payments_summary, on=['Ngày', config.ON_OFF_COL_NHOM_KHOA],
                             how='outer').fillna(0)
    if not bang_thong_ke.empty:
        for col in ['Số Lượng Khóa', 'Số Lượng Mở', 'Thanh toán ngày']:
            if col in bang_thong_ke.columns: bang_thong_ke[col] = bang_thong_ke[col].astype(int)
        total_khoa = bang_thong_ke['Số Lượng Khóa'].sum()
        total_mo = bang_thong_ke['Số Lượng Mở'].sum()
        total_thanh_toan = bang_thong_ke['Thanh toán ngày'].sum()
        total_row = pd.DataFrame([{'Ngày': 'Tổng cộng', config.ON_OFF_COL_NHOM_KHOA: '',
                                   'Số Lượng Khóa': total_khoa, 'Số Lượng Mở': total_mo,
                                   'Thanh toán ngày': total_thanh_toan}])
        bang_thong_ke = bang_thong_ke.sort_values(by=['Ngày'])
        bang_thong_ke = pd.concat([bang_thong_ke, total_row], ignore_index=True)
        bang_thong_ke = bang_thong_ke.rename(columns={config.ON_OFF_COL_NHOM_KHOA: 'Nhóm'})
        if 'Ngày' in bang_thong_ke.columns:
            bang_thong_ke['Ngày'] = bang_thong_ke['Ngày'].apply(
                lambda x: x.strftime('%d/%m/%Y') if isinstance(x, date) else x)
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
# LOGIC CHO LỌC DỮ LIỆU TỒN
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