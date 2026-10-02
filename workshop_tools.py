"""Shared helpers for the open_workshops scripts.

Placeholders look like <<<SECTION_KEY>>> and are filled from config.toml
(section [event], key name  ->  <<<EVENT_NAME>>>) plus per-participant values.
Values are escaped for the target format (LaTeX / HTML) unless the
placeholder name ends in _TEX or _HTML, which marks ready-made markup.
"""
import html
import logging
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.toml"

TOKEN_RE = re.compile(r"<<<([A-Z0-9_]+)>>>")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("open_workshops")


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

def load_config(path: Path = CONFIG_FILE) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def config_values(config: dict) -> dict[str, str]:
    """Flatten config into {SECTION_KEY: value} and resolve placeholders used
    inside config values (e.g. an email subject containing <<<EVENT_NAME>>>)."""
    values = {}
    for section, entries in config.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            if isinstance(value, (str, int, float)):
                values[f"{section}_{key}".upper()] = str(value)

    for _ in range(3):
        for key, value in values.items():
            values[key] = TOKEN_RE.sub(lambda m: values.get(m.group(1), m.group(0)), value)
    return values


def is_unfilled(value) -> bool:
    return str(value).strip().upper().startswith("TODO")


def require_filled(values: dict, keys) -> None:
    """Fail early, with one message, if any of the given config keys still says TODO."""
    unfilled = sorted(k for k in keys if is_unfilled(values.get(k, "TODO")))
    if unfilled:
        raise SystemExit(
            "Please fill in these values in config.toml first:\n  "
            + "\n  ".join(unfilled)
        )


def project_path(relative: str) -> Path:
    """Resolve a path from config.toml relative to the open_workshops folder."""
    path = Path(relative)
    return path if path.is_absolute() else ROOT / path


# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------

