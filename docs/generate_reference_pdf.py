#!/usr/bin/env python3
"""
Complete Technical & Commercial Reference PDF
Telecom Cloud Intelligence Platform - PFE 2025-2026

Section 4 (Tunisian Telecom Market) updated with VERIFIED 2025 forfait data
scraped directly from operator websites and corroborated by thd.tn.

Sources:
  Orange Tunisie   : https://www.orange.tn/options-offres-mobile-prepayees  (live, March 2026)
  Tunisie Telecom  : https://www.tunisietelecom.tn/particulier/mobile/internet-mobile/forfaits/
                     + https://www.thd.tn/tunisie-telecom-revoit-ses-forfaits-internet-mobile-plus-de-data-et-des-prix-ajustes/  (Feb 2025)
                     + https://www.lapresse.tn/2025/02/14/decouvrez-les-offres-5g-de-tunisie-telecom/
  Ooredoo Tunisie  : https://www.ooredoo.tn/Personal/en/content/346-routeurs-mobile-wifi-4g
                     + https://www.thd.tn/mise-a-jour-comparatif-des-forfaits-data-5g-en-tunisie-bilan-de-la-premiere-semaine-de-lancement/  (Feb 2025)
  5G launch cross-check: https://www.thd.tn/mise-a-jour-comparatif-des-forfaits-data-5g-en-tunisie-bilan-de-la-premiere-semaine-de-lancement/
  Android DZ 2026  : https://www.android-dz.com/comparatif-forfaits-internet-en-tunisie-ooredoo-tt-et-orange-2026/
"""

import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# -- palette --
PRIMARY   = (0, 71, 171)
DARK      = (15, 23, 42)
ACCENT    = (6, 150, 180)
LIGHT_BG  = (240, 245, 255)
CODE_BG   = (245, 245, 245)
TEXT      = (30, 30, 30)
MUTED     = (100, 100, 100)
WHITE     = (255, 255, 255)
GREEN     = (34, 139, 34)
ORANGE    = (200, 100, 0)
RED       = (180, 30, 30)

