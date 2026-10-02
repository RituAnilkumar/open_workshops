"""Generate invitation letters (PDF) from the registration export.

Which letter(s) a participant gets is read from the registration form's
invitation-letter question ([columns] invitation_letter): answers containing
[letters] visa_keyword get the visa/travel letter (letter_visa_travel.tex),
answers containing [letters] funder_keyword get the funder letter
(letter_funder.tex). Someone who ticked both gets both.

The visa/travel letter states that the abstract was accepted only if you
have filled in the participant's "Presentation Format" column
([columns] presentation_format) in the export; otherwise that sentence is
left out.

Letters are written to invitation_letters/output/<ID>_<name>_<type>.pdf.

    python invitation_letters/generate_letters.py
    python invitation_letters/generate_letters.py --only 12 someone@example.org
    python invitation_letters/generate_letters.py --only 12 --type visa   # regardless of the form answer
    python invitation_letters/generate_letters.py --overwrite             # rebuild existing letters
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import workshop_tools as wt

HERE = Path(__file__).resolve().parent
TEMPLATES = {
    "visa": HERE / "letter_visa_travel.tex",
    "funder": HERE / "letter_funder.tex",
}
OUTPUT_DIR = HERE / "output"

REQUIRED_CONFIG = {
    "funder": [
        "EVENT_NAME", "EVENT_TYPE", "EVENT_START_DATE", "EVENT_END_DATE",
        "VENUE_NAME", "VENUE_CITY", "VENUE_COUNTRY",
        "SIGNATORY_NAME", "SIGNATORY_TITLE", "SIGNATORY_AFFILIATION",
    ],
}
REQUIRED_CONFIG["visa"] = REQUIRED_CONFIG["funder"] + [
    "ACCOMMODATION_NAME", "ACCOMMODATION_COST",
    "LETTERS_COVER_START_DATE", "LETTERS_COVER_END_DATE",
]


def letters_requested(answer: str, values: dict) -> list[str]:
    answer = answer.lower()
    kinds = []
    if values["LETTERS_VISA_KEYWORD"].lower() in answer:
        kinds.append("visa")
    if values["LETTERS_FUNDER_KEYWORD"].lower() in answer:
        kinds.append("funder")
    return kinds


def with_article(presentation_format: str) -> str:
    """'Oral' -> 'an oral', 'Poster' -> 'a poster'."""
    word = presentation_format.strip().lower()
    if not word:
        return ""
    return ("an " if word[0] in "aeiou" else "a ") + word


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="ID_OR_EMAIL",
                        help="Only participants with these form response IDs or email addresses.")
    parser.add_argument("--type", choices=sorted(TEMPLATES),
                        help="Only this letter type. With --only, it is generated even if the "
                             "participant did not ask for it on the form.")
    parser.add_argument("--overwrite", action="store_true", help="Rebuild letters that already exist.")
    args = parser.parse_args()

    config = wt.load_config()
    values = wt.config_values(config)
    columns = config["columns"]
    df, path = wt.load_participants(config)

    letter_column = columns.get("invitation_letter", "")
    if not (args.only and args.type):
        wt.require_columns(df, [letter_column], path)

    date = values.get("LETTERS_DATE", "").strip()
    graphics, support_files = wt.graphics_values(values, logo_width="45mm", signature_width="35mm")
    base_values = {
        **values, **graphics,
        "LETTER_DATE_TEX": wt.latex_escape(date) if date else r"\today",
    }
    templates = {kind: path.read_text(encoding="utf-8") for kind, path in TEMPLATES.items()}

    jobs = []
    for _, row in df.iterrows():
        row = row.to_dict()
        person = wt.participant_values(row, config, values)
        if args.only and not ({person["PARTICIPANT_ID"], person["PARTICIPANT_EMAIL"]} & set(args.only)):
            continue
        if args.only and args.type:
            kinds = [args.type]
        else:
            kinds = letters_requested(wt.column_value(row, columns, "invitation_letter"), values)
            if args.type:
                kinds = [k for k in kinds if k == args.type]
        for kind in kinds:
            jobs.append((kind, person))

    if not jobs:
        wt.log.info("No letters requested for the selected participants.")
        return

    for kind in {kind for kind, _ in jobs}:
        wt.require_filled(values, REQUIRED_CONFIG[kind])
    wt.check_tectonic()

    for kind, person in jobs:
        name = f"{int(person['PARTICIPANT_ID']):03d}_{wt.safe_filename(person['PARTICIPANT_NAME'])}_{kind}"
        output = OUTPUT_DIR / f"{name}.pdf"
        if output.exists() and not args.overwrite:
            wt.log.info("Skipping %s — already exists (use --overwrite to rebuild)", output.name)
            continue

        presentation = with_article(person["PRESENTATION_FORMAT"]) if person["TALK_TITLE"] else ""
        letter_values = {**base_values, **person, "PRESENTATION_FORMAT_ARTICLE": presentation}
        tex = wt.fill(templates[kind], letter_values, escape=wt.latex_escape, label=f"{kind} letter for {name}")
        wt.compile_tex(tex, output, support_files)

    wt.log.info("Done. Letters are in: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
