# GhithuWebApp/backend/pdf_generator.py

import traceback
from datetime import datetime
from weasyprint import HTML
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def resource_path(relative_path):
    """ Lấy đường dẫn tuyệt đối đến tài nguyên """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)

def _build_html_content(report_data):
    """Xây dựng chuỗi HTML cho báo cáo."""
    start_date = report_data.get('start_date_str', '')
    end_date = report_data.get('end_date_str', '')
    selected_group = report_data.get('selected_group', '')
    tables = report_data.get('tables', {})

    date_line_html = ""
    if start_date and end_date:
        if start_date == end_date:
            title_date_str_display = f"Ngày giao : {start_date}"
        else:
            title_date_str_display = f"Thời gian giao: {start_date} đến {end_date}"
    else:
        title_date_str_display = "Không có thông tin ngày"

    staff_list = config.STAFF_MAP.get(selected_group)
    staff_names_header = ", ".join(staff_list) if staff_list else "Tổng hợp"

    html_string = f"""
        <table class="header-table">
            <tr>
                <td>
                    CÔNG TY CỔ PHẦN CẤP NƯỚC BẾN THÀNH<br/>
                    <b>ĐỘI QUẢN LÝ GHI THU NƯỚC</b>
                    <div class="header-line"></div>
                </td>
                <td>
                    CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br/>
                    <b>Độc lập - Tự do - Hạnh phúc</b>
                    <div class="header-line"></div>
                </td>
            </tr>
        </table>
        <p class="report-date">
            Thành phố Hồ Chí Minh, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}
        </p>
        <div class="report-title-block">
            <h1>BÁO CÁO CÔNG TÁC TUẦN</h1>
            <p>{title_date_str_display}</p>
            <p>Nhân viên : {staff_names_header}</p>
        </div>
    """

    for title, df in tables.items():
        if not df.empty:
            df = df.copy()

            # Xử lý chung cho các bảng
            if 'Tổng cộng' in df.iloc[:, 0].values:
                df = df.astype(str)
                total_row_index = df[df.iloc[:, 0] == 'Tổng cộng'].index[0]
                df.loc[total_row_index] = df.loc[total_row_index].apply(lambda x: f"<b>{x}</b>")

            table_html = ""

            # === THAY ĐỔI LOGIC TẠI ĐÂY ===
            # Nếu là Bảng thống kê chi tiết, chúng ta sẽ thêm style trực tiếp
            if title == 'BẢNG THỐNG KÊ CHI TIẾT:':
                # Chuyển DataFrame thành HTML mà không có thẻ table
                # để chúng ta có thể chèn <colgroup> vào
                table_body_html = df.to_html(index=False, header=True, classes='data-table', border=0, escape=False)

                # Bỏ thẻ <table> và </table> từ chuỗi HTML được tạo ra
                table_body_html = table_body_html.replace('<table border="0" class="data-table">', '')
                table_body_html = table_body_html.replace('</table>', '')

                # Tạo HTML hoàn chỉnh với <colgroup> để định nghĩa độ rộng
                table_html = f"""
                        <table class="data-table" style="table-layout: fixed; width: 100%;">
                            <colgroup>
                                <col style="width: 25%;">
                                <col style="width: 15%;">
                                <col style="width: 15%;">
                                <col style="width: 15%;">
                                <col style="width: 15%;">
                                <col style="width: 15%;">
                            </colgroup>
                            {table_body_html}
                        </table>
                        """
            else:  # Đối với các bảng khác, giữ nguyên cách làm cũ
                table_html = df.to_html(index=False, classes='data-table', border=0, escape=False)

            # ==============================

            html_string += f'<p class="table-title">{title}</p>'
            html_string += table_html

    if staff_list and len(staff_list) == 2:
        html_string += f"""
        <table class="signature-table">
            <tr>
                <td><span class="role">NHÂN VIÊN</span><span class="name">{staff_list[0]}</span></td>
                <td><span class="role">NHÂN VIÊN</span><span class="name">{staff_list[1]}</span></td>
            </tr>
        </table>
        """

    return html_string


def create_pdf_report(report_data):
    """
    Tạo báo cáo PDF bằng WeasyPrint từ dữ liệu và trả về dưới dạng bytes.
    """
    try:
        css_file_path = resource_path('report_style.css')

        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_styles = f.read()

        html_body_content = _build_html_content(report_data)
        html_content = f"""
        <html>
            <head>
                <meta charset='UTF-8'>
                <style>{css_styles}</style>
            </head>
            <body>
                {html_body_content}
            </body>
        </html>
        """

        base_url_path = resource_path('.')
        html_obj = HTML(string=html_content, base_url=base_url_path)

        # Ghi ra bytes thay vì file
        pdf_bytes = html_obj.write_pdf()
        return True, pdf_bytes

    except Exception as e:
        error_details = f"Lỗi không xác định khi tạo PDF: {e}\n\nTraceback:\n{traceback.format_exc()}"
        return False, error_details


def create_detailed_list_pdf(report_title, df_details):
    """
    Tạo báo cáo PDF dạng danh sách chi tiết theo một DataFrame cho trước.
    """
    try:
        css_file_path = resource_path('report_style.css')
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_styles = f.read()

        table_html = df_details.to_html(index=False, classes='data-table', border=0, escape=False)

        # === THAY ĐỔI TẠI ĐÂY: Thêm style nội tuyến cho đường kẻ ===
        html_content = f"""
        <html>
            <head>
                <meta charset='UTF-8'>
                <style>
                    {css_styles}
                    @page {{
                        size: A4 landscape;
                        margin: 1cm;
                    }}
                    .list-title {{
                        text-align: center;
                        font-size: 14pt;
                        font-weight: bold;
                        margin: 0.5cm 0;
                    }}
                    .data-table td {{
                        word-break: break-word;
                    }}
                </style>
            </head>
            <body>
                <table class="header-table">
                    <tr>
                        <td>
                            CÔNG TY CỔ PHẦN CẤP NƯỚC BẾN THÀNH<br/>
                            <b>ĐỘI QUẢN LÝ GHI THU NƯỚC</b>
                            <div class="header-line" style="width: 30%; margin: 2px auto 0;"></div>
                        </td>
                        <td>
                            CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br/>
                            <b>Độc lập - Tự do - Hạnh phúc</b>
                            <div class="header-line" style="width: 30%; margin: 2px auto 0;"></div>
                        </td>
                    </tr>
                </table>
                <p class="report-date">
                    Thành phố Hồ Chí Minh, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}
                </p>
                <div class="list-title">
                    {report_title}
                </div>

                <table class="data-table" style="table-layout: fixed; width: 100%;">
                    <colgroup>
                        <col style="width: 4%;">   <col style="width: 8%;">   <col style="width: 12%;">  <col style="width: 7%;">   <col style="width: 11%;">  <col style="width: 5%;">   <col style="width: 8%;">   <col style="width: 10%;">  <col style="width: 4%;">   <col style="width: 4%;">   <col style="width: 4%;">   <col style="width: 23%;">  </colgroup>
                    {table_html.replace('<table border="0" class="data-table">', '').replace('</table>', '')}
                </table>

            </body>
        </html>
        """
        # ========================================================

        base_url_path = resource_path('.')
        html_obj = HTML(string=html_content, base_url=base_url_path)
        return True, html_obj.write_pdf()

    except Exception as e:
        error_details = f"Lỗi không xác định khi tạo PDF chi tiết: {e}\n\nTraceback:\n{traceback.format_exc()}"
        return False, error_details
