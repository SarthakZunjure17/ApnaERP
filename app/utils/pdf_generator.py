import datetime
from io import BytesIO
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


def generate_payslip_pdf_bytes(
    *,
    payslip_number: str,
    employee_code: str,
    employee_name: str,
    department_name: str,
    work_email: str,
    period_code: str,
    period_start: datetime.date,
    period_end: datetime.date,
    gross_salary: float,
    total_earnings: float,
    total_deductions: float,
    net_salary: float,
    components: List[dict],
    generated_at: Optional[datetime.datetime] = None,
) -> bytes:
    """
    Generates a professional PDF Payslip document in bytes using ReportLab.

    :param components: List of dicts with keys: 'name', 'type' ('Earning'/'Deduction'), 'amount'
    :return: Raw PDF binary content in bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    header_title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=0,
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
    )
    cell_bold_style = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    cell_normal_style = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )

    gen_time_str = (generated_at or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Company Header
    story.append(Paragraph("ApnaERP Enterprise", header_title_style))
    story.append(Paragraph("Official Employee Payslip Statement", subtitle_style))
    story.append(Spacer(1, 15))

    # 2. Employee & Period Info Box
    info_data = [
        [
            Paragraph("<b>Payslip Number:</b>", cell_bold_style),
            Paragraph(payslip_number, cell_normal_style),
            Paragraph("<b>Period Code:</b>", cell_bold_style),
            Paragraph(period_code, cell_normal_style),
        ],
        [
            Paragraph("<b>Employee Code:</b>", cell_bold_style),
            Paragraph(employee_code, cell_normal_style),
            Paragraph("<b>Period Dates:</b>", cell_bold_style),
            Paragraph(f"{period_start} to {period_end}", cell_normal_style),
        ],
        [
            Paragraph("<b>Employee Name:</b>", cell_bold_style),
            Paragraph(employee_name, cell_normal_style),
            Paragraph("<b>Department:</b>", cell_bold_style),
            Paragraph(department_name or "N/A", cell_normal_style),
        ],
        [
            Paragraph("<b>Work Email:</b>", cell_bold_style),
            Paragraph(work_email or "N/A", cell_normal_style),
            Paragraph("<b>Generated At:</b>", cell_bold_style),
            Paragraph(gen_time_str, cell_normal_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[100, 170, 100, 170])
    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 20))

    # 3. Itemized Salary Components Breakdown (Earnings vs Deductions)
    story.append(Paragraph("Salary Components Breakdown", section_heading_style))
    story.append(Spacer(1, 8))

    earnings = [c for c in components if c.get("type") == "Earning"]
    deductions = [c for c in components if c.get("type") == "Deduction"]

    comp_table_data = [
        [
            Paragraph("<b>Earnings Component</b>", cell_bold_style),
            Paragraph("<b>Amount (INR)</b>", cell_bold_style),
            Paragraph("<b>Deductions Component</b>", cell_bold_style),
            Paragraph("<b>Amount (INR)</b>", cell_bold_style),
        ]
    ]

    max_rows = max(len(earnings), len(deductions), 1)
    for i in range(max_rows):
        e_name = earnings[i]["name"] if i < len(earnings) else ""
        e_amt = f"₹ {earnings[i]['amount']:,.2f}" if i < len(earnings) else ""
        d_name = deductions[i]["name"] if i < len(deductions) else ""
        d_amt = f"₹ {deductions[i]['amount']:,.2f}" if i < len(deductions) else ""

        comp_table_data.append([
            Paragraph(e_name, cell_normal_style),
            Paragraph(e_amt, cell_normal_style),
            Paragraph(d_name, cell_normal_style),
            Paragraph(d_amt, cell_normal_style),
        ])

    comp_table = Table(comp_table_data, colWidths=[170, 100, 170, 100])
    comp_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(comp_table)
    story.append(Spacer(1, 20))

    # 4. Summary Totals Box
    story.append(Paragraph("Salary Summary", section_heading_style))
    story.append(Spacer(1, 8))

    summary_data = [
        [
            Paragraph("<b>Gross Salary:</b>", cell_bold_style),
            Paragraph(f"₹ {gross_salary:,.2f}", cell_normal_style),
            Paragraph("<b>Total Deductions:</b>", cell_bold_style),
            Paragraph(f"₹ {total_deductions:,.2f}", cell_normal_style),
        ],
        [
            Paragraph("<b>Total Earnings:</b>", cell_bold_style),
            Paragraph(f"₹ {total_earnings:,.2f}", cell_normal_style),
            Paragraph("<b>Net Payable Salary:</b>", ParagraphStyle("NetBold", parent=cell_bold_style, fontSize=11, textColor=colors.HexColor("#047857"))),
            Paragraph(f"<b>₹ {net_salary:,.2f}</b>", ParagraphStyle("NetVal", parent=cell_normal_style, fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#047857"))),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[120, 150, 120, 150])
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bbf7d0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcfce7")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 30))

    # 5. Footer Disclaimer
    footer_text = Paragraph(
        "<i>This is a computer-generated document and requires no physical signature. Confidential - ApnaERP Enterprise System.</i>",
        subtitle_style,
    )
    story.append(footer_text)

    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    return pdf_content
