"""Generate one invoice PDF per participant who is not fee-waived.

Reads the registration export ([files] registration_export in config.toml),
fills invoice_template.tex + letterhead.lco and compiles them with tectonic
into invoices/output/<invoice number>.pdf. Invoice numbers come from
[registration] invoice_number_format and each participant's form response ID.

    python invoices/generate_invoices.py                  # all missing invoices
    python invoices/generate_invoices.py --only ABC_2027_003 ABC_2027_007
    python invoices/generate_invoices.py --overwrite      # rebuild existing PDFs
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import workshop_tools as wt

HERE = Path(__file__).resolve().parent
TEMPLATE_FILE = HERE / "invoice_template.tex"
LETTERHEAD_FILE = HERE / "letterhead.lco"
OUTPUT_DIR = HERE / "output"

REQUIRED_CONFIG = [
    "EVENT_NAME", "EVENT_START_DATE", "EVENT_END_DATE",
    "VENUE_NAME", "VENUE_CITY", "VENUE_COUNTRY",
    "SIGNATORY_NAME",
    "ORGANISER_NAME", "ORGANISER_ADDRESS_LINE1", "ORGANISER_ADDRESS_LINE2",
    "ORGANISER_ADDRESS_LINE3", "ORGANISER_EMAIL", "ORGANISER_WEBSITE",
    "BANK_ACCOUNT_NAME", "BANK_BANK_NAME", "BANK_IBAN", "BANK_BIC",
    "REGISTRATION_FEE", "REGISTRATION_CURRENCY", "REGISTRATION_PAYMENT_DEADLINE",
    "REGISTRATION_INVOICE_NUMBER_FORMAT",
]


def registration_fee(values: dict) -> float:
    try:
        return float(values["REGISTRATION_FEE"].replace(",", ""))
    except ValueError:
        raise SystemExit(f"[registration] fee must be a number, got: {values['REGISTRATION_FEE']!r}")


def fee_text(values: dict) -> str:
    """Registration fee formatted with currency, e.g. '250.00 EUR'."""
    return f"{registration_fee(values):,.2f} {values['REGISTRATION_CURRENCY']}"


def invoice_pdf(invoice_number: str) -> Path:
    return OUTPUT_DIR / f"{wt.safe_filename(invoice_number)}.pdf"


def organiser_details_tex(values: dict) -> str:
    """Right-hand column of the letterhead. Optional lines are left out when empty."""
    e = wt.latex_escape
    lines = [
        rf"  {e(values['ORGANISER_ADDRESS_LINE1'])}\\",
        rf"  {e(values['ORGANISER_ADDRESS_LINE2'])}\\",
        rf"  {e(values['ORGANISER_ADDRESS_LINE3'])}\\[5mm]",
        r"  \textbf{E-Mail}\\[0mm]",
        rf"  {e(values['ORGANISER_EMAIL'])}\\[5mm]",
        r"  \textbf{Web}\\[0mm]",
        rf"  {e(values['ORGANISER_WEBSITE'])}\\[5mm]",
    ]
    if values.get("ORGANISER_REGISTRATION"):
        lines.append(rf"  \parbox[t]{{50mm}}{{\raggedright\textbf{{{e(values['ORGANISER_REGISTRATION'])}}}}}\\[0mm]")
        if values.get("ORGANISER_REGISTRY_NUMBER"):
            lines.append(rf"  Registry No.: {e(values['ORGANISER_REGISTRY_NUMBER'])}\\[5mm]")
        else:
            lines.append(r"  \\[5mm]")
    if values.get("ORGANISER_TAX_ID"):
        lines += [r"  \textbf{Tax ID}\\[0mm]", rf"  {e(values['ORGANISER_TAX_ID'])}\\[5mm]"]
    lines += [
        r"  \textbf{Bank Account}\\[0mm]",
        rf"  Name: {e(values['BANK_ACCOUNT_NAME'])}\\",
        rf"  Bank Name: {e(values['BANK_BANK_NAME'])}\\",
        rf"  IBAN: {e(values['BANK_IBAN'])}\\",
        rf"  BIC: {e(values['BANK_BIC'])}",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="INVOICE_NUMBER", help="Only these invoice numbers.")
    parser.add_argument("--overwrite", action="store_true", help="Rebuild PDFs that already exist.")
    args = parser.parse_args()

    config = wt.load_config()
    values = wt.config_values(config)
    wt.require_filled(values, REQUIRED_CONFIG)
    columns = config["columns"]
    df, _ = wt.load_participants(config)

    wt.check_tectonic()
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    graphics, support_files = wt.graphics_values(values, logo_width="42mm")
    base_values = {
        **values, **graphics,
        "ORGANISER_DETAILS_TEX": organiser_details_tex(values),
        "INVOICE_TOTAL": fee_text(values),
    }
    vat_note = values.get("ORGANISER_VAT_NOTE", "")
    base_values["VAT_NOTE_TEX"] = rf"{{\scriptsize {wt.latex_escape(vat_note)}}}" if vat_note else ""

    letterhead = wt.fill(
        LETTERHEAD_FILE.read_text(encoding="utf-8"), base_values,
        escape=wt.latex_escape, label=LETTERHEAD_FILE.name,
    )

    for _, row in df.iterrows():
        row = row.to_dict()
        person = wt.participant_values(row, config, values)
        number = person["INVOICE_NUMBER"]
        if wt.is_waived(row, columns):
            wt.log.info("Skipping %s — fee waived", person["PARTICIPANT_NAME"])
            continue
        if args.only and number not in args.only:
            continue
        if not person["PARTICIPANT_COUNTRY"]:
            wt.log.warning("%s: no country found in the affiliation; the address will have no country line",
                           person["PARTICIPANT_NAME"])

        output_pdf = invoice_pdf(number)
        if output_pdf.exists() and not args.overwrite:
            wt.log.info("Skipping %s — PDF already exists (use --overwrite to rebuild)", number)
            continue

        tex = wt.fill(template, {**base_values, **person}, escape=wt.latex_escape, label=f"invoice {number}")
        wt.compile_tex(tex, output_pdf, support_files, {"letterhead.lco": letterhead})

    wt.log.info("Done. PDFs are in: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