OUT = "docs/complete-technical-reference.pdf"


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 18, 18)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 11, "F")
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*WHITE)
        self.set_xy(10, 2)
        self.cell(130, 7, "Telecom Cloud Intelligence  -  Complete Technical & Commercial Reference")
        self.set_xy(155, 2)
        self.set_font("Helvetica", "", 7.5)
        self.cell(45, 7, f"PFE 2025-2026  |  {datetime.date.today()}", align="R")
        self.set_text_color(*TEXT)
        self.ln(6)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-13)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    def sec(self, num, title):
        self.ln(5)
        self.set_fill_color(*DARK)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 11, f"  {num}.  {title}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.ln(3)

    def sub(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*PRIMARY)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.3)
        x, y = self.get_x(), self.get_y()
        self.line(x, y, x + 174, y)
        self.set_text_color(*TEXT)
        self.ln(2)

    def sub2(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*ACCENT)
        self.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.ln(1)

    def p(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*TEXT)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def b(self, items, indent=8):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*TEXT)
        for item in items:
            self.set_x(self.l_margin + indent)
            self.cell(5, 5.5, chr(149), new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.multi_cell(0, 5.5, item)
        self.ln(1)

    def kv(self, rows, col1=52):
        fill = False
        for k, v in rows:
            self.set_fill_color(*(LIGHT_BG if fill else WHITE))
            self.set_font("Helvetica", "B", 9)
            x = self.get_x()
            y = self.get_y()
            self.multi_cell(col1, 5.5, "  " + k, fill=True, border=0,
                            new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_xy(x + col1, y)
            self.set_font("Helvetica", "", 9)
            self.multi_cell(0, 5.5, v, fill=True, border=0,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            fill = not fill
        self.ln(2)

    def code(self, text):
        self.set_fill_color(*CODE_BG)
        self.set_font("Courier", "", 8)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 4.5, text, fill=True, border=1)
        self.set_text_color(*TEXT)
        self.set_font("Helvetica", "", 9.5)
        self.ln(2)

    def badge(self, label, color):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*color)
        self.set_text_color(*WHITE)
        self.cell(len(label) * 3 + 12, 6, f"  {label}  ", fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_text_color(*TEXT)
        self.set_font("Helvetica", "", 9.5)
        self.cell(3, 6, " ")

    def source_note(self, text):
        """Small italic source citation line."""
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.set_x(self.l_margin + 4)
        self.multi_cell(0, 4.5, f"Source: {text}")
        self.set_text_color(*TEXT)
        self.ln(1)


def build():
    pdf = PDF()
    pdf.set_title("Telecom Cloud Intelligence - Complete Reference")
    pdf.set_author("Souhayl Guenichi - Huawei Tunisia PFE 2025-2026")

    # ================================================================ COVER
    pdf.add_page()
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, 210, 100, "F")
    pdf.set_xy(10, 18)
    pdf.set_font("Helvetica", "B", 30)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(190, 14, "Telecom Cloud\nIntelligence Platform", align="C")
    pdf.set_xy(10, 58)
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(190, 7, "Complete Technical & Commercial Reference", align="C")
    pdf.set_xy(10, 72)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(190, 7,
        "PFE 2025-2026  |  ESPRIT University  |  Huawei Tunisia Internship", align="C")
    pdf.set_xy(10, 84)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(190, 7, f"Generated: {datetime.date.today()}", align="C")

    pdf.set_text_color(*TEXT)
    pdf.set_y(110)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Table of Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    toc = [
        "1.  Project in Plain Language",
        "2.  The Telecom Problem (Commercial Context)",
        "3.  SLA Explained - What, Why, and How",
        "4.  Tunisian Telecom Market (Verified Facts & 2025 Forfait Data)",
        "5.  System Architecture (5 Containers)",
        "6.  The 22-Step Pipeline",
        "7.  AI/ML Models - Complete Breakdown",
        "8.  Database Schema (7 Tables)",
        "9.  REST API (7 Endpoints)",
        "10. Data Lake (3 Layers)",
        "11. Huawei Cloud Stack Mapping",
        "12. What's Built vs Planned (Roadmap)",
        "13. Sources & References",
    ]
    for line in toc:
        pdf.set_x(25)
        pdf.cell(0, 6.5, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ================================================================ 1
    pdf.add_page()
    pdf.sec("1", "Project in Plain Language")

    pdf.sub("1.1  One-Paragraph Summary")
    pdf.p(
        "Telecom Cloud Intelligence is a platform that simulates a telecom operator's "
        "network data (how the cell towers are performing) and business data (how much "
        "revenue subscribers are generating), then uses AI to find problems in both, "
        "and finally computes the CORRELATION between network problems and business impact. "
        "Everything runs in Docker containers and is designed to be deployable on "
        "Huawei Cloud Stack (HCS)."
    )

    pdf.sub("1.2  What It Actually Does (Step by Step)")
    pdf.b([
        "Generates synthetic OSS data: 200 network records per run from 10 simulated cell "
        "towers, each with 5 Key Performance Indicators (KPIs)",
        "Generates synthetic BSS data: 200 subscriber records from 3 Tunisian operators, "
        "with realistic prepaid/postpaid revenue patterns in TND",
        "Injects realistic fault patterns: 2-3 cells randomly degrade (latency spikes, "
        "throughput collapses) and correlated subscribers see reduced data usage + higher churn",
        "Stores raw data in a 3-layer data lake (MinIO): Raw -> Processed -> Curated",
        "Runs 3 AI models: SLA risk scoring, network anomaly detection, revenue anomaly detection",
        "Computes statistical correlations between network metrics and business metrics "
        "(Pearson and Spearman coefficients)",
        "Persists everything to PostgreSQL (7 tables) with full traceability",
        "Serves all results through 7 REST API endpoints",
    ])

    pdf.sub("1.3  Why This Project Matters")
    pdf.p(
        "In real telecom operations, the network team and the business team work in silos. "
        "When a cell tower degrades, the network engineer sees it in their OSS dashboard. "
        "But the revenue team only discovers the business impact weeks later in a monthly report. "
        "By then, subscribers have already churned, revenue has already dropped, and SLA penalty "
        "clauses have already been triggered. This platform closes that gap by correlating "
        "technical performance with business outcomes in near-real-time."
    )

    # ================================================================ 2
    pdf.add_page()
    pdf.sec("2", "The Telecom Problem (Commercial Context)")

    pdf.sub("2.1  What is OSS?")
    pdf.p(
        "OSS = Operations Support System. This is the technical side of a telecom operator. "
        "OSS tools monitor the physical network: cell towers, radio signals, packet routing, "
        "bandwidth utilization. OSS answers the question: 'Is the network working?'"
    )
    pdf.p("In our platform, OSS data consists of 5 KPIs per cell tower record:")
    pdf.kv([
        ("throughput_mbps",   "Data transfer speed. How fast can a subscriber download? "
                              "Normal: 60-100 Mbps. Degraded: <20 Mbps. "
                              "Defined in 3GPP TS 28.554 as 'DL Throughput at IP Layer'."),
        ("latency_ms",        "Round-trip delay for a data packet. How long does a request take? "
                              "Normal: 15-35 ms. Degraded: >60 ms. "
                              "3GPP TS 28.554: 'Packet Delay Budget'. ITU-T Y.1541 Class 0: <100ms."),
        ("packet_loss_pct",   "Percentage of data packets that never arrive. "
                              "Normal: 0-1%. Degraded: >3%. "
                              "ITU-T Y.1541: maximum 0.1% for Class 0 (real-time services)."),
        ("active_users",      "Number of subscribers currently connected to this cell. "
                              "Normal: 50-300. Overloaded: >400. "
                              "Reflects cell capacity as defined in 3GPP TS 36.314."),
        ("signal_rsrp_dbm",   "Reference Signal Received Power. Radio signal strength. "
                              "Normal: -60 to -90 dBm. Weak: < -110 dBm. "
                              "3GPP TS 36.214: RSRP measurement definition. "
                              "Below -110 dBm = cell edge, poor service."),
    ])

    pdf.sub("2.2  What is BSS?")
    pdf.p(
        "BSS = Business Support System. This is the commercial side. BSS handles billing, "
        "subscription management, revenue tracking, customer lifecycle. "
        "BSS answers the question: 'Is the business making money?'"
    )
    pdf.p("In our platform, BSS data reflects the Tunisian prepaid-dominant market:")
    pdf.kv([
        ("revenue_tnd",     "Total monthly subscriber spend in Tunisian Dinar. "
                            "Prepaid: cumulative bundle purchases (see Section 4 for verified pricing). "
                            "Postpaid: fixed plan cost (40-90 TND/month). "
                            "Revenue = what the operator actually earns from this subscriber."),
        ("data_used_gb",    "Monthly mobile data consumption. "
                            "GSMA Intelligence 2023: average Tunisian mobile user consumes ~4.2 GB/month. "
                            "Range in our data: 0.1-50 GB to cover light and heavy users."),
        ("voice_min",       "Monthly voice call minutes. "
                            "INTT 2023: average ~210 min/month. Range: 0-600."),
        ("sms_count",       "Monthly SMS messages sent. Declining metric. "
                            "INTT notes SMS usage down ~35% YoY due to WhatsApp/Messenger."),
        ("churn_risk",      "Estimated probability that this subscriber will leave the operator. "
                            "0.0 = loyal, 1.0 = almost certain to churn. "
                            "In our fault injection, churn spikes when the subscriber's cell degrades."),
        ("line_type",       "'prepaid' or 'postpaid'. Tunisia is ~80% prepaid. "
                            "This ratio matches INTT 2023 market statistics."),
    ])

    pdf.sub("2.3  The Gap Between OSS and BSS")
    pdf.p(
        "In most telecom operators, OSS data lives in the network operations center (NOC) "
        "and BSS data lives in the finance/commercial department. They use different tools, "
        "different databases, different teams. The correlation between 'cell tower X degraded "
        "for 3 hours' and 'we lost 150,000 TND in revenue from that area' is computed manually "
        "weeks later, if at all."
    )
    pdf.p(
        "Our platform automates this correlation in seconds. Every pipeline run computes "
        "Pearson and Spearman coefficients between OSS metrics (latency, throughput, packet loss) "
        "and BSS metrics (revenue, data usage, churn risk) at the cell level."
    )

    # ================================================================ 3
    pdf.add_page()
    pdf.sec("3", "SLA Explained - What, Why, and How")

    pdf.sub("3.1  What is an SLA?")
    pdf.p(
        "SLA = Service Level Agreement. It is a contractual commitment between a telecom "
        "operator and their customers (B2B) or internal business units. It specifies minimum "
        "performance thresholds that the network must maintain."
    )
    pdf.p("Real-world SLA thresholds (typical in Tunisian B2B contracts):")
    pdf.kv([
        ("Latency",        "< 50 ms round-trip. Source: ITU-T Y.1541 Class 1."),
        ("Packet Loss",    "< 1%. Source: ITU-T Y.1541 Class 1."),
        ("Throughput",     "> 20 Mbps minimum guaranteed. Varies by contract tier."),
        ("Availability",   "> 99.9% uptime per month (max 43 min downtime). "
                           "Source: TM Forum SLA Management Handbook GB917."),
    ])

    pdf.sub("3.2  Why SLA Matters Commercially")
    pdf.b([
        "B2B contracts: penalty clauses are triggered. Example: a bank paying 5,000 TND/month "
        "for guaranteed connectivity may receive a 20% credit (1,000 TND) per month with SLA violation.",
        "Consumer impact: subscribers experiencing poor service churn to competitors. "
        "Acquiring a new subscriber costs 5-10x more than retaining one (GSMA estimate).",
        "Regulatory: INTT can impose fines for repeated service quality failures.",
        "Revenue correlation: our data shows that when cells degrade, subscriber data usage "
        "drops by 40-70% and churn risk spikes by 0.3-0.55 points - this is measurable revenue loss.",
    ])

    pdf.sub("3.3  Why PREDICT SLA Risk (Not Just Detect Breaches)?")
    pdf.p(
        "Detecting a breach after it happens is too late. The penalty is already owed. "
        "The customer is already frustrated. The revenue is already lost."
    )
    pdf.p(
        "Predictive SLA management means: given the current 15-minute window of network KPIs, "
        "what is the PROBABILITY that an SLA breach will occur? If the probability is high, "
        "the operator can take preventive action before the breach happens."
    )
    pdf.b([
        "Reroute traffic away from degraded cells",
        "Send priority maintenance crews",
        "Proactively notify enterprise customers",
        "Temporarily reduce load (congestion management)",
        "Avoid financial penalty clauses",
    ])

    pdf.sub("3.4  How Our SLA Risk Model Works")
    pdf.p("Step 1 - Data Collection (every 15 minutes):")
    pdf.p(
        "The pipeline collects 200 OSS records from 10 cell towers. Each record has "
        "the 5 raw KPIs: throughput, latency, packet loss, active users, signal strength."
    )
    pdf.p("Step 2 - Feature Engineering (aggregation into 9 features):")
    pdf.kv([
        ("mean_throughput_mbps",  "Average speed across all cells in this window"),
        ("std_throughput_mbps",   "Speed stability - high std = unstable network"),
        ("mean_latency_ms",       "Average delay across all cells"),
        ("std_latency_ms",        "Latency stability - high std = jittery"),
        ("max_latency_ms",        "Worst-case latency - captures spikes"),
        ("mean_packet_loss_pct",  "Average packet loss"),
        ("max_packet_loss_pct",   "Worst-case packet loss"),
        ("mean_active_users",     "Network load indicator"),
        ("mean_signal_rsrp_dbm",  "Average signal strength"),
    ])
    pdf.p(
        "Why 9 features instead of 5? Because risk is about more than averages. A network "
        "with mean latency 30ms but max 200ms is much riskier than one with mean 30ms and "
        "max 35ms. The std and max features capture volatility and worst-case scenarios."
    )
    pdf.p("Step 3 - Model Prediction:")
    pdf.p(
        "The GradientBoostingRegressor takes the 9-feature vector and outputs a continuous "
        "risk score between 0.0 and 1.0:"
    )
    pdf.kv([
        ("0.0 - 0.3",   "LOW RISK. SLA is safe. Normal operations."),
        ("0.3 - 0.6",   "MODERATE RISK. Monitor closely. Possible degradation developing."),
        ("0.6 - 0.8",   "HIGH RISK. Take preventive action. SLA breach likely."),
        ("0.8 - 1.0",   "CRITICAL. Breach imminent or already occurring."),
    ], col1=30)

    pdf.p("Step 4 - Explainability:")
    pdf.p(
        "The model outputs feature importances telling you WHY the risk is high. "
        "In our trained model: mean_latency_ms has importance 0.69 (latency explains 69% "
        "of SLA risk), mean_packet_loss_pct at 0.12, max_latency_ms at 0.08. "
        "This means a telecom engineer can immediately see: 'fix the latency problem first'."
    )

    pdf.sub("3.5  The Training Label Formula")
    pdf.code(
        "risk  = clip((latency - 20) / 60,    0, 0.35)   # latency contribution\n"
        "      + clip((max_lat - 30) / 70,     0, 0.25)   # spike contribution\n"
        "      + clip(packet_loss / 4,          0, 0.25)   # loss contribution\n"
        "      + clip(max_loss / 6,             0, 0.15)   # worst-case loss\n"
        "      + clip((60 - throughput) / 100,  0, 0.20)   # low speed\n"
        "      + noise(0, 0.03)                            # small randomness"
    )
    pdf.p(
        "Interpretation: latency below 20ms contributes zero risk. Above 80ms = maximum "
        "latency risk (0.35). Throughput above 60 Mbps = zero throughput risk. Below 60 = "
        "risk increases proportionally. These thresholds are aligned with ITU-T Y.1541 "
        "and real-world SLA contracts."
    )

    # ================================================================ 4  (CORRECTED)
    pdf.add_page()
    pdf.sec("4", "Tunisian Telecom Market (Verified Facts & 2025 Forfait Data)")

    pdf.sub("4.1  The Three Operators")
    pdf.kv([
        ("Ooredoo Tunisie",   "Subsidiary of Ooredoo Group (Qatar). ~7.5M subscribers (2023). "
                              "Strong 4G/5G coverage in urban areas. Market share ~33%. "
                              "Source: Ooredoo Group Annual Report 2023."),
        ("Tunisie Telecom",   "State-owned incumbent. ~8.2M subscribers. Largest fixed + mobile "
                              "footprint. Best rural coverage. Market share ~36%. "
                              "Source: Tunisie Telecom Annual Report 2023."),
        ("Orange Tunisie",    "Subsidiary of Orange Group (France). ~5.8M subscribers. "
                              "Known for data-heavy offers and youth segment. Market share ~26%. "
                              "Source: INTT Annual Telecommunications Report 2023."),
    ])
    pdf.p(
        "Total mobile subscribers in Tunisia: ~21.5M (population ~12M - many people hold 2+ SIMs). "
        "Mobile penetration: ~180%. 5G launched on 14 February 2025 by all three operators simultaneously. "
        "Source: INTT 2023, thd.tn February 2025."
    )

    pdf.sub("4.2  Prepaid-Dominant Market")
    pdf.p(
        "Tunisia is a prepaid-dominant market. Approximately 80% of mobile subscribers are "
        "prepaid, 20% are postpaid. Typical of North African and Middle Eastern markets. "
        "Source: GSMA Intelligence - Tunisia Country Overview 2023."
    )
    pdf.p(
        "Key structural note: all three operators now offer data bundles valid for 5G, 4G, and 3G "
        "on the same price grids, following INTT's regulated 5G tariff framework (Feb 2025). "
        "Payment discounts: -5% via phone balance, -10% via bank card (all operators)."
    )

    # ---- ORANGE TUNISIE  ----
    pdf.sub("4.3  Orange Tunisie Prepaid Internet Options (*124#)")
    pdf.p(
        "Data verified directly from orange.tn/options-offres-mobile-prepayees (live page, March 2026). "
        "USSD activation: *124# (main data options) and *120# (7-day option). "
        "Includes full range from micro-top-ups to long-validity large bundles."
    )
    pdf.kv([
        ("100 Mo - 0.5 DT",    "Validity: 1 day. Micro top-up for occasional use. USSD *124#."),
        ("200 Mo - 0.9 DT",    "Validity: 4 days. Short-trip option. USSD *124#."),
        ("330 Mo - 1.5 DT",    "Validity: 7 days. Weekly light user. USSD *124#."),
        ("750 Mo - 3.5 DT",    "Validity: 7 days. Weekly medium user. USSD *120#."),
        ("1.125 Go - 4.5 DT",  "Validity: 30 days. Monthly entry-level (equivalent ~4 DT/Go). USSD *124#."),
        ("2.2 Go - 7.7 DT",    "Validity: 30 days. (~3.5 DT/Go). USSD *124#."),
        ("4 Go - 10 DT",       "Validity: 30 days. Popular mid-tier (~2.5 DT/Go). USSD *124#."),
        ("6 Go - 15 DT",       "Validity: 30 days. (~2.5 DT/Go). USSD *124#."),
        ("25 Go - 30 DT",      "Validity: 30 days. Entry 5G/4G bundle (~1.2 DT/Go). USSD *124#."),
        ("30 Go - 36 DT",      "Validity: 30 days. (~1.2 DT/Go). USSD *124#."),
        ("42 Go - 46.2 DT",    "Validity: 30 days. Promo offer (~1.1 DT/Go). USSD *124#."),
        ("60 Go - 60 DT",      "Validity: 60 days. (~1.0 DT/Go). USSD *124#."),
        ("100 Go - 72 DT",     "Validity: 90 days. (~0.72 DT/Go). USSD *124#."),
        ("200 Go - 100 DT",    "Validity: 120 days. (~0.50 DT/Go). USSD *124#."),
        ("500 Go - 250 DT",    "Validity: 365 days. Nouveau (latest addition). (~0.50 DT/Go). USSD *124#."),
    ], col1=48)
    pdf.source_note(
        "orange.tn/options-offres-mobile-prepayees (direct page fetch, March 2026) | "
        "thd.tn - Comparatif 5G Tunisia Feb 2025"
    )

    # ---- TUNISIE TELECOM ----
    pdf.sub("4.4  Tunisie Telecom Prepaid Internet Forfaits (*140#) - Complete List")
    pdf.p(
        "Tunisie Telecom revised all mobile internet forfaits in February 2025 following the 5G launch. "
        "USSD: *140# (standard forfaits) | *540# (BIG forfaits, high-volume) | "
        "*140*7*5# (shared forfaits). Also activatable via My TT app. "
        "10% discount for bank card payment. "
        "Small forfaits updated: volumes increased at same price point (100 Mo replaced 75 Mo; "
        "1.5 Go replaced 1.25 Go). Mid-tier price per Go reduced from 3.5 DT/Go to 3 DT/Go."
    )
    pdf.kv([
        ("100 Mo - ~0.5 DT",    "Validity: 1 day. Revised up from 75 Mo at same price. USSD *140#."),
        ("500 Mo - ~2 DT",      "Validity: 7 days. Short weekly pass. USSD *140#."),
        ("1.5 Go - ~4 DT",      "Validity: 30 days. Revised up from 1.25 Go. (~2.67 DT/Go). USSD *140#."),
        ("4 Go - 10 DT",        "Validity: 30 days. Revised (was 2.8 Go at same price). (~2.5 DT/Go). USSD *140#."),
        ("25 Go - 30 DT",       "Validity: 30 days. (~1.2 DT/Go). Standard 5G/4G bundle. USSD *140#."),
        ("45 Go - 50 DT",       "Validity: 30 days. (~1.1 DT/Go). Best monthly value per thd.tn. USSD *140#."),
        ("110 Go - 80 DT",      "Validity: 60 days. (~0.72 DT/Go). BIG forfait. USSD *540#."),
        ("200 Go - 100 DT",     "Validity: 30 days. (~0.50 DT/Go). BIG forfait. USSD *540#."),
    ], col1=52)
    pdf.source_note(
        "thd.tn - 'Tunisie Telecom revoit ses forfaits' (28 Feb 2025): confirms 100Mo/0.5DT, "
        "4Go/10DT, 25Go/30DT, 45Go/50DT, 110Go/80DT, 200Go/100DT | "
        "lapresse.tn - 'Offres 5G de Tunisie Telecom' (14 Feb 2025) | "
        "tunisietelecom.tn/particulier/mobile/internet-mobile/forfaits/ | "
        "scribd.com/document/852681563/Tunisie-Telecom-Particulier-FORFAITS (TT official page capture)"
    )

    # ---- OOREDOO TUNISIE ----
    pdf.sub("4.5  Ooredoo Tunisie Flexi Internet Forfaits (*124#) - Complete List")
    pdf.p(
        "Ooredoo has two ranges: micro/short-validity 'Flexi' passes and monthly 'Flexi+' bundles. "
        "All valid on 5G/4G/3G. USSD: *124# or Eddenyalive/My Ooredoo app. "
        "-10% bank card, -5% balance. USSD menu (live screenshot March 2026): "
        "01:FORSA | 1:Flexi 30Go/55Go/42Go/10Go/25Go/100Go/8Go/75Go/jusqu'a 1000Go | "
        "2:Flexi 1.25Go(30J):5DT | 3:Flexi 2j:2dt | 4:Flexi 1j:1dt | "
        "5:Forfaits Facebook | 6:Autres Flexi | 7:KADO-Net | 8:Kridi Net | "
        "9:Familia Net | 10:Ta7wil-Net | 11:Simulateur | 12:Options YA BALACH."
    )
    pdf.p("MICRO / SHORT-VALIDITY (from Autres Flexi + live table at ooredoo.tn):")
    pdf.kv([
        ("Flexi Micro: 50 MB - 0.25 DT",     "Validity: 2 hours only."),
        ("Flexi 1d Mini: 100 MB - 0.5 DT",   "Validity: until midnight. AUTO-RENEWS daily. Menu opt 4."),
        ("Flexi 1d: 220 MB - 1 DT",          "Validity: until midnight (1 day). Menu option 4."),
        ("Flexi 2d: 440 MB - 2 DT",          "Validity: 2 days. Menu option 3."),
        ("Flexi 1.25 Go - 5 DT",             "Validity: 30 days. Menu option 2. (~4 DT/Go)."),
        ("Flexi 30d: 4 Go - 10 DT",          "Validity: 30 days. Autres Flexi. (~2.5 DT/Go)."),
        ("BIG Flexi: 6 Go - 15 DT",          "Validity: 30 days. Autres Flexi. (~2.5 DT/Go)."),
        ("Flexi 8 Go - 20 DT",               "Validity: 30 days. Autres Flexi. (~2.5 DT/Go)."),
    ], col1=60)
    pdf.p("FLEXI+ LARGE BUNDLES (from Flexi+ table at ooredoo.tn, confirmed by USSD menu option 1):")
    pdf.kv([
        ("Flexi 10 Go - 25 DT",              "Validity: 30 days. (~2.5 DT/Go)."),
        ("Flexi 25 Go - 30 DT",              "Validity: 30 days. (~1.2 DT/Go)."),
        ("Flexi 30 Go - 36 DT",              "Validity: 30 days. (~1.2 DT/Go)."),
        ("Xtra Flexi 35 Go + 120min - 50 DT", "Validity: 30 days. Includes 120 free call min + Starzplay."),
        ("Flexi 42 Go - 46.2 DT",            "Validity: 30 days. (~1.1 DT/Go)."),
        ("Flexi 55 Go - 55 DT",              "Validity: 55 days. (~1.0 DT/Go)."),
        ("Flexi 75 Go - 67.5 DT",            "Validity: 60 days. (~0.9 DT/Go)."),
        ("Flexi 100 Go - 72 DT",             "Validity: 90 days. (~0.72 DT/Go)."),
        ("Flexi 200 Go - 100 DT",            "Validity: 120 days. (~0.50 DT/Go)."),
        ("Flexi 500 Go - 250 DT",            "Validity: 5 months. Exclusive high-volume."),
        ("Flexi 1000 Go - 500 DT",           "Validity: 12 months. Maximum offer."),
    ], col1=60)
    pdf.source_note(
        "PRIMARY SOURCE 1: ooredoo.tn/Personal/en/content/272-les-nouveaux-flexi "
        "(complete HTML price table fetched live March 2026) | "
        "PRIMARY SOURCE 2: Live USSD *124# screenshot (device, March 2026 - confirms exact menu items) | "
        "CROSS-CHECK: thd.tn Comparatif 5G Tunisia (18 Feb 2025)"
    )

    pdf.sub("4.6  Postpaid Plans (All Three Operators)")
    pdf.p(
        "Postpaid subscribers pay a fixed monthly invoice and typically receive combined "
        "data + voice bundles. Require ID and a contract. The following ranges are representative "
        "of current postpaid catalogue tiers across operators."
    )
    pdf.kv([
        ("~40 DT/month",   "Entry postpaid: ~10-15 GB data + unlimited on-net calls. "
                           "Requires ID and contract. Example: Ooredoo Nkalmek entry / TT post entry."),
        ("~60 DT/month",   "Mid postpaid: ~25-30 GB + unlimited national calls + some roaming minutes. "
                           "Example: Ooredoo Nkalmek mid / Orange postpaid mid."),
        ("~90 DT/month",   "Premium postpaid: ~50-60 GB + unlimited calls + priority service. "
                           "Example: Ooredoo Nkalmek premium / TT post premium."),
    ])
    pdf.source_note(
        "ooredoo.tn/Personal/fr/content/826-nkalmek | orange.tn/professionnels | "
        "tunisietelecom.tn/particulier/mobile/"
    )

    pdf.sub("4.7  ARPU and Market Context")
    pdf.p(
        "ARPU (Average Revenue Per User) in Tunisia is among the lowest in the MENA region. "
        "Blended ARPU: approximately 12-18 TND/month (2023). Prepaid ARPU: ~8-15 TND/month. "
        "Postpaid ARPU: ~45-70 TND/month. "
        "The verified forfait pricing above shows per-Go costs ranging from ~3.5 DT (small bundles) "
        "down to ~0.50 DT (large bundles), reflecting the 5G price war launched in February 2025. "
        "Source: GSMA Intelligence, INTT Annual Report 2023."
    )

    pdf.sub("4.8  Data Sources and Verification")
    pdf.b([
        "Orange prepaid options: orange.tn/options-offres-mobile-prepayees - LIVE page "
        "(full price table fetched March 2026)",
        "Tunisie Telecom forfaits: tunisietelecom.tn/particulier/mobile/internet-mobile/forfaits/ "
        "confirmed by thd.tn (28 Feb 2025) and lapresse.tn (14 Feb 2025)",
        "Ooredoo forfaits: ooredoo.tn/Personal/en/content/272-les-nouveaux-flexi "
        "(live HTML table March 2026, two price tables: micro range + Flexi+ range) "
        "+ Live USSD *124# screenshot (device, March 2026 - exact menu structure) "
        "+ thd.tn 5G launch analysis (Feb 2025)",
        "Cross-operator 5G comparison (all three): thd.tn (18 Feb 2025) - independent analyst Mohamed Ali Bouriga",
        "INTT statistics: intt.tn publications section for annual market data",
        "GSMA Intelligence: gsmaintelligence.com - Tunisia Country Profile 2023",
        "NOTE: Orange USSD for data is *124# (confirmed orangeassistance.tn); "
        "*120# covers some 7-day options. Tunisie Telecom: *140# standard, *540# BIG forfaits.",
    ])

    # ================================================================ 5
    pdf.add_page()
    pdf.sec("5", "System Architecture (5 Containers)")

    pdf.sub("5.1  Overview")
    pdf.p(
        "The platform runs as 5 Docker containers orchestrated by Docker Compose. "
        "Each container has a single responsibility. They communicate over an internal "
        "Docker network. External access is only through the API Gateway on port 8000."
    )

    pdf.kv([
        ("postgres (port 5432)",       "PostgreSQL 16 database. Stores all structured results: "
                                       "pipeline runs, anomalies, risk scores, correlations, model metadata. "
                                       "Health-checked every 5 seconds. Data persists in 'pgdata' Docker volume."),
        ("minio (ports 9000/9001)",    "MinIO S3-compatible object storage. Acts as the 3-layer data lake. "
                                       "Port 9000 = S3 API. Port 9001 = web console. "
                                       "Data persists in 'miniodata' Docker volume."),
        ("api-gateway (port 8000)",    "FastAPI application. The only public-facing service. "
                                       "Read-only queries against PostgreSQL. 7 REST endpoints. "
                                       "Depends on: postgres, minio."),
        ("ai-service (port 8001)",     "FastAPI application hosting 3 trained ML models. "
                                       "Internal only (not exposed outside Docker network). "
                                       "Models persist in 'aimodels' Docker volume. "
                                       "Depends on: postgres."),
        ("pipeline-worker (no port)",  "One-shot Python script. Runs the 22-step pipeline once, "
                                       "then exits. Triggered manually via 'docker compose run'. "
                                       "Depends on: postgres, minio, ai-service."),
    ])

    pdf.sub("5.2  Data Flow")
    pdf.code(
        "pipeline-worker (run-once)\n"
        "  |-- generate 200 OSS + 200 BSS records\n"
        "  |-- upload raw JSON --> MinIO (raw bucket)\n"
        "  |-- process + enrich --> MinIO (processed bucket)\n"
        "  |-- POST /infer/sla-risk --> ai-service\n"
        "  |-- POST /infer/anomaly --> ai-service\n"
        "  |-- POST /infer/revenue-anomaly --> ai-service\n"
        "  |-- compute correlations (scipy)\n"
        "  |-- build curated dataset --> MinIO (curated bucket)\n"
        "  |-- INSERT results --> PostgreSQL (7 tables)\n"
        "\n"
        "api-gateway (:8000)\n"
        "  |-- SELECT --> PostgreSQL --> JSON response to user"
    )

    pdf.sub("5.3  Why This Architecture?")
    pdf.b([
        "Separation of concerns: each service has one job. Easier to test, deploy, scale.",
        "The AI service can be replaced with a different model without touching the pipeline.",
        "The API gateway can serve results to any frontend or dashboard tool.",
        "The pipeline worker can be scheduled (cron) or triggered by events.",
        "Every component maps directly to Huawei Cloud Stack (Section 11).",
    ])

    # ================================================================ 6
    pdf.add_page()
    pdf.sec("6", "The 22-Step Pipeline")

    steps = [
        ("Ensure MinIO buckets",
         "Creates 'raw', 'processed', 'curated' buckets if they don't exist."),
        ("Generate OSS data (with fault injection)",
         "200 records from 10 cells. Business-hour load curves (Gaussian peak at 13:00). "
         "2-3 random cells get fault injection: throughput collapse (x0.1-0.35), "
         "latency spike (x2.5-5.0), packet loss surge (+3-8%), signal degradation (-15 to -30 dBm)."),
        ("Generate BSS data (with correlated dips)",
         "200 subscriber records. 80% prepaid / 20% postpaid. Revenue in TND based on verified "
         "Tunisian operator forfait tiers (see Section 4). "
         "When a subscriber's serving cell is faulted, their data usage drops (x0.3-0.6), "
         "voice minutes drop (x0.4-0.7), churn risk spikes (+0.3-0.55)."),
        ("Upload OSS raw to MinIO",
         "JSON file -> s3://raw/oss/YYYY/MM/DD/<run_id>.json"),
        ("Upload BSS raw to MinIO",
         "JSON file -> s3://raw/bss/YYYY/MM/DD/<run_id>.json"),
        ("Insert pipeline_runs record",
         "PostgreSQL row tracking this execution: run_id, status='started', started_at."),
        ("Register raw datasets",
         "2 rows in dataset_registry: OSS raw + BSS raw, with object keys and row counts."),
        ("Process OSS -> processed layer",
         "Enriches records with: latency_severity (normal/medium/high/critical), "
         "throughput_category (good/fair/degraded), load_factor, qos_score. "
         "Strips is_fault flag. Uploads to s3://processed/oss/."),
        ("Process BSS -> processed layer",
         "Enriches records with: arpu_category (low <10 TND / mid <40 TND / high), "
         "data_intensity (GB per TND spent), churn_bucket (safe/watch/risk). "
         "Uploads to s3://processed/bss/."),
        ("Register processed datasets",
         "2 more rows in dataset_registry for the processed objects."),
        ("Compute aggregate features",
         "9 OSS features (mean/std/max of KPIs) + 6 BSS features (mean revenue, data, voice, "
         "sms, churn risk). These feed the AI models."),
        ("Call AI /infer/sla-risk",
         "Sends the 9-feature vector. Gets back: risk score (0-1), feature importances, "
         "top driver, model version."),
        ("Call AI /infer/anomaly",
         "Sends all 200 OSS records. IsolationForest returns per-record: is_anomaly flag + "
         "severity score (0-1). Typical: 5-15% anomaly rate with fault injection."),
        ("Call AI /infer/revenue-anomaly",
         "Sends all 200 BSS records. IsolationForest returns per-record: is_anomaly flag + "
         "severity score. Detects: SIM box fraud patterns, dormant SIMs, SMS spam, excessive usage."),
        ("Compute OSS-BSS correlations",
         "5 metric pairs x 2 methods = 10 correlation results. "
         "Pairs: latency<->revenue, throughput<->data_usage, packet_loss<->churn, "
         "latency<->churn, throughput<->revenue. Methods: Pearson (linear) + Spearman (monotonic)."),
        ("Build curated dataset",
         "Joins OSS + BSS at cell level. Includes: per-cell means, AI results, correlations. "
         "Uploads to s3://curated/joined/<run_id>_curated.json"),
        ("Register curated dataset",
         "1 row in dataset_registry for the curated object."),
        ("Persist SLA risk score",
         "Row in sla_risk_scores: score, JSONB explanation, model version, time window."),
        ("Persist OSS anomalies",
         "1 row per anomalous record in anomalies table: cell_id, severity, KPI value, baseline."),
        ("Persist revenue anomalies",
         "1 row per anomalous subscriber in revenue_anomalies: operator, plan, line_type, severity."),
        ("Register models",
         "3 rows in model_registry (ON CONFLICT DO NOTHING): sla-risk v2.0, anomaly v2.0, "
         "revenue-anomaly v2.0."),
        ("Persist correlations + mark succeeded",
         "10 rows in correlation_insights. Update pipeline_runs status='succeeded'."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(0, 6.5, f"  Step {i}: {title}",
                 fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*TEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(24)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(1.5)

    # ================================================================ 7
    pdf.add_page()
    pdf.sec("7", "AI/ML Models - Complete Breakdown")

    pdf.sub("7.1  Model 1: SLA Risk Scorer (GradientBoostingRegressor)")
    pdf.kv([
        ("Algorithm",        "GradientBoostingRegressor (scikit-learn)"),
        ("Task",             "Regression: predict SLA breach probability [0, 1]"),
        ("Input",            "9 aggregated OSS KPI features per 15-minute window"),
        ("Output",           "Continuous risk score 0.0 to 1.0 + feature importances"),
        ("Training samples", "3,000 synthetic windows with deterministic risk labels"),
        ("Hyperparameters",  "n_estimators=200, max_depth=4, learning_rate=0.05, "
                             "subsample=0.8, random_state=42"),
        ("Preprocessing",    "StandardScaler (zero mean, unit variance)"),
        ("Persistence",      "/app/models/sla_risk_model.joblib (Docker volume)"),
        ("Top feature",      "mean_latency_ms (importance ~0.69)"),
    ])

    pdf.sub2("Why GBR and Not Something Else?")
    pdf.kv([
        ("vs Linear Regression",  "Rejected. Latency-risk relationship is non-linear. "
                                  "Below 20ms = zero risk, above 60ms = high risk. "
                                  "Linear models cannot capture thresholds."),
        ("vs Neural Network",     "Rejected for Phase 2-3. Requires larger datasets. "
                                  "Poor interpretability (black box). "
                                  "Jury/supervisor cannot understand the output."),
        ("vs Random Forest",      "Considered. GBR outperforms RF on structured tabular data "
                                  "with <10K samples (Friedman 2001)."),
        ("Academic backing",      "Friedman (2001): GBR on tabular < 10K samples. "
                                  "Chen & Guestrin (2016): gradient boosting dominance on 29 datasets."),
    ])

    pdf.sub("7.2  Model 2: Network Anomaly Detector (IsolationForest)")
    pdf.kv([
        ("Algorithm",        "IsolationForest (scikit-learn)"),
        ("Task",             "Unsupervised anomaly detection on per-record OSS KPIs"),
        ("Input",            "5 per-record features: throughput, latency, packet_loss, "
                             "active_users, signal_rsrp"),
        ("Output",           "is_anomaly (bool) + severity score (0-1, normalized)"),
        ("Training samples", "3,000 records (95% normal, 5% injected faults)"),
        ("Contamination",    "0.05 (expects ~5% anomaly rate)"),
        ("Hyperparameters",  "n_estimators=150, random_state=42"),
        ("Persistence",      "/app/models/anomaly_model.joblib"),
    ])

    pdf.sub2("Why IsolationForest?")
    pdf.p(
        "Anomaly detection in telecom is an unsupervised problem: we don't have labeled "
        "'this record is anomalous' data (real operators rarely label anomalies consistently). "
        "IsolationForest works by isolating observations: anomalies are easier to separate "
        "from the rest because they are rare and different. It requires no labels, handles "
        "high-dimensional data efficiently, and is robust to contamination. "
        "Academic backing: Liu et al. (2008) 'Isolation-Based Anomaly Detection'."
    )

    pdf.sub("7.3  Model 3: Revenue Anomaly Detector (IsolationForest)")
    pdf.kv([
        ("Algorithm",        "IsolationForest (scikit-learn)"),
        ("Task",             "Unsupervised anomaly detection on BSS subscriber records"),
        ("Input",            "5 features: revenue_tnd, data_used_gb, voice_min, "
                             "sms_count, churn_risk"),
        ("Output",           "is_anomaly (bool) + severity score (0-1, normalized)"),
        ("Training samples", "3,000 records (95% normal Tunisian subscriber behavior, "
                             "5% anomalous: SIM box fraud, dormant SIMs, SMS spam)"),
        ("Persistence",      "/app/models/revenue_anomaly_model.joblib"),
    ])

    pdf.sub2("What Revenue Anomalies Look Like (Tunisian Market)")
    pdf.kv([
        ("SIM box fraud",     "Very high recharges (150-500 TND) + very high voice minutes "
                              "(800-2000 min). SIM boxes terminate international calls through "
                              "local SIMs, generating massive artificial traffic."),
        ("Dormant SIM",       "Near-zero revenue (<1 TND) + zero voice/data. Often stolen or "
                              "abandoned SIMs. Operator still pays for number allocation."),
        ("SMS spam",          "Normal revenue but SMS count 300-1000. Indicates a spam or "
                              "marketing abuse pattern."),
        ("Churn-correlated",  "High churn risk (>0.7) combined with abrupt usage drops. "
                              "Subscriber is about to leave the operator."),
    ])

    # ================================================================ 8
    pdf.add_page()
    pdf.sec("8", "Database Schema (7 Tables)")

    tables = [
        ("pipeline_runs",
         "Tracks every pipeline execution. 1 row per run.",
         [("run_id", "TEXT UNIQUE", "UUID-based identifier: run-<12 hex chars>"),
          ("status", "TEXT", "'started' or 'succeeded'"),
          ("started_at", "TIMESTAMPTZ", "When the pipeline began"),
          ("finished_at", "TIMESTAMPTZ", "When it completed (NULL if running)"),
          ("error_message", "TEXT", "Error details if it failed")]),
        ("dataset_registry",
         "Tracks every dataset object in MinIO. 5 rows per run (2 raw + 2 processed + 1 curated).",
         [("run_id", "TEXT FK", "Links to pipeline_runs"),
          ("dataset_type", "TEXT", "'oss', 'bss', or 'curated'"),
          ("layer", "TEXT", "'raw', 'processed', or 'curated'"),
          ("object_key", "TEXT", "MinIO path: oss/2026/03/09/run-xxx.json"),
          ("row_count", "BIGINT", "Number of records in the dataset")]),
        ("model_registry",
         "Tracks ML model versions. 3 rows (one per model). Uses ON CONFLICT DO NOTHING.",
         [("model_name", "TEXT", "'sla-risk', 'anomaly', or 'revenue-anomaly'"),
          ("version", "TEXT", "'v2.0'"),
          ("artifact_object_key", "TEXT", "Path to joblib file")]),
        ("sla_risk_scores",
         "SLA breach risk predictions. 1 row per pipeline run.",
         [("score", "DOUBLE", "Risk score 0.0 to 1.0"),
          ("explanation", "JSONB", "Feature importances, top driver, method"),
          ("window_start/end", "TIMESTAMPTZ", "15-minute window boundaries"),
          ("model_version", "TEXT", "'v2.0'")]),
        ("anomalies",
         "Per-record network anomalies. ~5-30 rows per run (depends on fault injection).",
         [("cell_id", "TEXT", "Which cell tower: CELL-001 to CELL-010"),
          ("kpi_name", "TEXT", "'composite_kpi'"),
          ("severity", "DOUBLE", "Anomaly severity 0.0 to 1.0"),
          ("value", "DOUBLE", "Actual KPI value that triggered the anomaly"),
          ("baseline_value", "DOUBLE", "Expected normal value (e.g., 25ms for latency)")]),
        ("revenue_anomalies",
         "Per-subscriber BSS anomalies. ~5-20 rows per run.",
         [("operator", "TEXT", "'Ooredoo Tunisie', 'Tunisie Telecom', or 'Orange Tunisie'"),
          ("subscriber_id", "TEXT", "TN-XXXXXX format"),
          ("line_type", "TEXT", "'prepaid' or 'postpaid'"),
          ("plan", "TEXT", "Forfait or postpaid plan name (e.g., 'data_25go', 'post_60')"),
          ("severity", "DOUBLE", "Anomaly severity 0.0 to 1.0"),
          ("value", "DOUBLE", "Revenue amount that triggered the anomaly")]),
        ("correlation_insights",
         "OSS-BSS statistical correlations. 10 rows per run (5 pairs x 2 methods).",
         [("metric_x", "TEXT", "OSS metric: mean_latency_ms, mean_throughput_mbps, etc."),
          ("metric_y", "TEXT", "BSS metric: mean_revenue_tnd, mean_churn_risk, etc."),
          ("method", "TEXT", "'pearson' or 'spearman'"),
          ("corr_value", "DOUBLE", "Correlation coefficient: -1.0 to +1.0"),
          ("p_value", "DOUBLE", "Statistical significance. <0.05 = significant")]),
    ]

    for tbl_name, tbl_desc, columns in tables:
        pdf.sub(tbl_name)
        pdf.p(tbl_desc)
        for col, dtype, desc in columns:
            pdf.set_x(24)
            pdf.set_font("Courier", "B", 8.5)
            pdf.cell(42, 5.5, col, new_x=XPos.RIGHT, new_y=YPos.LAST)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(26, 5.5, dtype, new_x=XPos.RIGHT, new_y=YPos.LAST)
            pdf.set_text_color(*TEXT)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5.5, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    # ================================================================ 9
    pdf.add_page()
    pdf.sec("9", "REST API (7 Endpoints)")

    endpoints = [
        ("GET /health",             "Service liveness check",
         "Returns {\"status\": \"ok\"}. Used by monitoring and health checks."),
        ("GET /sla-risk",           "Latest SLA risk score",
         "Returns the most recent SLA risk prediction with full explanation: score, "
         "feature importances, top driver, model version, time window."),
        ("GET /sla-risk/history",   "Historical SLA risk scores",
         "Query parameter: ?limit=N (default 20, max 200). Returns the last N scores "
         "ordered newest first. Useful for trend analysis."),
        ("GET /anomalies",          "Network anomalies",
         "Query parameter: ?limit=N (default 50, max 500). Returns detected OSS anomalies "
         "with cell_id, severity, KPI value, baseline value, model version."),
        ("GET /pipeline-runs",      "Pipeline execution history",
         "Query parameter: ?limit=N (default 10, max 100). Returns recent pipeline runs "
         "with status, timestamps, and error messages if any."),
        ("GET /revenue-anomalies",  "BSS revenue anomalies",
         "Query parameter: ?limit=N (default 50, max 500). Returns detected subscriber "
         "anomalies with operator, line_type, plan, severity, revenue value."),
        ("GET /correlation",        "OSS-BSS correlations",
         "Query parameter: ?limit=N (default 50, max 200). Returns Pearson and Spearman "
         "correlations between network metrics and business metrics."),
    ]
    for method, summary, desc in endpoints:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_font("Courier", "B", 10)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(0, 7, f"  {method}", fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*TEXT)
        pdf.cell(0, 6, f"  {summary}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(22)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(3)

    # ================================================================ 10
    pdf.add_page()
    pdf.sec("10", "Data Lake (3 Layers)")

    pdf.sub("10.1  Why a Data Lake?")
    pdf.p(
        "A data lake is an architectural pattern where raw data is stored as-is and "
        "progressively refined through layers. This is industry standard for any data-heavy "
        "platform. The pattern is sometimes called Bronze/Silver/Gold or Raw/Processed/Curated."
    )

    pdf.sub("10.2  Our 3 Layers")
    pdf.kv([
        ("RAW (MinIO 'raw' bucket)",
         "Original ingested data, unchanged. JSON files per run, date-partitioned: "
         "oss/YYYY/MM/DD/<run_id>.json and bss/YYYY/MM/DD/<run_id>.json. "
         "200 OSS records + 200 BSS records per run. "
         "Purpose: data lineage, reproducibility, audit trail."),
        ("PROCESSED (MinIO 'processed' bucket)",
         "Cleaned + enriched data. OSS records gain: latency_severity, throughput_category, "
         "load_factor, qos_score. BSS records gain: arpu_category, data_intensity, churn_bucket. "
         "is_fault flag is stripped (raw-only metadata). "
         "Purpose: feature-ready data for analytics and model training."),
        ("CURATED (MinIO 'curated' bucket)",
         "Final joined dataset. OSS + BSS aggregated at cell level + AI results + correlations. "
         "One JSON object per run with: sla_risk_score, oss_anomaly_count, bss_anomaly_count, "
         "per-cell means (throughput, latency, revenue, churn), all correlations. "
         "Purpose: single-source-of-truth for dashboards and reports."),
    ])

    # ================================================================ 11
    pdf.sec("11", "Huawei Cloud Stack Mapping")

    pdf.p(
        "The entire architecture is designed to be deployable on Huawei Cloud Stack (HCS) "
        "with zero architectural changes. Only infrastructure is swapped:"
    )
    pdf.kv([
        ("Docker containers",        "-> ECS (Elastic Cloud Server). Each service becomes an ECS instance "
                                     "or can be containerized on CCE (Cloud Container Engine)."),
        ("MinIO (object storage)",   "-> OBS (Object Bucket Service). Same S3-compatible API. "
                                     "Just change the endpoint URL and credentials."),
        ("PostgreSQL container",     "-> RDS for PostgreSQL. Managed database service. "
                                     "Same SQL schema, same psycopg2 driver, just change DATABASE_URL."),
        ("Docker network",           "-> VPC (Virtual Private Cloud). Same internal addressing. "
                                     "Security groups replace Docker network isolation."),
        ("Env-var secrets",          "-> IAM + KMS. Database passwords and S3 keys stored "
                                     "in Huawei Key Management Service instead of plain env vars."),
    ])

    # ================================================================ 12
    pdf.add_page()
    pdf.sec("12", "What's Built vs Planned (Roadmap)")

    pdf.sub("12.1  Completed Phases")
    phases_done = [
        ("Phase 1: Vertical Slice",
         "Full data flow: synthetic generation -> MinIO upload -> PostgreSQL persistence -> "
         "REST API serving. 12-step pipeline. 5 API endpoints. All tables populated."),
        ("Phase 2: Real ML Inference",
         "GradientBoostingRegressor for SLA risk + IsolationForest for anomaly detection. "
         "Real trained models with feature importances. Model persistence via joblib."),
        ("Phase 3: Rich Data + Revenue Anomaly + Correlations",
         "Fault injection in synthetic data (business-hour curves, cell degradation). "
         "Correlated BSS dips. Revenue anomaly model (IsolationForest on BSS). "
         "OSS-BSS correlation engine (Pearson + Spearman, 5 pairs). "
         "Processed + curated data lake layers. model_registry + correlation_insights populated. "
         "Tunisian prepaid market model based on VERIFIED 2025 operator forfait data. "
         "22-step pipeline. 7 API endpoints. 7 tables."),
    ]
    for title, desc in phases_done:
        pdf.badge("COMPLETED", GREEN)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_x(22)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(3)

    pdf.sub("12.2  Planned Phases")
    phases_planned = [
        ("Phase 4: Labeled Evaluation",
         "Create labeled test dataset with known anomalies. Compute precision, recall, "
         "F1 score for each model. Generate evaluation report for PFE defense."),
        ("Phase 5: Observability (Prometheus + Grafana)",
         "Add Prometheus metrics collection from all services. Grafana dashboards for: "
         "pipeline run history, SLA risk trends, anomaly rates, system metrics."),
        ("Phase 6: HCS Deployment",
         "Deploy on actual Huawei Cloud Stack: OBS buckets, RDS PostgreSQL, ECS instances. "
         "Produce evidence screenshots for PFE report. Highest impression-to-effort ratio "
         "for Huawei audience."),
    ]
    for title, desc in phases_planned:
        pdf.badge("PLANNED", ORANGE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_x(22)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(3)

    # ================================================================ 13
    pdf.add_page()
    pdf.sec("13", "Sources & References")

    pdf.sub("13.1  Standards & Specifications")
    refs_std = [
        "[1]  3GPP TS 28.554 - Management and Orchestration; 5G End-to-End KPIs. "
        "Defines throughput, latency, packet loss KPIs used in our OSS data model.",
        "[2]  3GPP TS 36.314 - E-UTRAN; Layer 2 Measurements. "
        "Defines cell-level load and resource utilization measurements.",
        "[3]  3GPP TS 36.214 - E-UTRAN; Physical Layer Measurements. "
        "Defines RSRP (Reference Signal Received Power) used as signal strength metric.",
        "[4]  ITU-T Y.1541 - Network Performance Objectives for IP-Based Services. "
        "Defines latency, packet loss, and jitter thresholds by service class.",
        "[5]  TM Forum GB917 - SLA Management Handbook. "
        "Framework for defining, measuring, and managing SLA compliance.",
        "[6]  TM Forum TR255 - Quality of Experience (QoE) to Quality of Service (QoS) Correlation.",
        "[7]  ETSI GS NFV 003 - Network Functions Virtualisation; Terminology.",
    ]
    for ref in refs_std:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(22)
        pdf.multi_cell(0, 5, ref)
        pdf.ln(1)

    pdf.sub("13.2  Academic References")
    refs_acad = [
        "[8]   Friedman, J. (2001). 'Greedy Function Approximation: A Gradient Boosting Machine'. "
        "Annals of Statistics 29(5). Justification for GBR on small tabular datasets.",
        "[9]   Chen, T. & Guestrin, C. (2016). 'XGBoost: A Scalable Tree Boosting System'. "
        "KDD 2016. Gradient boosting superiority on structured data.",
        "[10]  Liu, F.T. et al. (2008). 'Isolation Forest'. IEEE ICDM 2008.",
        "[11]  Pedregosa, F. et al. (2011). 'Scikit-learn: ML in Python'. JMLR 12.",
        "[12]  Sculley, D. et al. (2015). 'Hidden Technical Debt in ML Systems'. NeurIPS.",
    ]
    for ref in refs_acad:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(22)
        pdf.multi_cell(0, 5, ref)
        pdf.ln(1)

    pdf.sub("13.3  Tunisian Market Sources (Verified 2025)")
    refs_tn = [
        "[13]  INTT (Instance Nationale des Telecommunications) - Annual Report 2023. "
        "URL: intt.tn/publications. "
        "Subscriber counts, ARPU, prepaid/postpaid split, SMS decline statistics.",
        "[14]  GSMA Intelligence - Tunisia Country Profile 2023. "
        "URL: gsmaintelligence.com. "
        "Mobile penetration, average data usage (4.2 GB/month), market structure.",
        "[15]  Orange Tunisie - Prepaid Options Page (LIVE, fetched March 2026). "
        "URL: orange.tn/options-offres-mobile-prepayees. "
        "Complete prepaid data bundle pricing: 100 Mo at 0.5 DT through 500 Go at 250 DT. "
        "USSD: *124# (primary), *120# (7-day options).",
        "[16]  Tunisie Telecom - Forfaits Internet Mobile Page. "
        "URL: tunisietelecom.tn/particulier/mobile/internet-mobile/forfaits/. "
        "Confirmed by: lapresse.tn (14 Feb 2025) and thd.tn (28 Feb 2025). "
        "USSD: *140# standard, *540# BIG forfaits. Key tiers: 4 Go/10 DT, 25 Go/30 DT, "
        "45 Go/50 DT, 110 Go/80 DT, 200 Go/100 DT.",
        "[17]  Ooredoo Tunisie - Complete Flexi Forfaits Page (PRIMARY SOURCE, live March 2026). "
        "URL: ooredoo.tn/Personal/en/content/272-les-nouveaux-flexi. "
        "Full HTML price tables fetched: micro range (50MB/0.25DT to 8Go/20DT) and "
        "Flexi+ range (10Go/25DT to 1000Go/500DT). USSD: *124#. "
        "Menu structure cross-verified by live *124# USSD screenshot (device, March 2026).",
        "[18]  THD.tn - Comparatif forfaits Data 5G Tunisia (18 Feb 2025). "
        "URL: thd.tn/mise-a-jour-comparatif-des-forfaits-data-5g-en-tunisie... "
        "Independent cross-operator analysis at 5G launch. "
        "Confirms: all 3 operators at 25 Go/30 DT; TT 45 Go/50 DT best monthly value; "
        "Ooredoo leads on high-volume (500 Go, 1 To).",
        "[19]  THD.tn - Tunisie Telecom revoit ses forfaits (28 Feb 2025). "
        "URL: thd.tn/tunisie-telecom-revoit-ses-forfaits-internet-mobile-plus-de-data-et-des-prix-ajustes/. "
        "Documents TT's February 2025 price revision: 4 Go/10 DT (down from 3.5 DT/Go), "
        "new BIG forfaits 110 Go/80 DT and 200 Go/100 DT.",
        "[20]  Ooredoo Tunisie Annual Report 2023. "
        "Subscriber count ~7.5M, Ooredoo Group parent (Qatar). ooredoo.tn.",
        "[21]  Tunisie Telecom Annual Report 2023. "
        "Subscriber count ~8.2M, state-owned incumbent. tunisietelecom.tn.",
        "[22]  INS (Institut National de la Statistique) - Tunisia Demographics 2023. "
        "Population ~12M, mobile penetration ~180%. ins.tn.",
    ]
    for ref in refs_tn:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(22)
        pdf.multi_cell(0, 5, ref)
        pdf.ln(1)

    pdf.sub("13.4  Technology References")
    refs_tech = [
        "[23]  FastAPI Documentation (fastapi.tiangolo.com). REST API framework.",
        "[24]  PostgreSQL 16 Documentation (postgresql.org). Database system.",
        "[25]  MinIO Documentation (min.io). S3-compatible object storage.",
        "[26]  Docker Documentation (docs.docker.com). Containerization.",
        "[27]  Huawei Cloud Stack Documentation. HCS service mapping (ECS, OBS, RDS).",
        "[28]  SciPy Documentation (scipy.org). Pearson/Spearman correlation functions.",
    ]
    for ref in refs_tech:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(22)
        pdf.multi_cell(0, 5, ref)
        pdf.ln(1)

    # ── save ──
    pdf.output(OUT)
    print(f"\nPDF generated: {OUT}")
    print(f"Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build()