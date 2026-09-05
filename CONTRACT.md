# The row contract

One bank-statement transaction, as it moves through the pipeline. Every workstream reads
and writes this shape. It is fixed: change it only by agreement with all four owners.

```json
{
  "row_id": 17,
  "source": { "pdf": "20260331_NI_V_SCSP_CALDER_EUR_030041.pdf", "page": 2 },
  "raw": {
    "account_name": "NI V SCSP",
    "account_number": "240-644826-130",
    "currency": "EUR",
    "bank_reference": "10716RS62GWQ",
    "narrative_raw": "NI ABF I SCSP, PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR PURCHASE...",
    "narrative_normalised": "NI ABF I SCSP PMT FRM NI ABF II SCSP TO NI ABF I SCSP FOR PURCHASE...",
    "value_date": "2026-03-05",
    "post_date": "2026-03-05",
    "credit": null,
    "debit": -301908.70,
    "balance": 20088.76
  },
  "fields": {
    "matched_sender_beneficiary": {
      "value": "NI ABF I SCSp",
      "confidence": 0.91,
      "status": "auto",
      "evidence": {
        "span": [0, 13],
        "text": "NI ABF I SCSP",
        "source_list": "Legal Entity Master List"
      },
      "alternatives": [ { "value": "NI ABF II SCSp", "confidence": 0.44 } ]
    }
  }
}
```

## Rules

1. **No bare strings.** Every entry in `fields` is a `Field`: `value`, `confidence`,
   `status`, `evidence`, `alternatives`.
2. **`status` is one of `auto`, `needs_review`, `unresolved`.** The review UI orders on this.
3. **`evidence.span` is a character offset into `narrative_raw`**, not the normalised form.
   The UI highlights the raw text, so offsets must survive normalisation.
4. **`alternatives` is what the reviewer chooses from** when rejecting a proposal. Populate it
   even when confident — an empty list means the reviewer has to type.

## The eight fields to fill

| Field key | Difficulty | Human filled (of 100) |
|---|---|---|
| `matched_legal_entity`         | free        | 100 |
| `cash_leg_transtype`           | free        | 100 |
| `counterparty_transtype`       | medium      | 100 |
| `matched_project_code`         | medium      | 100 (30 are "Flag for review - no project match") |
| `classification`               | medium      | 100 |
| `pulled_out_sender_beneficiary`| hard        |  55 |
| `matched_sender_beneficiary`   | hard        |  48 |
| `resolved_position` / `resolved_deal` | hard |  30 |
