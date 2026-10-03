"""Sample email dataset generator creating realistic .eml, .json, and .txt files for IT and Corporate Actions workflows."""

from __future__ import annotations
import argparse
from email.message import EmailMessage as PyEmailMessage
import json
from pathlib import Path
import sys

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_emails"
CORPORATE_ACTIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "corporate_actions_emails"

SAMPLE_EMAILS = [
    {
        "filename": "01_security_breach_alert.eml",
        "format": "eml",
        "subject": "CRITICAL: Potential unauthorized credential dump and database breach detected",
        "from": "sec-alerts@external-watchdog.io",
        "to": "security@acmecorp.com",
        "date": "Sat, 03 Oct 2026 09:15:00 +0000",
        "body": """Hello Security Team,

Our threat intelligence monitoring has detected plaintext API credentials and session tokens matching your production cluster on a public pastebin.

Immediate action is recommended:
1. Revoke the master API keys for cluster `us-east-prod-04`.
2. Inspect audit logs for unauthorized exports during the last 6 hours.
3. Lock down exposed endpoints immediately.

Please acknowledge receipt as soon as possible.

Best,
Sentinel Threat Research Unit""",
    },
    {
        "filename": "02_production_outage_bug.eml",
        "format": "eml",
        "subject": "URGENT: Checkout API returning 500 Internal Server Error for all users",
        "from": "ops-lead@globalretail.com",
        "to": "support@acmecorp.com",
        "date": "Sat, 03 Oct 2026 10:02:15 +0000",
        "body": """Hi Support,

Since approximately 09:45 AM UTC, our customers are unable to complete any checkout transactions. Every request to `/api/v2/payments/charge` fails with HTTP 500.

This is causing an active revenue loss of ~$15,000 per hour.

Error excerpt:
`NullPointerException at PaymentGatewayAdapter.java:142`

Please engage your engineering on-call immediately.

Regards,
Alex Chen, Head of Engineering""",
    },
    {
        "filename": "03_enterprise_demo_request.eml",
        "format": "eml",
        "subject": "Inquiry regarding Enterprise Tier licensing for 750 seats",
        "from": "marcus.vance@megacorp-logistics.com",
        "to": "sales@acmecorp.com",
        "date": "Fri, 02 Oct 2026 16:30:00 +0000",
        "body": """Hello Acme Sales Team,

We are currently evaluating workflow orchestration solutions for our global supply chain division. We currently have 750 team members who will require daily access.

Could we schedule a product demonstration next Tuesday or Wednesday with an Enterprise Solution Architect? We also would like to discuss custom SLA terms, SOC2 compliance reports, and volume pricing.

Looking forward to your response.

Marcus Vance
VP of Technology Procurement""",
    },
    {
        "filename": "04_disputed_invoice_billing.json",
        "format": "json",
        "data": {
            "id": "INV-DISP-88219",
            "subject": "Discrepancy and double charge on Invoice #INV-2026-9041",
            "from": "accounting@zenithdesign.studio",
            "to": "billing@acmecorp.com",
            "date": "Sat, 03 Oct 2026 08:12:44 +0000",
            "body": "Hi Acme Billing,\n\nWe noticed that our credit card ending in 4109 was charged twice for $1,450 on October 1st for the annual Pro subscription renewal. We should have only been billed once.\n\nCould you please investigate this duplicate charge and issue a prompt refund for the second transaction?\n\nAttached is our credit card statement screenshot.\n\nThank you,\nSarah Lin\nController, Zenith Studio",
        },
    },
    {
        "filename": "05_dark_mode_feature_request.json",
        "format": "json",
        "data": {
            "id": "FEAT-REQ-3011",
            "subject": "Feature Request: Native Dark Mode and Keyboard Shortcuts in Dashboard",
            "from": "dev-user@community-forum.org",
            "to": "feedback@acmecorp.com",
            "date": "Thu, 01 Oct 2026 14:05:00 +0000",
            "body": "Hey team!\n\nLove using your product every day. One request: when working late in low light environments, the bright white dashboard gets tiring on the eyes. Would it be possible to add a native dark theme toggle and vim-style keyboard navigation for switching between pipelines?\n\nKeep up the great work!\nCheers,\nDave",
        },
    },
    {
        "filename": "06_cold_marketing_spam.txt",
        "format": "txt",
        "text": """From: growth-guru@fastlead-booster.xyz
To: info@acmecorp.com
Subject: Skyrocket your B2B sales leads with AI scraping in 30 days guaranteed!!

Hey CEO,

Are you tired of low conversion rates? Our automated lead engine scours LinkedIn to deliver 5,000 verified decision maker contacts every single week for just $49/mo.

Click here to claim your 50% discount: https://bit.ly/spam-unsub-993

Unsubscribe by replying STOP.""",
    },
    {
        "filename": "07_urgent_vip_escalation.eml",
        "format": "eml",
        "subject": "SLA BREACH: Unresolved ticket #49120 and contract cancellation notice",
        "from": "csuite@titan-financial.com",
        "to": "escalations@acmecorp.com",
        "date": "Sat, 03 Oct 2026 10:45:10 +0000",
        "body": """To Whom It May Concern,

Our priority ticket #49120 regarding data ingestion synchronization has now been unresponsive for over 48 hours, violating section 4.2 of our Platinum SLA contract.

If this issue is not escalated to your VP of Support and resolved by end of business today, our legal counsel has instructed us to initiate formal contract termination.

We expect a phone call from executive management within the next two hours.

Sincerely,
Elena Rostova, Chief Operations Officer""",
    },
]

