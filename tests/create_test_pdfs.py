"""Create test PDF files for pipeline testing."""
import fitz  # PyMuPDF
import sys

def create_pdf(filename, pages_content):
    doc = fitz.open()
    for text in pages_content:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=11)
    doc.save(filename)
    doc.close()
    print(f"Created: {filename}")


# 1. Receipt PDF
receipt_text = """RECEIPT
Store: QuickMart Supermarket
Address: 123 Main Street, Springfield
Date: 2026-08-10
Receipt #: RCP-2024-88421

Items:
1. Organic Milk (1 gal)          $5.99
2. Whole Wheat Bread             $3.49
3. Fresh Salmon (2 lbs)          $18.99
4. Avocados (3 pk)               $4.99
5. Coffee Beans (12 oz)          $12.49
6. Greek Yogurt (6 pk)           $6.99

Subtotal:                       $52.94
Tax (8.25%):                     $4.37
Total:                          $57.31

Payment Method: Visa ending in 4521
Transaction ID: TXN-9987123456
Vendor: QuickMart Inc.
Tax ID: 45-1234567

Thank you for shopping with us!
"""

# 2. Contract PDF
contract_text = """PROFESSIONAL SERVICES AGREEMENT

This Services Agreement ("Agreement") is entered into as of August 1, 2026,
by and between TechCorp Solutions Inc. ("Company"), located at 500 Innovation Drive,
San Jose, CA 95134, and DataFlow Consulting LLC ("Contractor"),
located at 200 Market Street, San Francisco, CA 94105.

ARTICLE 1 - SCOPE OF SERVICES
The Contractor agrees to provide software development and consulting services
as described in Exhibit A attached hereto. Services shall include but not be
limited to: system architecture design, API development, database optimization,
and security auditing.

ARTICLE 2 - COMPENSATION
The Company shall pay Contractor a fixed fee of $150,000 (One Hundred Fifty
Thousand Dollars) for all services rendered under this Agreement. Payment shall
be made in three installments: 40% upon execution, 30% at midpoint, and 30%
upon completion.

ARTICLE 3 - TERM AND TERMINATION
This Agreement shall commence on August 1, 2026, and shall continue for a
period of twelve (12) months. Either party may terminate this Agreement with
thirty (30) days written notice. Upon termination, the Contractor shall be
entitled to payment for all services rendered up to the date of termination.

ARTICLE 4 - CONFIDENTIALITY
Both parties agree to maintain strict confidentiality of all proprietary
information, trade secrets, and business data disclosed during the term of
this Agreement. This obligation survives termination for a period of five (5) years.

ARTICLE 5 - LIMITATION OF LIABILITY
IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF THIS AGREEMENT.
The total liability shall not exceed the total compensation paid under this Agreement.

ARTICLE 6 - GOVERNING LAW
This Agreement shall be governed by the laws of the State of California.

ARTICLE 7 - INDEMNIFICATION
Each party shall indemnify and hold harmless the other party from any claims,
damages, or expenses arising from the indemnifying party's breach of this Agreement.

SIGNED:
_________________________    _________________________
TechCorp Solutions Inc.      DataFlow Consulting LLC
Date: August 1, 2026        Date: August 1, 2026
"""

# 3. General PDF (report)
general_text = """QUARTERLY PERFORMANCE REPORT
Q2 2026 - Engineering Division

Executive Summary:
The engineering division achieved significant milestones during Q2 2026,
delivering three major product releases and reducing technical debt by 23%.
Team productivity increased by 15% compared to Q1, as measured by velocity metrics.

Key Achievements:
1. Launched v3.0 of the core platform with 99.97% uptime
2. Reduced average API response time from 450ms to 120ms
3. Completed migration of 2.3 million user accounts to new auth system
4. Implemented automated CI/CD pipeline reducing deployment time by 60%

Team Metrics:
- Sprint velocity: 142 story points (up from 123 in Q1)
- Bug resolution time: 4.2 hours average (down from 7.8 hours)
- Code review turnaround: 2.1 hours average
- Test coverage: 87% (target: 85%)

Challenges and Risks:
- Database scaling concerns for projected Q3 growth
- Two senior engineers departing, knowledge transfer in progress
- Legacy API deprecation timeline may need extension

Budget Overview:
Allocated: $2,400,000
Spent: $2,180,000
Remaining: $220,000
Utilization: 90.8%

Q3 Priorities:
1. Database sharding implementation
2. Mobile app redesign launch
3. SOC 2 Type II compliance audit
4. Hiring 3 senior engineers

Prepared by: Engineering Leadership Team
Date: July 2026
"""

# 4. Invoice PDF
invoice_text = """INVOICE
WebDesign Pros LLC
404 Creativity Ave, New York, NY 10001
Date: 2026-08-15
Invoice #: INV-2026-0081

Bill To: Acme Corp
Attn: Accounts Payable

Services Provided:
1. Website Redesign            $4,500.00
2. SEO Optimization            $1,200.00
3. Monthly Hosting (Aug)       $150.00

Subtotal:                      $5,850.00
Tax (0%):                      $0.00
Total Due:                     $5,850.00

Please remit payment within 30 days.
"""

# 5. Academic PDF
academic_text = """RESEARCH PAPER: QUANTUM ALGORITHMS
Abstract
This paper presents a novel approach to quantum error correction protocols 
that achieves a 15% reduction in physical qubit overhead.

1. Introduction
Quantum computing holds immense promise for cryptography and material science.
However, error rates in NISQ devices remain a challenge. 
Our proposed protocol, Q-Shield, addresses surface code inefficiencies.

2. Methodology
We simulated 10,000 circuits using Qiskit. 
Parameters: T1=50us, T2=50us, 2-qubit gate error 0.1%.

3. Results
The Q-Shield protocol outperformed standard Steane codes in all regimes.
Threshold improved from 1.2% to 1.45%.
"""

create_pdf(sys.argv[1] + "/test_receipt.pdf", [receipt_text])
create_pdf(sys.argv[1] + "/test_contract.pdf", [contract_text[:2000], contract_text[2000:]])
create_pdf(sys.argv[1] + "/test_general.pdf", [general_text])
create_pdf(sys.argv[1] + "/test_invoice.pdf", [invoice_text])
create_pdf(sys.argv[1] + "/test_academic.pdf", [academic_text])

print("All 5 test PDFs created successfully!")
