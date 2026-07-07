"""render_manual.py — hero-class OEM manual PDF (Tier 1, ~40pp).

Formats the authored content in meridian.yaml (documents.manual). The generator
never authors facts (P10) — it only lays them out with clear numbered headings
so the M3 structure-aware chunker can split on them.
"""

from __future__ import annotations

from catalogue import load_design, manual_doc
from pdf_helpers import OcePDF, save_pdf


def _toc(pdf: OcePDF, sections: list[dict]) -> None:
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 8, "Contents")
    pdf.ln(3)
    for sec in sections:
        pdf.toc_line(f"{sec['number']}. {sec['title']}")
        for sub in sec.get("subsections", []):
            pdf.toc_line(f"{sub['number']} {sub['title']}", indent=10)
    pdf.ln(2)


def _hero_datasheets(pdf: OcePDF, design: dict) -> None:
    """Appendix A — per-installed-pump data sheets (real facts from the registry)."""
    pdf.h1("A", "Appendix — Installed Pump Data Sheets")
    heroes = [a for a in design["assets"] if a.get("hero")]
    for a in heroes:
        pdf.h2(f"A.{heroes.index(a) + 1}", f"{a['tag']} — {a['name']}")
        pdf.kv_table(
            [
                ("Tag", a["tag"]),
                ("Service duty", a["service_duty"]),
                ("Plant / Unit", f"{a['plant']} / {a['unit']}"),
                ("Area", a["area"]),
                ("Criticality", a["criticality"]),
                ("Installed on", str(a["installed_on"])),
                ("Seal flush plan", "API Plan 11 (OEM)"),
            ],
            ("Parameter", "Value"),
        )


def _commissioning_checklist(pdf: OcePDF) -> None:
    pdf.h1("B", "Appendix — Commissioning Checklist")
    items = [
        "Foundation grouted and level; soft foot within 0.05 mm at each foot.",
        "Pipework independently supported; no nozzle loads on the pump.",
        "Coupling aligned cold to 0.05 mm parallel / angular.",
        "Seal flush confirmed as OEM API Plan 11 with correct orifice size.",
        "Seal flush line clean and unrestricted; flush flow within data-sheet range.",
        "Direction of rotation verified before coupling connected.",
        "Bearing lubrication confirmed correct grade and quantity.",
        "Suction strainer fitted and clean.",
        "Instrumentation (vibration, bearing/seal temperature) commissioned.",
        "Hot alignment re-checked after first run at temperature.",
    ]
    pdf.numbered_steps(items)


def render(design: dict) -> int:
    m = design["documents"]["manual"]
    meta = manual_doc(design)
    pdf = OcePDF(doc_no=m["doc_no"])

    pdf.title_block(m["title"], f"{m['doc_no']}  |  Rheinwerk Pumps GmbH")
    pdf.para(m["intro"])
    _toc(pdf, m["sections"])

    for sec in m["sections"]:
        pdf.h1(sec["number"], sec["title"])
        for p in sec.get("paragraphs", []):
            pdf.para(p)
        for sub in sec.get("subsections", []):
            pdf.h2(sub["number"], sub["title"])
            for p in sub.get("paragraphs", []):
                pdf.para(p)
            if sub.get("steps"):
                pdf.numbered_steps(sub["steps"])
        # Section 6 troubleshooting table.
        if sec.get("troubleshooting"):
            pdf.wide_table(
                ["Symptom", "Probable cause", "Recommended action"],
                [[t["symptom"], t["cause"], t["action"]] for t in sec["troubleshooting"]],
                (50, 55, 65),
            )
        # Section 7 parts + torque tables.
        if sec.get("parts"):
            pdf.h2(f"{sec['number']}.1", "Recommended Spare Parts")
            pdf.wide_table(
                ["Item", "Part number", "Material", "Qty"],
                [[p["item"], p["part_no"], p["material"], p["qty"]] for p in sec["parts"]],
                (60, 55, 45, 20),
            )
        if sec.get("torques"):
            pdf.h2(f"{sec['number']}.2", "Fastener Torque Values")
            pdf.kv_table(
                [(t["fastener"], t["value"]) for t in sec["torques"]],
                ("Fastener", "Torque"),
            )
        # Section 8 technical data.
        if sec.get("technical_data"):
            pdf.kv_table(
                [(t["parameter"], t["value"]) for t in sec["technical_data"]],
                ("Parameter", "Value"),
            )

    _hero_datasheets(pdf, design)
    _commissioning_checklist(pdf)

    size = save_pdf(pdf, meta.abs_path)
    print(f"render_manual: {meta.abs_path.name} — {pdf.page_no()} pages, {size} B")
    return size


def main() -> None:
    from validate_design import validate_design

    design = load_design()
    validate_design(design)
    render(design)


if __name__ == "__main__":
    main()
