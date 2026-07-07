"""render_reports.py — 30 inspection + 15 incident report PDFs.

Tier-1 depth on the hero assets: each hero operational_history_note (incl. the
flush-plan thread) becomes a full report. Tier-2/3 assets get one-page reports
templated from registry facts. The document catalogue (catalogue.report_docs)
decides which reports exist and where; this generator only renders them.
"""

from __future__ import annotations

from catalogue import load_design, report_docs, stable_rng
from pdf_helpers import OcePDF, save_pdf


def _asset_kv(pdf: OcePDF, asset: dict) -> None:
    pdf.kv_table(
        [
            ("Asset tag", asset["tag"]),
            ("Name", asset["name"]),
            ("Class", asset["class"]),
            ("Plant / Unit / Area", f"{asset['plant']} / {asset['unit']} / {asset['area']}"),
            ("Service duty", asset["service_duty"]),
            ("Criticality", asset["criticality"]),
            ("Installed on", str(asset["installed_on"])),
        ],
        ("Field", "Value"),
    )


_FILLER_INSPECTION = [
    "Routine inspection carried out. Equipment found in satisfactory operating condition with no abnormality requiring corrective action at this time.",
    "General condition inspection completed. Readings within normal limits; housekeeping and external condition acceptable. Continue normal monitoring.",
    "Scheduled inspection performed. No leaks, abnormal noise or vibration observed. Equipment fit for continued service.",
]
_FILLER_INCIDENT = [
    "Minor operational upset attended. Equipment restored to service after checks; no lasting damage identified. Root cause considered routine.",
    "Trip investigated. Normal parameters confirmed on restart; monitoring continued. No corrective maintenance required beyond reset.",
    "Reported abnormality attended. On inspection no defect confirmed; equipment returned to service.",
]


def render(design: dict) -> None:
    notes = {n["id"]: n for n in design["operational_history_notes"]}
    assets = {a["tag"]: a for a in design["assets"]}
    metas = report_docs(design)

    total = 0
    for meta in metas:
        pdf = OcePDF(doc_no=meta.rel_path.rsplit("/", 1)[-1].replace(".pdf", ""))
        kind_label = "Inspection Report" if meta.doc_type == "inspection_report" else "Incident Report"
        asset = assets.get(meta.owner_tag) if meta.owner_tag else None

        pdf.title_block(meta.title, f"{kind_label}  |  {'Tier 1' if meta.tier == 1 else 'Tier ' + str(meta.tier)}")
        if asset:
            pdf.h1("1", "Asset")
            _asset_kv(pdf, asset)

        if meta.note_id:
            note = notes[meta.note_id]
            pdf.h1("2", "Findings")
            pdf.para(note["body"])
            pdf.h1("3", "Recommendation")
            if "flush" in note["body"].lower() or "seal" in note["body"].lower():
                pdf.para(
                    "Verify the seal flush plan on this and the sister CP200 pumps "
                    "against the OEM MSC-CP200 manual (API Plan 11) and correct any "
                    "field deviation before further seal replacement."
                )
            else:
                pdf.para("Continue condition monitoring per the PM schedule.")
        else:
            pool = _FILLER_INSPECTION if meta.doc_type == "inspection_report" else _FILLER_INCIDENT
            rng = stable_rng("report-body", meta.rel_path)
            pdf.h1("2", "Summary")
            pdf.para(pool[rng.randrange(len(pool))])

        total += save_pdf(pdf, meta.abs_path)

    n_insp = sum(1 for m in metas if m.doc_type == "inspection_report")
    n_inc = sum(1 for m in metas if m.doc_type == "incident_report")
    print(f"render_reports: {n_insp} inspection + {n_inc} incident reports, {total} B")


def main() -> None:
    from validate_design import validate_design

    design = load_design()
    validate_design(design)
    render(design)


if __name__ == "__main__":
    main()
