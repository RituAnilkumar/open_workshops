# open_workshops

Templates and scripts for organising a workshop or conference: registration
forms, abstract review, programme schedule, invitation letters, invoices,
registration emails and certificates of participation.

Nothing in here is tied to a particular event, organisation or person:

- All event-specific details live in **`config.toml`**.
- The participant list is the **registration-form export** in `data/`.

For a step-by-step to-do list covering everything, including the manual
logistics, see **[CHECKLIST.md](CHECKLIST.md)**. This allows you to check items that are completed if you open it in Notion or any other supported app.

---

## Contents

```
open_workshops/
├── README.md                    ← this file: setup, config, how each part works
├── CHECKLIST.md                 ← to-do list for the whole event, in order
├── config.toml                  ← fill this in first (all event details)
├── environment.yml              ← conda environment for the scripts
├── workshop_tools.py            ← shared code used by all scripts
├── assets/                      ← optional place for logos / signature (paths are set in config)
├── data/                        ← registration-form export (= participant list)
│   └── registration_form_export_example.xlsx
├── abstract_review/
│   └── abstract_review_template.xlsx   ← review sheet + session planning (manual)
├── schedule/
│   └── schedule_template.docx          ← programme layout (manual, Word)
├── invitation_letters/
│   ├── letter_visa_travel.tex   ← visa / travel-funding letter (LaTeX)
│   ├── letter_funder.tex        ← letter for employers / funders (LaTeX)
│   └── generate_letters.py      ← registration export → letter PDFs
├── invoices/
│   ├── invoice_template.tex, letterhead.lco   ← invoice layout (LaTeX)
│   ├── emails/invoice_email.html, waiver_email.html
│   ├── generate_invoices.py     ← registration export → invoice PDFs
│   └── send_registration_emails.py  ← emails invoices / fee waivers via Outlook
└── certificates/
    ├── certificate_template.tex             ← "plain" design (can include talk title)
    ├── certificate_template_decorative.tex  ← "decorative" design
    └── generate_certificates.py
```

---

## 1. One-time setup

