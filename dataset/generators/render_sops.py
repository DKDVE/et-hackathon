"""render_sops.py — 10 SOP PDFs.

Tier-1 SOPs (isolation & seal replacement, hot work, LOTO) carry full numbered
steps; the rest are thin. One SOP (SOP-001) gets a final image-only page — a
'scanned' sign-off sheet with no text layer — as the honest OCR-demo page
(TDD §8): M3's pypdf extraction yields <30 chars there and falls back to OCR.
"""

from __future__ import annotations

from catalogue import load_design, sop_docs
from pdf_helpers import OcePDF, render_text_image, save_pdf


def _render_one(sop: dict, out_path) -> int:
    pdf = OcePDF(doc_no=sop["id"])
    pdf.title_block(f"{sop['id']} — {sop['title']}", f"Standard Operating Procedure  |  Tier {sop['tier']}")
    pdf.h1("1", "Purpose")
    pdf.para(sop["purpose"])
    pdf.h1("2", "Procedure")
    pdf.numbered_steps(sop["steps"])

    if sop.get("scanned_page"):
        # Build the scanned sign-off sheet as an image, then embed it full-page.
        scan_png = out_path.parent / f"_scan_{sop['id']}.png"
        render_text_image(
            f"{sop['id']} — Completion & Sign-off (scanned)",
            [
                "This page is a scanned sign-off sheet.",
                "",
                "Work carried out by: ______________________",
                "Checked by (supervisor): __________________",
                "Permit number: ___________________________",
                "Seal flush plan verified as OEM Plan 11:  Y / N",
                "Date: ____________   Time: ____________",
                "",
                "Signature: ________________________________",
            ],
            scan_png,
        )
        pdf.add_page()
        pdf.image(str(scan_png), x=0, y=0, w=pdf.w, h=pdf.h)

    return save_pdf(pdf, out_path)


def render(design: dict) -> None:
    metas = {m.title: m for m in sop_docs(design)}
    total = 0
    for sop in design["documents"]["sops"]:
        meta = metas[sop["title"]]
        size = _render_one(sop, meta.abs_path)
        total += size
    print(f"render_sops: {len(design['documents']['sops'])} SOPs rendered, {total} B")


def main() -> None:
    from validate_design import validate_design

    design = load_design()
    validate_design(design)
    render(design)


if __name__ == "__main__":
    main()
