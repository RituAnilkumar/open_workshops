"""Email invoices (or fee-waiver notices) to participants via Outlook.

Participants marked as fee-waived get emails/waiver_email.html (no invoice);
everyone else gets emails/invoice_email.html with their invoice PDF. The
programme PDF from config.toml ([email] schedule_pdf) is attached to both.

NOTHING IS SENT unless you pass --send. Without it the script only lists
what it would send, so always do a dry run first.

    python invoices/send_registration_emails.py                       # dry run, everyone
    python invoices/send_registration_emails.py --kind waiver         # dry run, waivers only
    python invoices/send_registration_emails.py --only ABC_2027_004 someone@example.org --send
    python invoices/send_registration_emails.py --preview preview.html  # write first email to a file
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import workshop_tools as wt
from generate_invoices import fee_text, invoice_pdf

HERE = Path(__file__).resolve().parent
INVOICE_EMAIL = HERE / "emails" / "invoice_email.html"
WAIVER_EMAIL = HERE / "emails" / "waiver_email.html"

REQUIRED_CONFIG = [
    "EVENT_NAME", "EVENT_DATES_SHORT", "VENUE_NAME", "VENUE_CITY", "VENUE_COUNTRY",
    "REGISTRATION_PAYMENT_FORM_URL", "EMAIL_SENDER_ADDRESS", "EMAIL_SENDER_NAME",
]


def paragraph(text: str) -> str:
    return f"<p>{wt.html_escape(text)}</p>" if text.strip() else ""


def shared_html(values: dict, schedule_attached: bool) -> dict:
    """Optional paragraphs, left out when the matching config value is empty."""
    if not schedule_attached:
        schedule = ""
    elif values.get("SCHEDULE_STATUS", "").strip():
        schedule = (" A tentative programme schedule is attached. This is a preliminary "
                    "schedule and is likely to change.")
    else:
        schedule = " The programme schedule is attached."

    funder = values.get("FEE_WAIVER_FUNDER", "").strip()
    condition = values.get("FEE_WAIVER_CONDITION", "").strip()
    url = values.get("FEE_WAIVER_CONDITION_URL", "").strip()
    condition_html = ""
    if condition:
        condition_html = f"<p>{wt.html_escape(condition)}"
        if url:
            condition_html += f'<br>\n<a href="{wt.html_escape(url)}">{wt.html_escape(url)}</a>'
        condition_html += "</p>"

    return {
        "SCHEDULE_SENTENCE_HTML": schedule,
        "PROGRAMME_NOTE_HTML": paragraph(values.get("EVENT_PROGRAMME_NOTE", "")),
        "ACCOMMODATION_NOTE_HTML": paragraph(values.get("ACCOMMODATION_EMAIL_NOTE", "")),
        "WAIVER_FUNDER_HTML": f" thanks to funding from <strong>{wt.html_escape(funder)}</strong>" if funder else "",
        "WAIVER_CONDITION_HTML": condition_html,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--send", action="store_true", help="Actually send. Without this flag nothing is sent.")
    parser.add_argument("--kind", choices=["all", "invoice", "waiver"], default="all",
                        help="Which participants to email (default: all).")
    parser.add_argument("--only", nargs="+", metavar="INVOICE_OR_EMAIL",
                        help="Only participants with these invoice numbers or email addresses.")
    parser.add_argument("--delay", type=int, help="Seconds between emails (default: [email] delay_seconds).")
    parser.add_argument("--preview", metavar="FILE.html", help="Write the first email body to this file and stop.")
    args = parser.parse_args()

    config = wt.load_config()
    values = wt.config_values(config)
    wt.require_filled(values, REQUIRED_CONFIG)
    columns = config["columns"]
    delay = args.delay if args.delay is not None else int(config["email"].get("delay_seconds", 10))

    schedule_setting = values.get("EMAIL_SCHEDULE_PDF", "").strip()
    schedule_pdf = wt.project_path(schedule_setting) if schedule_setting else None
    if schedule_pdf and not schedule_pdf.exists():
        message = f"Programme PDF not found: {schedule_pdf}"
        if args.send:
            raise SystemExit(message + "\nCheck the path, or set [email] schedule_pdf = \"\".")
        wt.log.warning(message)

    base_values = {**values, **shared_html(values, schedule_pdf is not None)}
    templates = {
        "invoice": (INVOICE_EMAIL.read_text(encoding="utf-8"), values["EMAIL_INVOICE_SUBJECT"]),
        "waiver": (WAIVER_EMAIL.read_text(encoding="utf-8"), values["EMAIL_WAIVER_SUBJECT"]),
    }

    df, _ = wt.load_participants(config)
    jobs = []
    for _, row in df.iterrows():
        row = row.to_dict()
        person = wt.participant_values(row, config, values)
        if not person["PARTICIPANT_NAME"] or not person["PARTICIPANT_EMAIL"]:
            continue
        if args.only and not ({person["INVOICE_NUMBER"], person["PARTICIPANT_EMAIL"]} & set(args.only)):
            continue

        kind = "waiver" if wt.is_waived(row, columns) else "invoice"
        if args.kind not in ("all", kind):
            continue

        email_values = {**base_values, **person}
        attachments = []
        if kind == "invoice":
            if not person["INVOICE_NUMBER"]:
                raise SystemExit("Please set [registration] invoice_number_format in config.toml first.")
            pdf = invoice_pdf(person["INVOICE_NUMBER"])
            if not pdf.exists():
                wt.log.error("Skipping %s — invoice PDF not found, run generate_invoices.py first",
                             person["INVOICE_NUMBER"])
                continue
            attachments.append(pdf)
            wt.require_filled(values, ["REGISTRATION_PAYMENT_DEADLINE", "REGISTRATION_FEE"])
            email_values["INVOICE_TOTAL"] = fee_text(values)
        if schedule_pdf and schedule_pdf.exists():
            attachments.append(schedule_pdf)

        template, subject = templates[kind]
        body = wt.fill(template, email_values, escape=wt.html_escape, label=f"{kind} email")
        jobs.append((kind, person["PARTICIPANT_EMAIL"], subject, body, attachments))

    if args.preview:
        if not jobs:
            raise SystemExit("No matching participants to preview.")
        Path(args.preview).write_text(jobs[0][3], encoding="utf-8")
        wt.log.info("Wrote preview of the email to %s to %s", jobs[0][1], args.preview)
        return

    if not args.send:
        wt.log.info("--- DRY RUN: nothing will be sent (add --send to send) ---")
    outlook = wt.outlook_client() if args.send else None

    for i, (kind, recipient, subject, body, attachments) in enumerate(jobs):
        names = ", ".join(Path(a).name for a in attachments) or "none"
        if not args.send:
            wt.log.info("[DRY RUN] %s email to %s | %s | attachments: %s", kind, recipient, subject, names)
            continue
        wt.outlook_send(outlook, values["EMAIL_SENDER_ADDRESS"], recipient, subject, body, attachments)
        wt.log.info("Sent %s email to %s", kind, recipient)
        if i < len(jobs) - 1:
            time.sleep(delay)

    wt.log.info("Done. %d email(s) %s.", len(jobs), "sent" if args.send else "would be sent")


if __name__ == "__main__":
    main()