1. Install [Miniconda/Anaconda](https://docs.conda.io/) if not already installed.
2. Create the environment (from this folder):
   ```
   conda env create -f environment.yml
   conda activate open-workshops
   ```
3. The first LaTeX compile downloads the LaTeX packages it needs, so it requires
   an internet connection once.

Sending emails needs Windows with Outlook. The letters and invoices use the
Calibri font, which ships with Windows/Office; on other systems change it to
an installed font (e.g. Carlito) at the top of the `.tex` / `.lco` files.

---

## 2. Fill in `config.toml`

Open `config.toml` and replace every value that starts with `TODO`. The scripts
stop with a list of the missing values if anything they need is still `TODO`,
so nothing half-filled is ever produced or sent.

| Section | What it is | Used in |
|---|---|---|
| `[event]` | Event name, type (workshop / conference …), start and end dates, short date range, optional programme note | everything |
| `[venue]` | Venue name, city, country | letters, invoices, emails, certificates |
| `[accommodation]` | Where participants stay, the expected cost, optional email note | visa/travel letter, emails |
| `[letters]` | Period the visa/travel letter covers, letter date, optional partner logo, keywords that pick the letter type from the form answer | letters |
| `[signatory]` | Who signs: name, position, affiliation, optional signature image | letters, invoices, certificates |
| `[organiser]` | Legal body issuing invoices: name, address, contact, optional registration / tax details and VAT note, logo | letters, invoices, certificates |
| `[bank]` | Account for registration payments | invoices |
| `[registration]` | Fee, currency, payment deadline, invoice-number format, link to the payment-confirmation form | invoices, emails |
| `[fee_waiver]` | Optional: who funds fee waivers and any condition attached (e.g. a membership requirement + link) | waiver email |
| `[email]` | Sender address and name, delay between emails, optional programme PDF to attach, subject lines | emails |
| `[schedule]` | `PRELIMINARY` makes the emails call the attached programme tentative; `""` once final | emails |
| `[certificates]` | Date printed on certificates, certificate-number format, design (`plain` / `decorative`) | certificates |
| `[files]` | Where the registration export is | all scripts |
| `[columns]` | Column headings in the registration export (defaults match the template form) | all scripts |

**Logos and signature:** set the paths to the image files (PDF, PNG or JPG):
- `[organiser] logo` appears on letters, invoices and certificates.
- `[letters] partner_logo` appears top right on the letters.
- `[signatory] signature_image` appears on letters, invoices and certificates.

Paths can be relative to this folder (e.g. `"assets/logo.pdf"`) or absolute
(e.g. `"C:/Users/me/Pictures/logo.png"`; use forward slashes). Leave a path as
`""` to show no image.

**Invoice and certificate numbers:** `[registration] invoice_number_format`
and `[certificates] number_format` contain a group of N's. That group is
replaced by the participant's form response **ID**, zero-padded to the
number of N's. For example, `ABC_2027_NNN` becomes `ABC_2027_005` for
response ID 5. Because the ID never changes, removing cancelled participants
never renumbers anyone. Put a separator before the N's (`_`, `-`) so the
number cannot run into letters of the prefix.

### Placeholders

Every config value is available as a placeholder `<<<SECTION_KEY>>>` in upper
case, e.g. `[event] name` → `<<<EVENT_NAME>>>`, `[signatory] title` →
`<<<SIGNATORY_TITLE>>>`. Config values may themselves contain placeholders
(e.g. the email subjects contain `<<<EVENT_NAME>>>`).

The scripts fill these per-participant placeholders from the registration
export:

| Placeholder | Source |
|---|---|
| `<<<PARTICIPANT_NAME>>>`, `<<<PARTICIPANT_EMAIL>>>` | name and email columns |
| `<<<PARTICIPANT_AFFILIATION>>>` | the affiliation exactly as entered |
| `<<<PARTICIPANT_ORGANISATION>>>`, `<<<PARTICIPANT_COUNTRY>>>` | the affiliation, split at its last comma |
| `<<<INVOICE_NUMBER>>>`, `<<<CERTIFICATE_NUMBER>>>` | the number formats above, using the response ID |
| `<<<TALK_TITLE>>>` | presentation-title column |

Placeholders ending in `_TEX` or `_HTML` (e.g. `<<<LOGO_TEX>>>`) are
generated by the scripts. Leave them in the templates.

---

## 3. The participant list: the registration export

Every script reads `data/registration_form_export.xlsx`, the Excel export of
the registration form ([files] `registration_export`). There is no separate
participant list to maintain.

- **Cancellations:** delete that person's row from the export. Every script
  re-reads the file each time it runs, so cancelled people simply disappear
  from letters, invoices, emails and certificates.
- **Columns you add yourself** (optional; names set in `[columns]`):

| Column | Meaning |
|---|---|
| `Fee Waived` | `yes` = no invoice; the fee-waiver email is sent instead |
| `Presentation Format` | Accepted format (e.g. `Oral`, `Poster`). If filled, the visa/travel letter states that the abstract was accepted. |
| `Attended` | After the event: if this column exists, only `yes` rows get a certificate |

See `data/registration_form_export_example.xlsx` for the expected layout.

If your form asks for the country separately, set `[columns] country` to that
column's heading. Otherwise the country is taken from the affiliation after
its last comma, which is the format the template form asks for:
"Institute, University, Country".

---

## 4. Workflow

Run all commands from this folder with the environment activated. Steps
marked **(manual)** need human judgement.

### 4.1 Registration and abstract submission (forms)

Template Microsoft Forms from a previous event are available to copy. Request
access from the link owner if you cannot open them:

- Registration form: <https://forms.cloud.microsoft/Pages/ShareFormPage.aspx?id=MH_ksn3NTkql2rGM8aQVG29GXOXNlpdMsjOTkve2krBUM1kzTkRBSVRNV0owSjVTQjA5TTRDVDZMOS4u&sharetoken=z0AFNh0kRc7Z3A6eivUc>
- Payment confirmation form: <https://forms.cloud.microsoft/Pages/ShareFormPage.aspx?id=MH_ksn3NTkql2rGM8aQVG29GXOXNlpdMsjOTkve2krBUODRRQzNUQTlSM0VJRlpYVUhVU1RVWkNDSS4u&sharetoken=7t9rfnDaIEE2uRzEK8BF>

After duplicating them:
1. Update the event details in the forms.
2. Put the payment-confirmation link into `[registration] payment_form_url`.
3. When registration closes, export the responses to Excel as
   `data/registration_form_export.xlsx`.
4. Remove the rows of everyone who has cancelled (e.g. by email). Keep doing
   this whenever further cancellations arrive.

If you change question wording in the form, update the matching headings in
`[columns]`.

### 4.2 Invitation letters

```
python invitation_letters/generate_letters.py            # → invitation_letters/output/<ID>_<name>_<type>.pdf
```
The letter type comes from each person's answer to the invitation-letter
question:

| Answer contains | Letter | Content |
|---|---|---|
| `[letters] visa_keyword` (default `visa`) | `letter_visa_travel.tex` | Invitation for visa / travel funding: accommodation details, extended travel period. If the person has a *Presentation Format*, it also says their abstract was accepted. |
| `[letters] funder_keyword` (default `funding`) | `letter_funder.tex` | Confirmation of participation for an employer or funder |

- Someone who asked for both letters gets both.
- `--only <IDs or emails>` limits a run to some people.
- `--only 12 --type visa` makes a letter for someone who did not ask for one on the form.
- Existing letters are skipped. Use `--overwrite` to rebuild them, e.g. after
  accepting an abstract.
- To change the wording, edit the `.tex` files. Keep the `<<<...>>>` placeholders.

### 4.3 Abstract review, technical sessions and programme (manual)

There are templates for these, but no scripts:

1. **Review:** copy `abstract_review/abstract_review_template.xlsx` to `data/`.
   - Paste the presenters, titles and abstracts from the export into the
     *Review* sheet.
   - Score relevance and quality, then record the decision and the assigned
     format and session. The sheet has drop-down lists for these.
2. **Sessions:** list the technical sessions with their names, formats, talk
   lengths, chairs and times in the *Sessions* sheet.
3. **Programme:** copy `schedule/schedule_template.docx` and fill it in.
   - It already has one row of each kind: day, session heading, talk, break,
     and plenary/social.
   - Copy rows (select the row → Ctrl+C → Ctrl+V) to add more.
   - Save it as PDF.
4. Copy the *Assigned Format* of accepted presenters into the export's
   *Presentation Format* column. Then re-run the letters with `--overwrite`
   for anyone whose visa/travel letter should mention the accepted abstract.
5. To attach the programme PDF to the registration emails, set its path in
   `[email] schedule_pdf`.

### 4.4 Invoices and registration emails

```
python invoices/generate_invoices.py                       # → invoices/output/<invoice number>.pdf
python invoices/send_registration_emails.py                # DRY RUN: lists what would be sent
python invoices/send_registration_emails.py --preview preview.html   # look at one email in a browser
python invoices/send_registration_emails.py --send         # actually sends
```
- Everyone gets an invoice for the registration fee, except those marked
  *Fee Waived*. They get the fee-waiver email instead of an invoice.
- **Nothing is emailed without `--send`.** Always do a dry run first.
- `--only <invoice numbers or emails>` limits a run to some people, e.g. late registrants.
- `--kind invoice` or `--kind waiver` limits a run to one email type.
- `generate_invoices.py` skips invoices that already exist. Use `--overwrite` to rebuild them.
- To change the wording, edit `invoices/invoice_template.tex` and
  `invoices/emails/*.html`.

### 4.5 Payment check (manual)

Participants fill in the payment-confirmation form after paying. No script
reads its responses: they are for you. Compare them, and the invoice
numbers, against the bank statements of the organiser's account. Chase
anyone missing.

### 4.6 Venue booking and accommodation (manual)

See the *Venue, food and accommodation* section of [CHECKLIST.md](CHECKLIST.md).
Put the accommodation name and cost into `[accommodation]`. They are used by
the visa/travel letter and the emails.

### 4.7 Certificates of participation

After the event, add an *Attended* column to the export and mark who came. Then run:
```
python certificates/generate_certificates.py
```
This creates:
- one PDF per participant in `certificates/output/`
- two blank fill-in-by-hand certificates, for on-site sign-ups
- `certificates/certificates_for_printing.pdf`, with all participant
  certificates merged into one file

Choose the design with `[certificates] design`.

---

## Personal data

`data/` and all `output/` folders contain personal data (names, emails,
affiliations). Keep them out of anything shared publicly. The included
`.gitignore` does this if the folder is ever put under git. Delete them after
the retention period stated in your registration form's privacy notice.