CORPORATE_ACTIONS_EMAILS = [
    {
        "filename": "00_urgent_merger_attached_proxy.eml",
        "format": "eml",
        "subject": "Urgent: Action Required for ABC Corp Merger",
        "from": "proxy-alerts@custodian.com",
        "to": "ca-ops@apexcapital.com",
        "date": "Sat, 03 Oct 2026 11:00:00 +0000",
        "body": "Please review the attached corporate proxy document for restructuring options.",
        "attachments": [
            {
                "filename": "abc_corp_merger_proxy.pdf",
                "content_type": "application/pdf",
                "data": b"%PDF-1.4 ABC Corp Merger Restructuring Proxy Document Options: Option 1 Cash $48.50, Option 2 Stock 1.15 Delta Tech shares. Deadline 05-OCT-2026.",
            }
        ],
    },
    {
        "filename": "01_voluntary_tender_offer_deadline.eml",
        "format": "eml",
        "subject": "URGENT ELECTION: Voluntary Tender Offer for Quantum Dynamics Corp (ISIN: US74765A1022) - Expiration 04-Oct-2026 17:00 EST",
        "from": "custody-notifications@bnymellon.com",
        "to": "ca-ops@apexcapital.com",
        "date": "Sat, 03 Oct 2026 09:30:00 +0000",
        "body": """Dear Client,

Please be advised of an urgent VOLUNTARY CORPORATE ACTION regarding your holdings:

Security: QUANTUM DYNAMICS CORP COM (ISIN: US74765A1022 / CUSIP: 74765A102)
Event Type: Voluntary Tender Offer / Takeover Bid
Offeror: Hyperion Capital Holdings LLC
Consideration: USD 54.00 Cash per Common Share, OR 1.25 Hyperion Common Shares (US449102108) per Share tendered.

*** TIME CRITICAL ELECTION DEADLINE ***
Custodian Cutoff Time: 04-OCT-2026 17:00 EST
Depository Cutoff (DTCC): 05-OCT-2026 11:00 EST

Options Available:
1. Cash Option: Elect USD 54.00 per share
2. Stock Option: Elect 1.25 Hyperion shares per share
3. Take No Action (Retain original Quantum Dynamics shares)

DEFAULT OPTION: Option 3 (Take No Action / Do not tender)

Please submit your Portfolio Manager elections via the Corporate Actions Portal or return MT565 SWIFT instructions before the custodian cutoff. Failure to submit valid instructions by 17:00 EST will result in no action taken.

Corporate Actions Custody Operations
BNY Mellon Asset Servicing""",
    },
    {
        "filename": "02_cash_dividend_declaration.eml",
        "format": "eml",
        "subject": "MANDATORY CASH DIVIDEND: Novo Nordisk A/S (ISIN: DK0062498333) - Interim Dividend DKK 6.40",
        "from": "ca-announcements@euroclear.com",
        "to": "settlements@apexcapital.com",
        "date": "Fri, 02 Oct 2026 14:15:00 +0000",
        "body": """EVENT NOTIFICATION: MANDATORY CORPORATE ACTION

Corporate Action Reference: EU-DIV-2026-991204
Event Type: Mandatory Cash Dividend (DVCA)
Issuer: NOVO NORDISK A/S (DK0062498333)
Market: Nasdaq Copenhagen (XCSE)

Event Key Dates:
- Ex-Dividend Date: 10-OCT-2026
- Record Date: 11-OCT-2026
- Payment Date: 20-OCT-2026

Financial Terms:
- Gross Dividend Rate: DKK 6.400000 per share
- Statutory Withholding Tax: 27.0%
- Net Rate: DKK 4.672000 per share
- Currency: DKK (Danish Krone)

Processing Note:
This is a mandatory event requiring no shareholder election. Entitlements will be credited automatically to your clearing cash account on value date 20-OCT-2026. Please update fund accounting ledgers accordingly.

Euroclear Corporate Action Operations""",
    },
    {
        "filename": "03_rights_issue_subscription.json",
        "format": "json",
        "data": {
            "id": "CA-RIGHTS-2026-7881",
            "subject": "VOLUNTARY RIGHTS ISSUE: Apex Renewables PLC (ISIN: GB00B1YW4409) - Subscription Cutoff Approaching",
            "from": "global-custody@citi.com",
            "to": "portfolio-ops@apexcapital.com",
            "date": "Sat, 03 Oct 2026 08:45:00 +0000",
            "body": "ATTENTION: CORPORATE ACTIONS TRADING DESK\n\nEvent Type: Voluntary Rights Offering (RHTS)\nSecurity: APEX RENEWABLES PLC ORD 10P (GB00B1YW4409)\nRights Security ISIN: GB00B88K3391 (Apex Renewables Nil-Paid Rights)\n\nRatio: 1 new ordinary share for every 4 existing shares held\nSubscription Price: 420.00 GBX per new ordinary share\n\nKey Deadlines:\n- Rights Trading Expiry: 05-OCT-2026 12:00 BST\n- Custodian Election Deadline: 06-OCT-2026 15:00 BST\n\nOptions:\nOption 1: Subscribe in full (exercise rights at 420p per share)\nOption 2: Apply for excess shares (subject to scaling)\nOption 3: Sell rights in the market before trading closes\nOption 4: Lapse / No action (Rights will lapse worthless)\n\nAction Required: Urgent instruction required from portfolio managers. Kindly confirm funds availability in settlement account for total subscription consideration.",
        },
    },
    {
        "filename": "04_forward_stock_split_3_for_1.eml",
        "format": "eml",
        "subject": "MANDATORY EVENT NOTICE: 3-for-1 Forward Stock Split for Titan Technologies Inc (CUSIP: 886732109)",
        "from": "corporateactions@dtcc.com",
        "to": "ca-ops@apexcapital.com",
        "date": "Sat, 03 Oct 2026 07:10:00 +0000",
        "body": """THE DEPOSITORY TRUST & CLEARING CORPORATION (DTCC)
MANDATORY CORPORATE ACTION NOTIFICATION

Notice ID: DTCC-SPLIT-2026-5501
Event Type: Forward Stock Split (SPLF)
Security Name: TITAN TECHNOLOGIES INC COM
CUSIP: 886732109
ISIN: US8867321098
Exchange: NASDAQ

Terms:
- Split Ratio: 3 for 1 (2 additional shares distributed for each 1 share held)
- Record Date: 12-OCT-2026
- Payable / Distribution Date: 15-OCT-2026
- Ex-Date (as determined by NASDAQ): 16-OCT-2026

Position Adjustment Instructions:
Holdings on record date will automatically be multiplied by 3. Open orders on market trading venues will be adjusted per exchange rules. No action required from underlying beneficial owners. Security master team should update nominal share count and adjust historical per-share cost basis.

DTCC Operations""",
    },
    {
        "filename": "05_proxy_voting_agm_resolutions.json",
        "format": "json",
        "data": {
            "id": "PROXY-AGM-2026-094",
            "subject": "SHAREHOLDER MEETING: Annual General Meeting (AGM) Proxy Ballot for Atlas Global PLC (ISIN: GB0000533153)",
            "from": "proxy-ballots@broadridge.com",
            "to": "stewardship@apexcapital.com",
            "date": "Thu, 01 Oct 2026 11:20:00 +0000",
            "body": "BROADRIDGE INVESTOR COMMUNICATION SOLUTIONS\nProxy Voting Notice & Shareholder Meeting Package\n\nMeeting: Annual General Meeting (AGM)\nIssuer: ATLAS GLOBAL PLC (ISIN: GB0000533153 / SEDOL: 0053315)\nMeeting Date: 16-OCT-2026 10:00 BST (London, UK)\nVoting Cutoff Date: 13-OCT-2026 17:00 BST\n\nKey Agenda Resolutions:\n- Resolution 1: Receive Annual Report & Financial Statements (Management Recommendation: FOR)\n- Resolution 2: Approve Directors' Remuneration Policy (Contested)\n- Resolution 3-7: Re-election of Independent Board Directors\n- Resolution 8: Re-appointment of Ernst & Young as Statutory Auditor\n- Resolution 12: Shareholder Sponsored Resolution: 2030 Climate Transition Scope 3 Emissions Disclosure\n\nPlease enter your stewardship voting instructions (FOR, AGAINST, ABSTAIN) via ProxyEdge or return ISO 20022 semt.020 / MT565 before the voting deadline.",
        },
    },
    {
        "filename": "06_spinoff_distribution_new_isin.eml",
        "format": "eml",
        "subject": "MANDATORY CORPORATE SPIN-OFF: Enterprise Holdings Inc spinning off CloudOps Solutions (Allocation Ratio: 0.25)",
        "from": "ca-syndicate@jpmorgan.com",
        "to": "asset-servicing@apexcapital.com",
        "date": "Fri, 02 Oct 2026 17:45:00 +0000",
        "body": """J.P. MORGAN GLOBAL ASSET SERVICING
CORPORATE REORGANIZATION BULLETIN

Event Type: Mandatory Spin-Off (SOFF)
Parent Security: ENTERPRISE HOLDINGS INC (ISIN: US29364G1033 / CUSIP: 29364G103)
Spin-Off Security: CLOUDOPS SOLUTIONS INC (New ISIN: US18905B1012 / CUSIP: 18905B101)

Transaction Summary:
Enterprise Holdings Inc is executing a tax-free spin-off of 100% of its CloudOps enterprise cloud software division.

Distribution Terms:
- Allocation Ratio: 0.250000 shares of CloudOps for every 1.000000 share of Enterprise Holdings held.
- Fractional Shares: Fractional entitlements will not be issued; cash-in-lieu of fractional shares will be paid following post-spin trading volume weighted average price.
- Ex-Date: 18-OCT-2026
- Payment / Distribution Date: 24-OCT-2026

Operational Requirement:
Data Management / Security Master team must establish the new security master record for CloudOps Solutions (US18905B1012) in OMS/PMS trading systems prior to the ex-date.

J.P. Morgan Custody Operations""",
    },
    {
        "filename": "07_custodian_reconciliation_break.eml",
        "format": "eml",
        "subject": "CRITICAL BREAK: Corporate Action Entitlement Discrepancy - $60,000 Variance on Fund Alpha (Event ID: CA884102)",
        "from": "exceptions-team@northerntrust.com",
        "to": "recon-escalations@apexcapital.com",
        "date": "Sat, 03 Oct 2026 10:15:30 +0000",
        "body": """URGENT ESCALATION: CORPORATE ACTIONS RECONCILIATION BREAK

To: Corporate Actions Operations & Financial Controller
From: Northern Trust Global Exception Management Desk

Event ID: CA-884102
Account: Apex Alpha Institutional Multi-Asset Fund (Acc: #NT-90812)
Security: VODAFONE GROUP PLC (ISIN: GB00BH4HKS39)
Event: Final Cash Dividend Payment

Discrepancy Details:
- Internal Accounting Expected Cash: USD 245,400.00
- Custodian Credited Cash Amount: USD 185,400.00
- NET UNRECONCILED BREAK: USD (60,000.00) NEGATIVE VARIANCE

Root Cause Analysis:
The custodian withholding tax module erroneously applied the non-treaty 30% statutory withholding tax rate instead of the certified 15% Double Taxation Treaty (DTT) rate specified in the fund's W-8BEN-E declaration on file.

Immediate Operational Action Required:
1. Open priority escalation ticket with Northern Trust Tax Operations.
2. Provide certified Form W-8BEN-E treaty schedule re-verification.
3. Obtain reclaim credit confirmation to prevent monthly NAV miscalculation.

Status: UNRESOLVED / CRITICAL OPERATIONAL IMPACT
Recon Desk Phone: +1 (312) 555-0199""",
    },
    {
        "filename": "08_optional_dividend_scrip_cash.json",
        "format": "json",
        "data": {
            "id": "CA-OPTDIV-2026-443",
            "subject": "MANDATORY WITH CHOICE: Optional Dividend (Cash vs Scrip Shares) for TotalEnergies SE (ISIN: FR0000120271)",
            "from": "corporate-actions-desk@bnpparibas.com",
            "to": "corporateactions@apexcapital.com",
            "date": "Thu, 01 Oct 2026 16:40:00 +0000",
            "body": "BNP PARIBAS SECURITIES SERVICES\nEVENT NOTIFICATION: OPTIONAL DIVIDEND / SCRIP ELECTION (DVOP)\n\nIssuer: TOTALENERGIES SE (ISIN: FR0000120271)\nEvent: Q3 2026 Interim Optional Dividend\n\nElection Options:\nOption 1: 100% Cash Dividend at EUR 0.79 per share\nOption 2: Scrip Dividend - Receive new ordinary shares at discounted subscription price EUR 58.20 per share\n\nDEFAULT OPTION: Option 1 (100% Cash)\n\nElection Deadlines:\n- Custodian Election Deadline: 14-OCT-2026 16:00 CET\n- Settlement / Payment Date: 26-OCT-2026\n\nAction Required: Solicit Portfolio Manager investment election between cash yield and equity compounding before the deadline.",
        },
    },
    {
        "filename": "09_capital_reduction_notice.eml",
        "format": "eml",
        "subject": "MANDATORY CAPITAL REDUCTION: Pacific Mining Corp (ISIN: AU000000PMC2) - Par Value Reduction",
        "from": "custodyservices@hsbc.com",
        "to": "asset-ops@apexcapital.com",
        "date": "Wed, 30 Sep 2026 13:20:00 +0000",
        "body": """HSBC GLOBAL ASSET SERVICING
MANDATORY CORPORATE EVENT NOTIFICATION

Event Type: Capital Reduction / Return of Capital (CAPR)
Security: PACIFIC MINING CORP LTD (ISIN: AU000000PMC2 / ASX: PMC)

Details:
Following shareholder and court approval, Pacific Mining Corp is undertaking an equal capital reduction:
- Share capital reduction: Par value reduced from AUD 1.00 to AUD 0.20 per share
- Cash return payment: AUD 0.80 per share returned to shareholders of record
- Ex-Date: 22-OCT-2026
- Record Date: 23-OCT-2026
- Payment Date: 02-NOV-2026

Tax Treatment Note:
Return of capital will reduce the cost base of shares for capital gains tax purposes. Cash entitlement will be credited automatically. No shareholder election is required.

HSBC Custody Operations Sydney""",
    },
    {
        "filename": "10_unsolicited_financial_newsletter_spam.txt",
        "format": "txt",
        "text": """From: crypto-quant-alpha@hyperbot-yield.biz
To: ca-ops@apexcapital.com
Subject: [EXCLUSIVE] 1000% APY Guaranteed with our Institutional Arbitrage Algo! Book Demo Now

Attention Fund Operations Manager,

Are you leaving yield on the table? Our proprietary high-frequency AI bot scalps cross-exchange cryptocurrency spreads with 99.8% win rate and zero drawdown risk!

We are onboarding a strictly limited cohort of 10 family offices and hedge funds this quarter.

Click here to reserve your private institutional onboarding call: https://bit.ly/crypto-scam-arbitrage-772

Reply UNSUBSCRIBE to stop receiving our daily high-yield opportunities.""",
    },
]


