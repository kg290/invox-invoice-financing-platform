"""
Invoice PDF generator using ReportLab.
Generates a GST-compliant invoice PDF and returns the bytes.
"""
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

RUPEE = "Rs."


def generate_invoice_pdf(invoice, vendor, items) -> bytes:
    """Generate a professional GST invoice PDF. Returns raw PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18,
                                 textColor=colors.HexColor("#1e40af"), alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9,
                                    textColor=colors.gray, alignment=TA_CENTER)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading3"], fontSize=11,
                                   textColor=colors.HexColor("#1e3a5f"), spaceAfter=4)
    normal = styles["Normal"]
    bold = ParagraphStyle("Bold", parent=normal, fontName="Helvetica-Bold")
    small = ParagraphStyle("Small", parent=normal, fontSize=8)
    right_bold = ParagraphStyle("RBold", parent=bold, alignment=TA_RIGHT, fontSize=12)

    elements = []

    # ── Header ──
    elements.append(Paragraph("TAX INVOICE", title_style))
    elements.append(Paragraph("InvoX — Embedded Invoice Financing Platform", subtitle_style))
    elements.append(Spacer(1, 6 * mm))

    # ── Invoice Info ──
    info_data = [
        [Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}", normal),
         Paragraph(f"<b>Date:</b> {invoice.invoice_date}", normal)],
        [Paragraph(f"<b>Supply Type:</b> {'Intra-State' if invoice.supply_type == 'intra_state' else 'Inter-State'}", normal),
         Paragraph(f"<b>Due Date:</b> {invoice.due_date}", normal)],
        [Paragraph(f"<b>Place of Supply:</b> {invoice.place_of_supply} ({invoice.place_of_supply_code})", normal),
         Paragraph(f"<b>Reverse Charge:</b> {'Yes' if invoice.reverse_charge else 'No'}", normal)],
    ]
    info_table = Table(info_data, colWidths=[90 * mm, 90 * mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Seller / Buyer ──
    seller_buyer = [
        [Paragraph("<b>Seller (Supplier)</b>", heading_style),
         Paragraph("<b>Buyer</b>", heading_style)],
        [Paragraph(f"{vendor.business_name}<br/>"
                   f"GSTIN: {vendor.gstin}<br/>"
                   f"{vendor.business_address}<br/>"
                   f"{vendor.business_city}, {vendor.business_state} - {vendor.business_pincode}<br/>"
                   f"State Code: {vendor.gstin[:2]}", small),
         Paragraph(f"{invoice.buyer_name}<br/>"
                   f"GSTIN: {invoice.buyer_gstin or 'B2C (Unregistered)'}<br/>"
                   f"{invoice.buyer_address}<br/>"
                   f"{invoice.buyer_city}, {invoice.buyer_state} - {invoice.buyer_pincode}<br/>"
                   f"State Code: {invoice.buyer_state_code}", small)],
    ]
    sb_table = Table(seller_buyer, colWidths=[90 * mm, 90 * mm])
    sb_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(sb_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Line Items ──
    is_intra = invoice.supply_type == "intra_state"
    if is_intra:
        header = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable", "CGST", "SGST", "Total"]
    else:
        header = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable", "IGST", "Total"]

    rows = [header]
    for idx, item in enumerate(items, 1):
        if is_intra:
            rows.append([
                str(idx), item.description, item.hsn_sac_code,
                f"{item.quantity} {item.unit}", f"{RUPEE}{item.unit_price:,.2f}",
                f"{RUPEE}{item.taxable_value:,.2f}",
                f"{RUPEE}{item.cgst_amount:,.2f} ({item.gst_rate / 2}%)",
                f"{RUPEE}{item.sgst_amount:,.2f} ({item.gst_rate / 2}%)",
                f"{RUPEE}{item.total_amount:,.2f}",
            ])
        else:
            rows.append([
                str(idx), item.description, item.hsn_sac_code,
                f"{item.quantity} {item.unit}", f"{RUPEE}{item.unit_price:,.2f}",
                f"{RUPEE}{item.taxable_value:,.2f}",
                f"{RUPEE}{item.igst_amount:,.2f} ({item.gst_rate}%)",
                f"{RUPEE}{item.total_amount:,.2f}",
            ])

    if is_intra:
        col_widths = [8 * mm, 40 * mm, 18 * mm, 18 * mm, 20 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm]
    else:
        col_widths = [8 * mm, 48 * mm, 20 * mm, 20 * mm, 22 * mm, 24 * mm, 24 * mm, 24 * mm]

    items_table = Table(rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Summary ──
    summary_rows = [
        ["Sub Total", f"{RUPEE}{invoice.subtotal:,.2f}"],
    ]
    if invoice.total_discount > 0:
        summary_rows.append(["Discount", f"-{RUPEE}{invoice.total_discount:,.2f}"])
    if is_intra:
        summary_rows.append(["Total CGST", f"{RUPEE}{invoice.total_cgst:,.2f}"])
        summary_rows.append(["Total SGST", f"{RUPEE}{invoice.total_sgst:,.2f}"])
    else:
        summary_rows.append(["Total IGST", f"{RUPEE}{invoice.total_igst:,.2f}"])
    if invoice.total_cess > 0:
        summary_rows.append(["Cess", f"{RUPEE}{invoice.total_cess:,.2f}"])
    if invoice.round_off != 0:
        summary_rows.append(["Round Off", f"{RUPEE}{invoice.round_off:,.2f}"])
    summary_rows.append(["GRAND TOTAL", f"{RUPEE}{invoice.grand_total:,.2f}"])

    summary_table = Table(summary_rows, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1e40af")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Blockchain Hash ──
    if invoice.blockchain_hash:
        elements.append(Paragraph("<b>Blockchain Proof</b>", heading_style))
        elements.append(Paragraph(
            f"Block Hash: <font face='Courier' size='7'>{invoice.blockchain_hash}</font><br/>"
            f"Block Index: #{invoice.block_index}",
            small
        ))
        elements.append(Spacer(1, 4 * mm))

    # ── Terms ──
    if invoice.terms:
        elements.append(Paragraph("<b>Terms & Conditions</b>", heading_style))
        elements.append(Paragraph(invoice.terms, small))
    if invoice.notes:
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph("<b>Notes:</b> " + invoice.notes, small))

    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("This is a computer-generated invoice. No signature required.", subtitle_style))
    elements.append(Paragraph(f"Generated by InvoX Platform | Blockchain-Verified", subtitle_style))

    doc.build(elements)
    return buf.getvalue()
