"""
Smart Contract PDF generator.
Generates a comprehensive settlement contract PDF with all transaction details.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY


def generate_smart_contract_pdf(
    listing,
    invoice,
    vendor,
    lender,
    items,
    repayments,
    blockchain_blocks=None,
) -> bytes:
    """
    Generate a comprehensive Smart Contract PDF documenting the entire
    financing lifecycle: listing, funding, repayments, and settlement.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ContractTitle", parent=styles["Heading1"], fontSize=22,
        textColor=colors.HexColor("#1e3a5f"), alignment=TA_CENTER,
        spaceAfter=2 * mm, fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "ContractSubtitle", parent=styles["Normal"], fontSize=10,
        textColor=colors.HexColor("#64748b"), alignment=TA_CENTER, spaceAfter=4 * mm,
    )
    section_style = ParagraphStyle(
        "SectionHead", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#1e40af"), spaceBefore=6 * mm, spaceAfter=3 * mm,
        borderPadding=(0, 0, 2, 0), fontName="Helvetica-Bold",
    )
    subsection_style = ParagraphStyle(
        "SubSection", parent=styles["Heading3"], fontSize=10,
        textColor=colors.HexColor("#334155"), spaceBefore=3 * mm, spaceAfter=2 * mm,
        fontName="Helvetica-Bold",
    )
    normal = ParagraphStyle("ContractNormal", parent=styles["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("ContractSmall", parent=styles["Normal"], fontSize=8, leading=11)
    bold = ParagraphStyle("ContractBold", parent=normal, fontName="Helvetica-Bold")
    mono = ParagraphStyle("ContractMono", parent=small, fontName="Courier", fontSize=7)
    body = ParagraphStyle("ContractBody", parent=normal, alignment=TA_JUSTIFY, leading=14)
    right_bold = ParagraphStyle("RB", parent=bold, alignment=TA_RIGHT, fontSize=11)
    center_small = ParagraphStyle("CS", parent=small, alignment=TA_CENTER, textColor=colors.gray)

    elements = []

    # ══════════════════════════════════════════
    #  HEADER & TITLE
    # ══════════════════════════════════════════
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af")))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("SMART CONTRACT", title_style))
    elements.append(Paragraph("Invoice Financing Settlement Agreement", subtitle_style))
    elements.append(Paragraph(
        f"Contract ID: SC-{listing.id:04d}-{invoice.invoice_number} &nbsp;|&nbsp; "
        f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}",
        center_small,
    ))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af")))
    elements.append(Spacer(1, 4 * mm))

    # Status banner
    status_label = listing.listing_status.upper()
    status_color = "#22c55e" if listing.listing_status == "settled" else (
        "#3b82f6" if listing.listing_status == "funded" else "#f59e0b"
    )
    elements.append(Paragraph(
        f'<font color="{status_color}" size="12"><b>● CONTRACT STATUS: {status_label}</b></font>',
        ParagraphStyle("StatusBanner", parent=bold, alignment=TA_CENTER, spaceBefore=2 * mm, spaceAfter=4 * mm),
    ))

    # ══════════════════════════════════════════
    #  1. PARTIES INVOLVED
    # ══════════════════════════════════════════
    elements.append(Paragraph("1. PARTIES INVOLVED", section_style))

    parties_data = [
        [Paragraph("<b>VENDOR (Borrower)</b>", bold), Paragraph("<b>LENDER (Investor)</b>", bold)],
        [
            Paragraph(
                f"<b>Name:</b> {vendor.full_name}<br/>"
                f"<b>Business:</b> {vendor.business_name}<br/>"
                f"<b>Type:</b> {vendor.business_type} — {vendor.business_category}<br/>"
                f"<b>GSTIN:</b> {vendor.gstin}<br/>"
                f"<b>PAN:</b> {vendor.personal_pan}<br/>"
                f"<b>Address:</b> {vendor.business_address}, {vendor.business_city}, "
                f"{vendor.business_state} - {vendor.business_pincode}<br/>"
                f"<b>Phone:</b> {vendor.phone}<br/>"
                f"<b>Email:</b> {vendor.email}<br/>"
                f"<b>CIBIL Score:</b> {vendor.cibil_score}<br/>"
                f"<b>Annual Turnover:</b> ₹{vendor.annual_turnover:,.2f}",
                small,
            ),
            Paragraph(
                f"<b>Name:</b> {lender.name}<br/>"
                f"<b>Organization:</b> {lender.organization or 'Individual'}<br/>"
                f"<b>Type:</b> {lender.lender_type}<br/>"
                f"<b>Email:</b> {lender.email}<br/>"
                f"<b>Phone:</b> {lender.phone or 'N/A'}",
                small,
            ),
        ],
    ]
    parties_table = Table(parties_data, colWidths=[90 * mm, 90 * mm])
    parties_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(parties_table)

    # ══════════════════════════════════════════
    #  2. INVOICE DETAILS
    # ══════════════════════════════════════════
    elements.append(Paragraph("2. INVOICE DETAILS", section_style))

    inv_info = [
        ["Invoice Number", invoice.invoice_number],
        ["Invoice Date", str(invoice.invoice_date)],
        ["Due Date", str(invoice.due_date)],
        ["Supply Type", "Intra-State" if invoice.supply_type == "intra_state" else "Inter-State"],
        ["Place of Supply", f"{invoice.place_of_supply} ({invoice.place_of_supply_code})"],
        ["Buyer Name", invoice.buyer_name],
        ["Buyer GSTIN", invoice.buyer_gstin or "B2C (Unregistered)"],
        ["Buyer Address", f"{invoice.buyer_address}, {invoice.buyer_city}, {invoice.buyer_state} - {invoice.buyer_pincode}"],
        ["Invoice Status", invoice.invoice_status.upper()],
        ["Payment Status", invoice.payment_status.upper()],
    ]
    inv_rows = [[Paragraph(f"<b>{k}</b>", small), Paragraph(str(v), normal)] for k, v in inv_info]
    inv_table = Table(inv_rows, colWidths=[55 * mm, 125 * mm])
    inv_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(inv_table)

    # Line items
    elements.append(Paragraph("2.1 Line Items", subsection_style))
    is_intra = invoice.supply_type == "intra_state"
    if is_intra:
        header = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable", "CGST", "SGST", "Total"]
    else:
        header = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Taxable", "IGST", "Total"]

    item_rows = [header]
    for idx, item in enumerate(items, 1):
        if is_intra:
            item_rows.append([
                str(idx), item.description, item.hsn_sac_code,
                f"{item.quantity} {item.unit}", f"₹{item.unit_price:,.2f}",
                f"₹{item.taxable_value:,.2f}",
                f"₹{item.cgst_amount:,.2f}", f"₹{item.sgst_amount:,.2f}",
                f"₹{item.total_amount:,.2f}",
            ])
        else:
            item_rows.append([
                str(idx), item.description, item.hsn_sac_code,
                f"{item.quantity} {item.unit}", f"₹{item.unit_price:,.2f}",
                f"₹{item.taxable_value:,.2f}",
                f"₹{item.igst_amount:,.2f}",
                f"₹{item.total_amount:,.2f}",
            ])

    if is_intra:
        col_widths = [8*mm, 36*mm, 16*mm, 16*mm, 18*mm, 20*mm, 18*mm, 18*mm, 20*mm]
    else:
        col_widths = [8*mm, 44*mm, 18*mm, 18*mm, 20*mm, 22*mm, 22*mm, 22*mm]

    items_table = Table(item_rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(items_table)

    # Totals
    elements.append(Paragraph("2.2 Invoice Totals", subsection_style))
    totals = [
        ["Subtotal", f"₹{invoice.subtotal:,.2f}"],
    ]
    if invoice.total_discount > 0:
        totals.append(["Discount", f"-₹{invoice.total_discount:,.2f}"])
    if is_intra:
        totals.append(["CGST", f"₹{invoice.total_cgst:,.2f}"])
        totals.append(["SGST", f"₹{invoice.total_sgst:,.2f}"])
    else:
        totals.append(["IGST", f"₹{invoice.total_igst:,.2f}"])
    if invoice.total_cess > 0:
        totals.append(["Cess", f"₹{invoice.total_cess:,.2f}"])
    totals.append(["GRAND TOTAL", f"₹{invoice.grand_total:,.2f}"])

    totals_table = Table(
        [[Paragraph(f"<b>{k}</b>", small), Paragraph(f"<b>{v}</b>" if k == "GRAND TOTAL" else v, normal)] for k, v in totals],
        colWidths=[50 * mm, 40 * mm], hAlign="RIGHT",
    )
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1e40af")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(totals_table)

    # ══════════════════════════════════════════
    #  3. FINANCING TERMS
    # ══════════════════════════════════════════
    elements.append(Paragraph("3. FINANCING TERMS", section_style))

    terms_data = [
        ["Listing Title", listing.listing_title or "—"],
        ["Listing Description", listing.listing_description or "—"],
        ["Requested Percentage", f"{listing.requested_percentage}%"],
        ["Requested Amount", f"₹{listing.requested_amount:,.2f}"],
        ["Max Interest Rate (Vendor)", f"{listing.max_interest_rate}% p.a."],
        ["Repayment Period", f"{listing.repayment_period_days} days"],
        ["Risk Score at Listing", f"{listing.risk_score}/100" if listing.risk_score else "N/A"],
        ["Listed Date", listing.created_at.strftime("%d %B %Y, %H:%M") if listing.created_at else "—"],
    ]
    terms_rows = [[Paragraph(f"<b>{k}</b>", small), Paragraph(str(v), normal)] for k, v in terms_data]
    terms_table = Table(terms_rows, colWidths=[55 * mm, 125 * mm])
    terms_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0fdf4")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(terms_table)

    # ══════════════════════════════════════════
    #  4. FUNDING DETAILS
    # ══════════════════════════════════════════
    elements.append(Paragraph("4. FUNDING DETAILS", section_style))

    funded_amount = listing.funded_amount or 0
    funding_data = [
        ["Funded Amount", f"₹{funded_amount:,.2f}"],
        ["Funded By", listing.funded_by or "—"],
        ["Funded Date", listing.funded_at.strftime("%d %B %Y, %H:%M") if listing.funded_at else "—"],
    ]
    # Calculate total interest earned
    total_interest = sum(r.interest_amount for r in repayments) if repayments else 0
    total_principal = sum(r.principal_amount for r in repayments) if repayments else 0
    total_paid = sum(r.paid_amount or r.total_amount for r in repayments if r.status == "paid") if repayments else 0
    funding_data.append(["Total Principal", f"₹{total_principal:,.2f}"])
    funding_data.append(["Total Interest Earned", f"₹{total_interest:,.2f}"])
    funding_data.append(["Total Amount Repaid", f"₹{total_paid:,.2f}"])

    if listing.settlement_date:
        funding_data.append(["Settlement Date", listing.settlement_date.strftime("%d %B %Y, %H:%M")])

    funding_rows = [[Paragraph(f"<b>{k}</b>", small), Paragraph(str(v), normal)] for k, v in funding_data]
    funding_table = Table(funding_rows, colWidths=[55 * mm, 125 * mm])
    funding_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(funding_table)

    # ══════════════════════════════════════════
    #  5. REPAYMENT SCHEDULE
    # ══════════════════════════════════════════
    if repayments:
        elements.append(Paragraph("5. REPAYMENT SCHEDULE", section_style))

        repay_header = ["#", "Due Date", "Principal", "Interest", "Total", "Status", "Paid Date", "Paid Amount"]
        repay_rows = [repay_header]
        for r in sorted(repayments, key=lambda x: x.installment_number):
            status_str = r.status.upper()
            repay_rows.append([
                str(r.installment_number),
                r.due_date,
                f"₹{r.principal_amount:,.2f}",
                f"₹{r.interest_amount:,.2f}",
                f"₹{r.total_amount:,.2f}",
                status_str,
                r.paid_date or "—",
                f"₹{r.paid_amount:,.2f}" if r.paid_amount else "—",
            ])

        repay_table = Table(repay_rows, colWidths=[8*mm, 24*mm, 24*mm, 22*mm, 24*mm, 20*mm, 24*mm, 24*mm], repeatRows=1)
        repay_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#059669")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (5, 1), (5, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdf4")]),
        ]))
        elements.append(repay_table)

        # Summary
        paid_count = sum(1 for r in repayments if r.status == "paid")
        total_count = len(repayments)
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f"<b>Repayment Summary:</b> {paid_count}/{total_count} installments paid | "
            f"Total Repaid: ₹{total_paid:,.2f} | "
            f"Outstanding: ₹{sum(r.total_amount for r in repayments if r.status != 'paid'):,.2f}",
            normal,
        ))

    # ══════════════════════════════════════════
    #  6. BLOCKCHAIN VERIFICATION
    # ══════════════════════════════════════════
    elements.append(Paragraph("6. BLOCKCHAIN VERIFICATION", section_style))
    elements.append(Paragraph(
        "All transactions in this contract are immutably recorded on the InvoX blockchain. "
        "Each block is cryptographically signed and linked to previous blocks, ensuring tamper-proof records.",
        body,
    ))
    elements.append(Spacer(1, 2 * mm))

    chain_data = [
        ["Invoice Block Hash", invoice.blockchain_hash or "N/A"],
        ["Listing Block Hash", listing.blockchain_hash or "N/A"],
        ["Invoice PDF Hash", listing.pdf_hash or "N/A"],
    ]
    chain_rows = [[Paragraph(f"<b>{k}</b>", small), Paragraph(f'<font face="Courier" size="7">{v}</font>', small)] for k, v in chain_data]
    chain_table = Table(chain_rows, colWidths=[45 * mm, 135 * mm])
    chain_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(chain_table)

    # ══════════════════════════════════════════
    #  7. TERMS & CONDITIONS
    # ══════════════════════════════════════════
    elements.append(Paragraph("7. TERMS & CONDITIONS", section_style))

    terms_text = [
        "1. This Smart Contract is generated by the InvoX platform and represents a binding record of the invoice financing transaction between the Vendor (Borrower) and Lender (Investor).",
        "2. The Vendor has listed the above invoice on the InvoX marketplace for financing. The Lender has agreed to fund the invoice at the stated terms.",
        f"3. The Vendor agrees to repay the funded amount of ₹{funded_amount:,.2f} plus applicable interest within {listing.repayment_period_days} days as per the repayment schedule above.",
        "4. All payments are processed through the InvoX Pay gateway with 256-bit SSL encryption.",
        "5. In case of default, the Lender reserves the right to initiate recovery proceedings as per applicable Indian laws including the MSME Development Act, 2006.",
        "6. Both parties acknowledge that all transactions are immutably recorded on the InvoX blockchain and can be verified independently.",
        "7. The platform charges no hidden fees. All interest rates and terms are transparent and agreed upon by both parties before funding.",
        "8. Disputes, if any, shall be resolved through arbitration as per the Arbitration and Conciliation Act, 1996.",
    ]
    for t in terms_text:
        elements.append(Paragraph(t, body))
        elements.append(Spacer(1, 1.5 * mm))

    # ══════════════════════════════════════════
    #  8. SIGNATURES
    # ══════════════════════════════════════════
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 6 * mm))

    sig_data = [
        [Paragraph("<b>Vendor (Borrower)</b>", bold), Paragraph("", normal), Paragraph("<b>Lender (Investor)</b>", bold)],
        [Spacer(1, 15 * mm), Spacer(1, 15 * mm), Spacer(1, 15 * mm)],
        [
            Paragraph(f"Name: {vendor.full_name}<br/>GSTIN: {vendor.gstin}", small),
            Paragraph("", small),
            Paragraph(f"Name: {lender.name}<br/>Org: {lender.organization or 'Individual'}", small),
        ],
        [
            Paragraph(f"Date: _______________", small),
            Paragraph("", small),
            Paragraph(f"Date: _______________", small),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[75 * mm, 30 * mm, 75 * mm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (0, 1), 1, colors.black),
        ("LINEBELOW", (2, 1), (2, 1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ]))
    elements.append(sig_table)

    # ══════════════════════════════════════════
    #  FOOTER
    # ══════════════════════════════════════════
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e40af")))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "This Smart Contract is digitally generated and blockchain-verified by the InvoX Platform. "
        "No physical signature is required for the digital version. "
        "For verification, scan the blockchain hashes above.",
        center_small,
    ))
    elements.append(Paragraph(
        f"© {datetime.utcnow().year} InvoX — Embedded Invoice Financing Platform for MSMEs | All Rights Reserved",
        ParagraphStyle("FooterCopy", parent=center_small, fontSize=7, textColor=colors.HexColor("#94a3b8")),
    ))

    doc.build(elements)
    return buf.getvalue()