def _write_emails_to_disk(emails_data: list[dict], target_dir: Path) -> list[Path]:
    """Helper to write email list to disk."""
    target_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for item in emails_data:
        file_path = target_dir / item["filename"]

        if item["format"] == "eml":
            msg = PyEmailMessage()
            msg["Subject"] = item["subject"]
            msg["From"] = item["from"]
            msg["To"] = item["to"]
            msg["Date"] = item["date"]
            msg.set_content(item["body"])
            if item.get("attachments"):
                for att in item["attachments"]:
                    att_data = att.get("data", b"Mock PDF attachment data")
                    msg.add_attachment(
                        att_data,
                        maintype="application",
                        subtype="pdf",
                        filename=att.get("filename", "corporate_action_notice.pdf"),
                    )
            file_path.write_bytes(msg.as_bytes())

        elif item["format"] == "json":
            file_path.write_text(json.dumps(item["data"], indent=2), encoding="utf-8")

        elif item["format"] == "txt":
            file_path.write_text(item["text"], encoding="utf-8")

        generated_files.append(file_path)

    return generated_files


def generate_sample_dataset(target_dir: Path = SAMPLE_DIR) -> list[Path]:
    """Generate sample IT/Operations email files on disk."""
    files = _write_emails_to_disk(SAMPLE_EMAILS, target_dir)
    print(f"Generated {len(files)} IT sample email files in {target_dir}")
    return files


def generate_corporate_actions_dataset(target_dir: Path = CORPORATE_ACTIONS_DIR) -> list[Path]:
    """Generate realistic Corporate Actions email files on disk."""
    files = _write_emails_to_disk(CORPORATE_ACTIONS_EMAILS, target_dir)
    print(f"Generated {len(files)} Corporate Actions email files in {target_dir}")
    return files


def generate_all_datasets() -> dict[str, list[Path]]:
    """Generate all datasets."""
    sample_files = generate_sample_dataset()
    ca_files = generate_corporate_actions_dataset()
    return {
        "sample_emails": sample_files,
        "corporate_actions_emails": ca_files,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample email datasets for Jev AI flows.")
    parser.add_argument(
        "--dataset",
        choices=["sample", "corporate_actions", "all"],
        default="all",
        help="Dataset to generate (sample, corporate_actions, or all)",
    )
    args = parser.parse_args()

    if args.dataset == "sample":
        generate_sample_dataset()
    elif args.dataset == "corporate_actions":
        generate_corporate_actions_dataset()
    else:
        generate_all_datasets()
