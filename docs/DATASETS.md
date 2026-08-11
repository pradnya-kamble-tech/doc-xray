# Doc-XRay — Dataset Research

This document records the public datasets evaluated for training and validating Doc-XRay's document type classifier. For the initial implementation we use a **keyword-scoring approach** (no fine-tuning of large models), so these datasets inform the vocabulary and class definitions rather than requiring full downloads.

---

## 1. RVL-CDIP

| Property | Detail |
|---|---|
| **Full name** | Ryerson Vision Lab Complex Document Information Processing |
| **URL** | https://www.cs.cmu.edu/~aharley/rvl-cdip/ |
| **Size** | 400,000 grayscale document images (16 classes × 25,000) |
| **Document types** | letter, memo, email, filefolder, form, handwritten, invoice, advertisement, budget, news article, presentation, scientific publication, questionnaire, resume/CV, scientific report, specification |
| **Labels** | 16 coarse-grained classes |
| **Format** | TIFF images + text labels (no OCR text supplied directly) |
| **License** | Freely available for non-commercial research |
| **Local dev subset** | A representative label list was used here. The full 400k image set is **not downloaded** (>40 GB). |
| **Usefulness for Doc-XRay** | Defines the canonical class taxonomy adopted for Doc-XRay: INVOICE, FORM, EMAIL, REPORT, ACADEMIC (from scientific publication/report). Confirms that a classifier should distinguish at least 8–16 document types. |

---

## 2. SROIE (Scanned Receipts OCR and Information Extraction)

| Property | Detail |
|---|---|
| **Full name** | ICDAR 2019 Robust Reading Challenge on Scanned Receipts OCR and IE |
| **URL** | https://rrc.cvc.uab.es/?ch=13 |
| **Size** | 626 training receipts, 347 test receipts |
| **Document types** | Grocery/retail receipts exclusively |
| **Labels** | Company name, date, address, total amount (key-value extraction) |
| **Format** | JPEG images + text box annotations + KV JSON |
| **License** | Public competition dataset, free for research |
| **Local dev subset** | Vocabulary (total, date, item, tax, receipt, amount, etc.) used directly to build RECEIPT classifier keywords. Images not downloaded. |
| **Usefulness for Doc-XRay** | Defines the key fields that should be present in a RECEIPT (total amount, date, vendor). Informs RECEIPT risk logic: flag if amount or date is missing/abnormal. |

---

## 3. CORD (Consolidated Receipt Dataset)

| Property | Detail |
|---|---|
| **Full name** | CORD: A Consolidated Receipt Dataset for Post-OCR Parsing |
| **URL** | https://github.com/clovaai/cord |
| **Size** | 1,000 Indonesian receipts (800 train / 100 val / 100 test) |
| **Document types** | Point-of-sale receipts |
| **Labels** | Hierarchical annotations: menu items, prices, sub-totals, totals, void, discount, tax |
| **Format** | JSON + images |
| **License** | Apache 2.0 |
| **Local dev subset** | JSON field taxonomy used to inform receipt keyword vocabulary. Full dataset not downloaded. |
| **Usefulness for Doc-XRay** | Reinforces RECEIPT class vocabulary and confirms that receipts should contain transaction details (items, prices, total, date, store name). The CORD label hierarchy directly mapped to Doc-XRay's RECEIPT anomaly detection rules (missing total → flag). |

---

## 4. FUNSD (Form Understanding in Noisy Scanned Documents)

| Property | Detail |
|---|---|
| **Full name** | FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents |
| **URL** | https://guillaumejaume.github.io/FUNSD/ |
| **Size** | 199 scanned forms (149 train / 50 test) |
| **Document types** | Administrative and bureaucratic forms |
| **Labels** | Linked key-value pairs with semantic roles (question, answer, header, other) |
| **Format** | JSON annotations on word-level bounding boxes + images |
| **License** | Public, research-only |
| **Local dev subset** | Vocabulary and field patterns used as inspiration for FORM class keywords. Images not downloaded. |
| **Usefulness for Doc-XRay** | Defines characteristics of forms: question/answer pairs, checkboxes, signature fields, required fields. Informs FORM risk logic: incomplete fields, missing signatures. |

---

## 5. Kleister-NDA (Legal Contracts)

| Property | Detail |
|---|---|
| **Full name** | Kleister NDA (Non-Disclosure Agreement) Dataset |
| **URL** | https://github.com/applicaai/kleister-nda |
| **Size** | 540 NDA documents |
| **Document types** | Non-Disclosure Agreements / legal contracts |
| **Labels** | Effective date, jurisdiction, party names, term of agreement (key-value) |
| **Format** | Plain text + JSON annotations |
| **License** | CC BY 4.0 — commercial and research use permitted |
| **Local dev subset** | Full text is small (~540 plain-text NDAs). Vocabulary extracted to build CONTRACT keyword set. Full download is optional (< 50 MB total). |
| **Usefulness for Doc-XRay** | Most directly relevant dataset. Defines NDA/contract language: indemnification, liability, confidential, termination, governing law, jurisdiction. Directly informs the CONTRACT risk rule set in risk_classifier.py. |

---

## Summary — Selected for Doc-XRay

| Dataset | Doc Types Used | How Used | Downloaded |
|---|---|---|---|
| RVL-CDIP | INVOICE, FORM, EMAIL, REPORT | Class taxonomy definition | Labels only (no images) |
| SROIE | RECEIPT | Keyword vocabulary for RECEIPT classifier | Vocabulary only |
| CORD | RECEIPT | Receipt field taxonomy → anomaly rules | Vocabulary only |
| FUNSD | FORM | Form field patterns | Vocabulary only |
| Kleister-NDA | CONTRACT | Contract keyword set; risk rules | Vocabulary only |

All vocabulary derived from these datasets is hardcoded into `services/document_classifier.py` and `services/risk_classifier.py`. **No large binary datasets are committed to this repository.**

The classifier uses a keyword-weighted scoring approach (no separate model training required), making it suitable for local Windows laptop development without GPU requirements.

---

## Document Types Supported by Doc-XRay

| Type | Emoji | Description |
|---|---|---|
| `RECEIPT` | 🧾 | Payment receipts, fee receipts, transaction records |
| `INVOICE` | 🧾 | Billing documents with line items and payment terms |
| `CONTRACT` | 📝 | Legal agreements, NDAs, service contracts |
| `FORM` | 📋 | Structured forms with fields to fill |
| `ACADEMIC` | 🎓 | Transcripts, certificates, academic records |
| `REPORT` | 📊 | Business/technical reports with metrics |
| `EMAIL` | 📧 | Email correspondence |
| `GENERAL` | 📄 | Unclassified or low-confidence documents |
