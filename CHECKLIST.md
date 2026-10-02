# Event checklist

Copy this file for each event and tick items off as you go. Items marked
**(script)** have a command; details are in the [README](README.md)
section given in brackets. Everything else is manual.

---

## 1. Early planning (6–12 months before)

- [ ] Fix dates, venue and approximate participant numbers.
- [ ] Draft a budget: income (registration fees, sponsors / grants) against
      costs (venue, catering, excursion, social events, merchandise, printing).
- [ ] Apply for sponsorship or funding. Note any conditions, e.g. logos on the
      website and programme, or a membership requirement for fee waivers.
- [ ] Decide the registration fee, what it includes (meals? excursion? Any goodies?) and
      the fee-waiver policy.
- [ ] Create the event website.
- [ ] If excursion or goodies are there, make a tentative plan and start orders
- [ ] Fill in `config.toml` (README §2), including the logo and signature paths.

## 2. Registration open

- [ ] Duplicate and update the registration and payment-confirmation forms (README §4.1).
- [ ] Put the form links on the website and announce the event.
- [ ] As requests come in: generate invitation letters **(script)**
      `python invitation_letters/generate_letters.py` (README §4.2).
- [ ] Decide fee waivers. Mark them `yes` in the export's *Fee Waived* column.

## 3. Registration closed

- [ ] Export the responses to `data/registration_form_export.xlsx`. Remove
      cancellations, and keep removing them as they arrive (README §3).
- [ ] Abstract review: score, decide, assign formats (README §4.3).
- [ ] Decide the technical sessions: names, formats, talk lengths, chairs.
- [ ] Decide the discussion-session themes.
- [ ] Draft the programme from `schedule/schedule_template.docx`, then save it
      as PDF and set `[email] schedule_pdf`.
- [ ] Record accepted formats in *Presentation Format*. Regenerate the
      visa/travel letters that should mention the accepted abstract
      **(script)** `--overwrite`.
- [ ] Generate invoices **(script)** `python invoices/generate_invoices.py` (README §4.4).
- [ ] Send invoices and fee-waiver emails **(script)**: dry run first, then `--send`.

## 4. Payments

- [ ] Check bank receipts against the invoices and the payment-confirmation
      form responses (README §4.5).
- [ ] Chase missing payments, including institutional ones such as purchase
      orders or invoicing portals.
- [ ] Follow up fee-waived participants who have not filled in the confirmation form.

## 5. Venue, food and accommodation

- [ ] Confirm which meals and breaks are included in the fee.
- [ ] Send dietary requirements to the venue / hotel. Flag allergies and
      coeliac disease explicitly.
- [ ] Collect accessibility requirements from the registration form.
- [ ] Finalise rooms: room types, sharing preferences, arrival / departure dates.
- [ ] Book the session rooms: plenary, posters, breakout and splinter
      meetings. Check AV and internet.
- [ ] Give the venue the poster day and the number of posters. Check the
      poster-board size.
- [ ] Tell the venue about any change to break or meal times.
- [ ] Put the accommodation details into `[accommodation]`.

## 6. Programme extras

- [ ] Online meeting link for hybrid or online sessions. Put it on the website.
- [ ] Participant chat channel (e.g. Slack). Send the invite link.
- [ ] Excursion: book in advance (tickets, transport, guide). Check the cost per person.
- [ ] Social events (ice breaker, dinner, party, quiz): plan and book.
- [ ] Mentorship lunches:
  - [ ] Confirm the mentors.
  - [ ] Assign mentees, not to a mentor from their own organisation.
  - [ ] Book the tables.
- [ ] Merchandise or gifts: order, split what is shipped and what is carried,
      and invoice anyone who buys extra.
- [ ] Sponsor branding on the website, programme and slides.

## 7. Final information email to participants (1–2 weeks before)

- [ ] Final programme (PDF, or a non-editable version online).
- [ ] Arrival information:
  - [ ] check-in and check-out times
  - [ ] luggage storage
  - [ ] whom to tell about late arrival
  - [ ] travel directions
- [ ] Talk lengths for each format, including question time.
- [ ] Poster size and orientation. Tell people to print at home if there is
      no printing on site.
- [ ] Links to the chat channel and the online meeting.
- [ ] Weather, clothing and footwear (especially for excursions), and a packing list.
- [ ] Sponsor conditions, e.g. a membership reminder.

## 8. Just before / during the event

- [ ] Print the certificate blanks and any signs, name badges or attendance lists.
      Pack paper, pens and adapters.
- [ ] Bring the merchandise or gifts.
- [ ] Record attendance in the export's *Attended* column.

## 9. After the event

- [ ] Certificates **(script)** `python certificates/generate_certificates.py` (README §4.7).
- [ ] Settle the venue and supplier invoices. Reconcile the budget.
- [ ] Write the event report for sponsors and funders: numbers, programme,
      outcomes, photos.
- [ ] Thank-you email with the slides or poster collection and any feedback survey if required.
- [ ] Delete personal data after the retention period.

---

