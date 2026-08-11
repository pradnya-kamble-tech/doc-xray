"""
Type-specific extraction engine for Document Intelligence Profiles (DIP).
Extracts key-value pairs (extracted_data) and actionable insights (recommended_actions) 
from text based on document_type using robust Regex heuristics.
"""
import re
from typing import Any

def extract_document_intelligence(text: str, document_type: str) -> dict[str, Any]:
    """
    Given the full document text and its detected type, returns the Document Intelligence Profile.
    Returns a dict with 'extracted_data' (dict) and 'recommended_actions' (list).
    """
    data: dict[str, str] = {}
    actions: list[str] = []
    
    text_clean = text.replace('\\n', ' ').strip()

    if document_type == "RECEIPT":
        # Amount
        amt_match = re.search(r'(?:Rs\.?|INR|\₹|Total Amount Paid:?|Amount Paid:?|Amount:?)\s*([0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if amt_match:
            data['Total Amount'] = f"Rs. {amt_match.group(1).strip()}"
        
        # Transaction ID
        txn_match = re.search(r'(?:Transaction ID|Txn ID|Reference|Ref No)[:\-]?\s*([A-Z0-9]+)', text, re.IGNORECASE)
        if txn_match:
            data['Transaction ID'] = txn_match.group(1).strip()
            
        # Receipt No
        rcpt_match = re.search(r'(?:Receipt No|Receipt Number)[:\-]?\s*([\w\-]+)', text, re.IGNORECASE)
        if rcpt_match:
            data['Receipt No'] = rcpt_match.group(1).strip()

        # Date
        date_match = re.search(r'(?:Date)[:\-]?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', text, re.IGNORECASE)
        if date_match:
            data['Date'] = date_match.group(1).strip()
            
        # Actions
        actions.append("Verify transaction ID matches bank records")
        actions.append("Ensure expense claim category is assigned")

    elif document_type == "INVOICE":
        inv_match = re.search(r'(?:Invoice No|Invoice Number)[:\-]?\s*([\w\-]+)', text, re.IGNORECASE)
        if inv_match:
            data['Invoice No'] = inv_match.group(1).strip()
            
        amt_match = re.search(r'(?:Total Amount Due|Total|Amount Due|Total Amount)[:\-]?\s*(?:Rs\.?|INR|\₹)?\s*([0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if amt_match:
            data['Amount Due'] = f"Rs. {amt_match.group(1).strip()}"
            
        date_match = re.search(r'(?:Invoice Date|Date)[:\-]?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', text, re.IGNORECASE)
        if date_match:
            data['Invoice Date'] = date_match.group(1).strip()
            
        due_match = re.search(r'(?:Due Date)[:\-]?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', text, re.IGNORECASE)
        if due_match:
            data['Due Date'] = due_match.group(1).strip()
            
        gst_match = re.search(r'(?:GSTIN)[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})', text, re.IGNORECASE)
        if gst_match:
            data['GSTIN'] = gst_match.group(1).strip()
            
        po_match = re.search(r'(?:Purchase Order|PO Reference|PO No)[:\-]?\s*([\w\-]+)', text, re.IGNORECASE)
        if po_match:
            data['PO Reference'] = po_match.group(1).strip()

        actions.append("Schedule payment before due date to avoid late fees")
        actions.append("Verify GSTIN validity on government portal")
        actions.append("Match PO Reference with internal purchase orders")

    elif document_type == "CONTRACT":
        # Basic heuristic for Party A and B in NDA/Contracts
        party_match = re.findall(r'(?:Party A|Party B|between)(?:[:,\s]*)([A-Z][a-zA-Z\s.,]+(?:Ltd\.|Inc\.|LLC|Corp|Group))', text)
        if len(party_match) >= 1:
            data['Primary Party'] = party_match[0].strip()
        if len(party_match) >= 2:
            data['Secondary Party'] = party_match[1].strip()
            
        date_match = re.search(r'(?:Effective Date|entered into as of)\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})', text, re.IGNORECASE)
        if date_match:
            data['Effective Date'] = date_match.group(1).strip()
            
        term_match = re.search(r'(?:period of|term of)\s+([A-Za-z0-9\-]+\s*(?:years|months|days))', text, re.IGNORECASE)
        if term_match:
            data['Duration/Term'] = term_match.group(1).strip()
            
        jurisdiction_match = re.search(r'(?:jurisdiction of the courts of|laws of)\s+([A-Z][a-zA-Z\s]+)', text, re.IGNORECASE)
        if jurisdiction_match:
            data['Jurisdiction'] = jurisdiction_match.group(1).strip()
            
        actions.append("Review 'Indemnification' and 'Limitation of Liability' clauses carefully")
        actions.append("Ensure legal team signs off on jurisdiction terms")
        actions.append("Add expiration/renewal dates to corporate calendar")

    elif document_type == "ACADEMIC":
        name_match = re.search(r'(?:Name|Student Name)[:\-]?\s*([A-Z][a-zA-Z\s]+)', text)
        if name_match:
            data['Student Name'] = name_match.group(1).strip()
            
        roll_match = re.search(r'(?:Roll No|Enrolment No|Registration No)[:\-]?\s*([\w\-\/]+)', text, re.IGNORECASE)
        if roll_match:
            data['Roll Number'] = roll_match.group(1).strip()
            
        prog_match = re.search(r'(?:Programme|Course|Degree)[:\-]?\s*([A-Za-z\s\(\)]+)', text)
        if prog_match:
            data['Programme'] = prog_match.group(1).strip()
            
        gpa_match = re.search(r'(?:SGPA|CGPA|Overall C\.G\.P\.A\.)[:\-]?\s*([0-9\.]+)\s*(?:/|\s*out of\s*)\s*([0-9\.]+)', text, re.IGNORECASE)
        if gpa_match:
            data['GPA'] = f"{gpa_match.group(1)} / {gpa_match.group(2)}"
            
        actions.append("Verify institutional seal or digital signature authenticity")
        actions.append("Cross-check roll number against university records")

    elif document_type == "FORM":
        actions.append("Check for any missing required fields")
        actions.append("Validate applicant signature presence")

    elif document_type == "REPORT":
        actions.append("Extract key performance metrics for presentation")
        actions.append("Distribute to relevant department stakeholders")
        
    elif document_type == "EMAIL":
        date_match = re.search(r'(?:Date|Sent)[:\-]?\s*([A-Za-z0-9\s:,]+)', text)
        if date_match:
            data['Date Sent'] = date_match.group(1).strip()
            
        actions.append("Scan for action items and deadlines")
        actions.append("Verify sender address for phishing indicators")

    else:
        actions.append("Extract entities for generic categorisation")
        actions.append("Assign document to appropriate knowledge base folder")
        
    # Apply cleanup — remove empty fields or trailing spaces
    data = {k: v.strip() for k, v in data.items() if v and isinstance(v, str)}

    return {
        "extracted_data": data,
        "recommended_actions": actions
    }
