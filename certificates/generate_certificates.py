"""Generate certificates of participation.

Reads the registration export ([files] registration_export in config.toml).
If it has an "Attended" column ([columns] attended), only rows marked "yes"
get a certificate. Certificate numbers come from [certificates] number_format
and each participant's form response ID. Also produces two fill-in-by-hand
blanks (with and without a talk line) and certificates_for_printing.pdf, all
participant certificates merged into one file.

    python certificates/generate_certificates.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pypdf import PdfReader, PdfWriter

import workshop_tools as wt

HERE = Path(__file__).resolve().parent
TEMPLATES = {
    "plain": HERE / "certificate_template.tex",
    "decorative": HERE / "certificate_template_decorative.tex",
}
OUTPUT_DIR = HERE / "output"
MERGED_FILE = HERE / "certificates_for_printing.pdf"
BLANK_MARKER = "BLANK"

REQUIRED_CONFIG = [
    "EVENT_NAME", "EVENT_START_DATE", "EVENT_END_DATE", "EVENT_DATES_SHORT",
    "VENUE_NAME", "VENUE_COUNTRY", "SIGNATORY_NAME",
    "ORGANISER_NAME", "ORGANISER_WEBSITE",
    "CERTIFICATES_ISSUE_DATE", "CERTIFICATES_NUMBER_FORMAT",
]

# Underlined blank space used on the fill-in-by-hand certificates.
BLANK_LONG = r"\underline{\hspace{55mm}}"
BLANK_SHORT = r"\underline{\hspace{40mm}}"
BLANK_TALK = r"\underline{\hspace{45mm}}"
BLANK_FIELDS = ("PARTICIPANT_NAME", "PARTICIPANT_ORGANISATION", "CERTIFICATE_NUMBER", "TALK_TITLE")


def generate_blank_certificates(template, values, support_files):
    for with_talk, name in ((True, f"{BLANK_MARKER}-TALK"), (False, BLANK_MARKER)):
        blank_values = {
            **values,
            "PARTICIPANT_NAME": BLANK_LONG,
            "PARTICIPANT_ORGANISATION": BLANK_LONG,
            "CERTIFICATE_NUMBER": BLANK_SHORT,
            "TALK_TITLE": BLANK_TALK if with_talk else "",
        }
        tex = wt.fill(template, blank_values, escape=wt.latex_escape, raw=BLANK_FIELDS, label=name)
        wt.compile_tex(tex, OUTPUT_DIR / f"{name}.pdf", support_files)


def merge_certificates(pdfs: list[Path]):
    """Merge this run's participant certificates into one file for printing."""
    if not pdfs:
        wt.log.warning("No certificates to merge.")
        return
    writer = PdfWriter()
    for pdf in pdfs:
        for page in PdfReader(str(pdf)).pages:
            writer.add_page(page)
    with open(MERGED_FILE, "wb") as f:
        writer.write(f)
    wt.log.info("Merged %d certificates into %s", len(pdfs), MERGED_FILE.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()

    config = wt.load_config()
    values = wt.config_values(config)
    wt.require_filled(values, REQUIRED_CONFIG)
    columns = config["columns"]

    design = config["certificates"].get("design", "plain")
    if design not in TEMPLATES:
        raise SystemExit(f"[certificates] design must be one of {sorted(TEMPLATES)}, got {design!r}")
    template = TEMPLATES[design].read_text(encoding="utf-8")

    df, _ = wt.load_participants(config)

    attended = columns.get("attended", "")
    if attended and attended in df.columns:
        df = df[df[attended].map(wt.is_yes)]
        wt.log.info("Only participants marked in column %r: %d", attended, len(df))

    wt.check_tectonic()
    graphics, support_files = wt.graphics_values(values, logo_width="52mm")
    base_values = {**values, **graphics}

    generated = []
    for _, row in df.iterrows():
        person = wt.participant_values(row.to_dict(), config, values)
        tex = wt.fill(template, {**base_values, **person}, escape=wt.latex_escape,
                      label=f"certificate {person['CERTIFICATE_NUMBER']}")
        output = OUTPUT_DIR / f"{wt.safe_filename(person['CERTIFICATE_NUMBER'])}.pdf"
        if output.exists():
            wt.log.info("Overwriting %s", output.name)
        if wt.compile_tex(tex, output, support_files):
            generated.append(output)

    generate_blank_certificates(template, base_values, support_files)
    merge_certificates(generated)
    wt.log.info("Done. %d certificate(s) in %s", len(generated), OUTPUT_DIR)


if __name__ == "__main__":
    main()
