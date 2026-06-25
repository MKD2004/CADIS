"""
scripts/seed_documents.py
=========================
Seeds ChromaDB with sample documents so first-time users have data to explore.
Idempotent — skips documents whose chunks already exist.

Called automatically during FastAPI lifespan startup.
"""

from __future__ import annotations

from core.logging import get_logger
from services.vector_store import VectorStoreService

logger = get_logger(__name__)

SAMPLE_DOCUMENTS: list[dict] = [
    {
        "id": "sample-cybersec-01",
        "title": "APT29 Threat Intelligence Report",
        "type": "sample_doc",
        "text": (
            "APT29, also known as Cozy Bear, is a cyber espionage group attributed to "
            "Russia's Foreign Intelligence Service (SVR). The group has been active since "
            "at least 2008 and is known for targeting government networks, think tanks, "
            "and critical infrastructure across NATO member states.\n\n"
            "In December 2020, APT29 was identified as the primary threat actor behind "
            "the SolarWinds supply chain attack, which compromised the Orion software "
            "update mechanism. The attack affected approximately 18,000 organizations "
            "including the U.S. Treasury Department, the Department of Homeland Security, "
            "and FireEye. The malware, dubbed SUNBURST, was embedded into legitimate "
            "software updates distributed between March and June 2020.\n\n"
            "The group employs sophisticated techniques including custom malware families "
            "such as WellMess, WellMail, and EnvyScout. Their tactics include spear-phishing "
            "campaigns, exploitation of zero-day vulnerabilities (CVE-2023-42793 in JetBrains "
            "TeamCity), and abuse of cloud services for command and control. APT29 has "
            "demonstrated the ability to maintain persistent access to compromised networks "
            "for extended periods, sometimes exceeding 12 months before detection.\n\n"
            "MITRE ATT&CK techniques commonly associated with APT29 include Initial Access "
            "via Supply Chain Compromise (T1195), Execution via Command and Scripting "
            "Interpreter (T1059), Persistence via Account Manipulation (T1098), and "
            "Exfiltration via Web Service (T1567). Defenders are advised to implement "
            "network segmentation, monitor for anomalous OAuth token usage, and deploy "
            "endpoint detection and response (EDR) solutions across all critical assets."
        ),
    },
    {
        "id": "sample-legal-01",
        "title": "Meridian Corp Acquisition Agreement Summary",
        "type": "sample_doc",
        "text": (
            "MERGER AGREEMENT SUMMARY — CONFIDENTIAL\n\n"
            "Parties: Meridian Corporation ('Acquirer'), a Delaware corporation with "
            "principal offices at 400 Park Avenue, New York, NY 10022, and NovaTech "
            "Solutions Inc. ('Target'), a California corporation headquartered at "
            "1200 Innovation Drive, Palo Alto, CA 94301.\n\n"
            "Transaction: Meridian agrees to acquire 100% of the outstanding shares of "
            "NovaTech for total consideration of $3.2 billion, comprising $2.4 billion in "
            "cash and $800 million in Meridian common stock at the 30-day VWAP preceding "
            "the closing date. The per-share price represents a 34% premium to NovaTech's "
            "unaffected closing price of $47.50 on March 15, 2025.\n\n"
            "Key Conditions: The closing is subject to (a) approval by NovaTech shareholders "
            "holding not less than two-thirds of outstanding shares, (b) regulatory clearance "
            "from the Federal Trade Commission and the European Commission under the EU "
            "Merger Regulation (EC 139/2004), (c) absence of any Material Adverse Effect, "
            "and (d) receipt of required third-party consents from licensors representing "
            "at least 85% of NovaTech's annual recurring revenue.\n\n"
            "Termination: Either party may terminate this Agreement if the closing has not "
            "occurred by September 30, 2025 (the 'Outside Date'). The Target shall pay a "
            "termination fee of $160 million (5% of equity value) if the Board withdraws "
            "its recommendation in favor of a Superior Proposal. The Acquirer shall pay a "
            "reverse termination fee of $240 million if it fails to obtain financing.\n\n"
            "Governing Law: This Agreement shall be governed by the laws of the State of "
            "Delaware without regard to conflict of law principles. Any disputes arising "
            "hereunder shall be submitted to the exclusive jurisdiction of the Court of "
            "Chancery of the State of Delaware. Attorneys Sarah Chen (Wachtell Lipton) "
            "and James Rodriguez (Skadden Arps) have reviewed and approved this summary "
            "on behalf of the respective parties."
        ),
    },
    {
        "id": "sample-medical-01",
        "title": "Clinical Case Study: Acute Myocardial Infarction",
        "type": "sample_doc",
        "text": (
            "CLINICAL CASE REPORT\n"
            "Department of Cardiology, St. Mary's Medical Center, Chicago, IL\n\n"
            "Patient: John M. Patterson, 58-year-old male, BMI 31.2\n"
            "Date of Admission: January 12, 2025\n"
            "Attending Physician: Dr. Emily Chen, MD, FACC\n\n"
            "Presenting Complaint: The patient presented to the Emergency Department at "
            "06:45 AM with acute substernal chest pain radiating to the left arm and jaw, "
            "onset approximately 90 minutes prior to arrival. Associated symptoms included "
            "diaphoresis, nausea, and dyspnea. Pain was rated 9/10 on the visual analog "
            "scale and was unresponsive to sublingual nitroglycerin administered by EMS.\n\n"
            "Medical History: Hypertension (diagnosed 2018, managed with lisinopril 20mg "
            "daily), Type 2 diabetes mellitus (HbA1c 7.8%, metformin 1000mg BID), "
            "hyperlipidemia (atorvastatin 40mg daily), and a 25-pack-year smoking history "
            "(quit 2022). Family history significant for coronary artery disease in father "
            "(MI at age 52) and brother (CABG at age 60).\n\n"
            "Diagnostic Findings: Initial 12-lead ECG demonstrated ST-segment elevation "
            "in leads II, III, aVF, and V5-V6, consistent with inferolateral STEMI. "
            "Troponin I was elevated at 12.4 ng/mL (normal <0.04). Bedside echocardiogram "
            "revealed hypokinesis of the inferior and lateral walls with estimated LVEF of "
            "35%. Coronary angiography identified a 99% occlusion of the proximal left "
            "circumflex artery (LCx) with TIMI 0 flow.\n\n"
            "Treatment: Primary percutaneous coronary intervention (PCI) was performed by "
            "Dr. Robert Williams within 62 minutes of arrival (door-to-balloon time). A "
            "3.5mm x 28mm drug-eluting stent (Xience Sierra, Abbott) was deployed to the "
            "proximal LCx with restoration of TIMI 3 flow. Post-procedure medications "
            "included dual antiplatelet therapy (aspirin 81mg daily, ticagrelor 90mg BID), "
            "high-intensity statin (rosuvastatin 40mg), ACE inhibitor (ramipril 5mg), and "
            "beta-blocker (metoprolol succinate 50mg daily). Total hospitalization cost "
            "was $94,500.\n\n"
            "Outcome: The patient was discharged on January 16, 2025 in stable condition. "
            "Follow-up echocardiogram at 6 weeks showed improved LVEF of 45%. Cardiac "
            "rehabilitation was initiated. Follow-up with Dr. Chen scheduled for March 10, "
            "2025."
        ),
    },
]

_CHUNK_SIZE = 400  # words per chunk


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), _CHUNK_SIZE):
        chunk = " ".join(words[i : i + _CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def seed_sample_documents() -> None:
    try:
        vs = VectorStoreService.get_instance()
    except Exception as exc:
        logger.warning("Cannot seed samples — VectorStore not ready: %s", exc)
        return

    collection_name = vs._settings.chroma_default_collection

    for doc in SAMPLE_DOCUMENTS:
        doc_id = doc["id"]

        try:
            coll = vs._get_or_create_collection(collection_name)
            existing = coll.get(where={"document_id": {"$eq": doc_id}})
            if existing["ids"]:
                logger.info("[seed] SKIP  '%s' — already loaded (%d chunks)", doc["title"], len(existing["ids"]))
                continue
        except Exception:
            pass

        chunks = _chunk_text(doc["text"])
        vs.upsert_document(
            document_id=doc_id,
            chunks=chunks,
            collection_name=collection_name,
            extra_metadata={
                "source": "sample",
                "title": doc["title"],
                "type": doc["type"],
            },
        )
        logger.info("[seed] OK    '%s' — ingested %d chunks", doc["title"], len(chunks))

    logger.info("[seed] Sample document seeding complete.")