def latex_escape(value) -> str:
    """Escape LaTeX special characters while retaining Unicode text."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def html_escape(value) -> str:
    return html.escape(str(value), quote=True)


def fill(template: str, values: dict, escape=None, raw=(), label="template") -> str:
    """Replace every <<<KEY>>> in template. Fails if a key is unknown or
    still TODO, so no half-filled document is ever produced."""
    used = set(TOKEN_RE.findall(template))
    missing = sorted(k for k in used if k not in values)
    unfilled = sorted(k for k in used if k in values and is_unfilled(values[k]))
    if missing or unfilled:
        message = f"Cannot fill {label}."
        if unfilled:
            message += "\n  Still TODO in config.toml: " + ", ".join(unfilled)
        if missing:
            message += "\n  Unknown placeholders: " + ", ".join(missing)
        raise SystemExit(message)

    def replace(match):
        key = match.group(1)
        value = values[key]
        if escape is None or key in raw or key.endswith(("_TEX", "_HTML")):
            return value
        return escape(value)

    return TOKEN_RE.sub(replace, template)


# -----------------------------------------------------------------------------
# Participant data
# -----------------------------------------------------------------------------

def read_table(path: Path) -> pd.DataFrame:
    """Read a CSV (UTF-8, falling back to Excel's Windows-1252) or Excel file.
    Everything is read as text; empty cells become ""."""
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            log.info("%s is not UTF-8; reading it as Windows-1252.", path.name)
            df = pd.read_csv(path, dtype=str, encoding="cp1252")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("").apply(lambda col: col.str.strip())


def require_columns(df: pd.DataFrame, columns, path: Path) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise SystemExit(
            f"{path.name} is missing columns: {missing}\n"
            "Either rename the columns in the file or update [columns] in config.toml."
        )


def is_yes(value) -> bool:
    return str(value).strip().lower() in {"yes", "y", "true", "1", "x"}


def load_participants(config: dict) -> tuple[pd.DataFrame, Path]:
    """Read the registration export ([files] registration_export): one row per
    participant. Cancelled participants are simply removed from that file."""
    columns = config["columns"]
    path = project_path(config["files"]["registration_export"])
    df = read_table(path)
    required = [columns[k] for k in ("id", "name", "affiliation", "email")]
    if columns.get("country"):
        required.append(columns["country"])
    require_columns(df, required, path)
    df = df[df[columns["name"]] != ""]

    ids = [response_id(v, path) for v in df[columns["id"]]]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f"Duplicate IDs in {path.name}: {duplicates}")
    return df, path


def response_id(value, path: Path) -> int:
    """Form response IDs are whole numbers (Excel may store them as 5.0)."""
    try:
        return int(float(str(value).strip()))
    except ValueError:
        raise SystemExit(f"{path.name}: ID {value!r} is not a number.")


def format_number(number_format: str, number: int, config_key: str) -> str:
    """Replace the last group of N's with the zero-padded number:
    format_number("ABC_2027_NNN", 5) -> "ABC_2027_005"."""
    groups = list(re.finditer(r"N+", number_format))
    if not groups:
        raise SystemExit(f"{config_key} must contain N's for the number, e.g. ABC_2027_NNN")
    last = groups[-1]
    digits = len(last.group())
    return number_format[: last.start()] + f"{number:0{digits}d}" + number_format[last.end():]


def split_affiliation(affiliation: str) -> tuple[str, str]:
    """'Institute, University, Country' -> ('Institute, University', 'Country')."""
    if "," not in affiliation:
        return affiliation.strip(), ""
    organisation, country = affiliation.rsplit(",", 1)
    return organisation.strip(), country.strip()


def column_value(row, columns: dict, key: str) -> str:
    """Value of an optional column; "" if the column is not configured or absent."""
    column = columns.get(key, "")
    return str(row.get(column, "")).strip() if column else ""


def participant_values(row, config: dict, values: dict) -> dict[str, str]:
    """Map a registration-export row to PARTICIPANT_* / INVOICE_NUMBER / ... placeholders."""
    columns = config["columns"]
    number = response_id(row[columns["id"]], Path(config["files"]["registration_export"]))
    affiliation = column_value(row, columns, "affiliation")
    if columns.get("country"):
        organisation, country = affiliation, column_value(row, columns, "country")
    else:
        organisation, country = split_affiliation(affiliation)

    result = {
        "PARTICIPANT_ID": str(number),
        "PARTICIPANT_NAME": column_value(row, columns, "name"),
        "PARTICIPANT_AFFILIATION": affiliation if not columns.get("country") or not country
                                   else f"{affiliation}, {country}",
        "PARTICIPANT_ORGANISATION": organisation,
        "PARTICIPANT_COUNTRY": country,
        "PARTICIPANT_EMAIL": column_value(row, columns, "email"),
        "TALK_TITLE": column_value(row, columns, "talk_title"),
        "PRESENTATION_FORMAT": column_value(row, columns, "presentation_format"),
        "INVOICE_NUMBER": "",
        "CERTIFICATE_NUMBER": "",
    }
    if not is_unfilled(values.get("REGISTRATION_INVOICE_NUMBER_FORMAT", "TODO")):
        result["INVOICE_NUMBER"] = format_number(
            values["REGISTRATION_INVOICE_NUMBER_FORMAT"], number, "[registration] invoice_number_format")
    if not is_unfilled(values.get("CERTIFICATES_NUMBER_FORMAT", "TODO")):
        result["CERTIFICATE_NUMBER"] = format_number(
            values["CERTIFICATES_NUMBER_FORMAT"], number, "[certificates] number_format")
    return result


def is_waived(row, columns: dict) -> bool:
    return is_yes(column_value(row, columns, "fee_waived"))


# -----------------------------------------------------------------------------
# Images (logos / signature)
# -----------------------------------------------------------------------------

def image_path(setting: str, config_key: str) -> Path | None:
    """Resolve an optional image path from config.toml (relative to this folder
    or absolute). Returns None if the setting is empty."""
    setting = setting.strip().strip('"')
    if not setting:
        return None
    if is_unfilled(setting):
        raise SystemExit(f"Please set {config_key} in config.toml (or set it to \"\").")
    path = project_path(setting)
    if not path.is_file():
        raise SystemExit(f"{config_key} file not found: {path}")
    return path


IMAGES = {
    # build-folder name: (config value, config key for messages)
    "logo": ("ORGANISER_LOGO", "[organiser] logo"),
    "partnerlogo": ("LETTERS_PARTNER_LOGO", "[letters] partner_logo"),
    "signature": ("SIGNATORY_SIGNATURE_IMAGE", "[signatory] signature_image"),
}


def graphics_values(values: dict, logo_width: str, signature_width: str = "25mm"):
    """Return (image placeholders, {build name: source path}).

    LOGO_TEX / PARTNER_LOGO_TEX / SIGNATURE_IMAGE_TEX are includegraphics
    commands, or "" when the image is not configured. SIGNATURE_TEX adds a line
    break after the signature image. Images are copied into the LaTeX build
    folder as logo.<ext> etc., so the original paths may contain spaces or live
    anywhere on disk."""
    support, tex = {}, {}
    for name, (value_key, config_key) in IMAGES.items():
        path = image_path(values.get(value_key, ""), config_key)
        if path is None:
            tex[name] = ""
            continue
        build_name = name + path.suffix.lower()
        support[build_name] = path
        width = signature_width if name == "signature" else logo_width
        tex[name] = rf"\includegraphics[width={width}]{{{build_name}}}"

    extra = {
        "LOGO_TEX": tex["logo"],
        "PARTNER_LOGO_TEX": tex["partnerlogo"],
        "SIGNATURE_IMAGE_TEX": tex["signature"],
        "SIGNATURE_TEX": tex["signature"] + r"\\[0mm]" if tex["signature"] else "",
    }
    return extra, support


# -----------------------------------------------------------------------------
# LaTeX
# -----------------------------------------------------------------------------

def check_tectonic() -> None:
    try:
        result = subprocess.run(["tectonic", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        result = None
    if result is None or result.returncode != 0:
        raise SystemExit(
            "tectonic not found. Activate the conda environment first:\n"
            "  conda activate open-workshops"
        )
    log.info("tectonic found: %s", result.stdout.strip())


def compile_tex(tex: str, output_pdf: Path, support_files=None, extra_texts=None) -> bool:
    """Compile LaTeX source to output_pdf in a temporary folder.

    support_files: {name in build folder: source path}, e.g. logo / signature.
    extra_texts:   {filename: text} written next to the .tex (e.g. a filled .lco).
    """
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        for name, path in (support_files or {}).items():
            shutil.copy(path, build / name)
        for name, text in (extra_texts or {}).items():
            (build / name).write_text(text, encoding="utf-8")
        (build / "document.tex").write_text(tex, encoding="utf-8")

        result = subprocess.run(
            ["tectonic", "document.tex"], cwd=build, capture_output=True, text=True
        )
        if result.returncode != 0:
            log.error("tectonic failed for %s:\n%s", output_pdf.name, result.stderr)
            return False

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(build / "document.pdf"), str(output_pdf))
    log.info("Generated: %s", output_pdf.name)
    return True


def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "_", str(value).strip())
    value = re.sub(r"\s+", "_", value)
    return value[:150] or "document"


# -----------------------------------------------------------------------------
# Outlook
# -----------------------------------------------------------------------------

def outlook_client():
    import win32com.client  # Windows only; imported here so dry runs work anywhere
    return win32com.client.Dispatch("Outlook.Application")


def outlook_send(outlook, sender: str, recipient: str, subject: str, body_html: str, attachments=()):
    mail = outlook.CreateItem(0)
    mail.SentOnBehalfOfName = sender
    mail.To = recipient
    mail.Subject = subject
    mail.HTMLBody = body_html
    for path in attachments:
        mail.Attachments.Add(str(Path(path).resolve()))
    mail.Send()
