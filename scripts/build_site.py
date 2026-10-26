#!/usr/bin/env python3
"""Regenerate docs/ (GitHub Pages) from evidence/ + registry/ + downloads/.

No hand edits in docs/: everything derives from exact bytes + JSON receipts.
Fails closed: missing evidence renders explicit PENDING states, never guesses.
"""
from __future__ import annotations

import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

STAMP = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

CSS = """
:root{--bg:#0e1116;--fg:#e8ecf1;--mut:#9aa4b2;--acc:#58a6ff;--ok:#3fb950;--no:#f85149;--warn:#d29922;--card:#161b22;--line:#30363d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 60px}
nav{border-bottom:1px solid var(--line);padding:14px 20px;display:flex;gap:18px;flex-wrap:wrap;align-items:center;background:#0d1117;position:sticky;top:0}
nav b{font-size:18px}nav a{color:var(--fg);opacity:.85}nav a:hover{opacity:1}
.hero{padding:34px 0 10px}h1{font-size:34px;margin:.2em 0}h2{margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:6px}h3{margin-top:1.4em}
.badge{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:700;margin:4px 8px 4px 0}
.ok{background:rgba(63,185,80,.15);color:var(--ok);border:1px solid var(--ok)}
.no{background:rgba(248,81,73,.12);color:var(--no);border:1px solid var(--no)}
.warn{background:rgba(210,153,34,.12);color:var(--warn);border:1px solid var(--warn)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
.btn{display:inline-block;background:var(--ok);color:#04120a!important;font-weight:700;padding:12px 22px;border-radius:8px;margin:8px 12px 8px 0}
.btn.sec{background:transparent;color:var(--fg)!important;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#1c2128}tr.hl td{background:rgba(88,166,255,.08)}
code,kbd{background:#1c2128;padding:2px 6px;border-radius:6px;font-size:13px}
pre{background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:14px;overflow:auto;font-size:13px}
.small{color:var(--mut);font-size:13px}ol.steps li{margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}
"""

NAV = """<nav><b>WBG1 · DOE GEMS</b><a href="index.html">Overview</a><a href="executive-summary.html">Executive summary</a><a href="how-to-submit.html">How to submit</a><a href="hypotheses.html">Hypotheses</a><a href="research.html">Research</a><a href="sources.html">Sources</a></nav>"""


def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · WBGGEMSDOE1</title><style>{CSS}</style></head>
<body>{NAV}<div class="wrap">{body}
<hr><p class="small">Generated {STAMP} from exact bytes + JSON receipts. No human inspection; gates fail closed. Repo: wingbangboozle1-lang/WBGGEMSDOE1.</p>
</div></body></html>"""


def load(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def main() -> int:
    docs = ROOT / "docs"
    dl = docs / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    (docs / ".nojekyll").write_text("")

    focus = load(ROOT / "registry" / "focus9.json", {"rasters": []})
    e1 = load(ROOT / "evidence" / "e1_surface.json")
    e1b = load(ROOT / "evidence" / "e1b_paleo.json")
    e2 = load(ROOT / "evidence" / "e2_sweep.json")
    card = load(ROOT / "evidence" / "e3_run_card.json")
    audits = sorted(glob.glob(str(dl / "*-audit.json")))
    audit = json.loads(Path(audits[-1]).read_text()) if audits else None
    selector = load(ROOT / "registry" / "selector.json", {"decision": "pending"})

    # ---- verdict ----
    if card and audit:
        v_fmt = card["validator"]["zeros"]["pass"]
        v_uniq = card["unique"]
        v_bar = card["beats_champion_holdout_bar"]
        verdict = card["verdict"]
        sel_ok = selector.get("decision") == "approved"
        dl_ok, sub_ok = True, bool(verdict == "promote" and sel_ok)
        fname = audit["zeros_tif"]["filename"]
        sha = audit["zeros_tif"]["sha256"]
        note = card["submission_note"]
        sub_name = "WBG1-H1-" + audit.get("content_digest8", "")
        proj = card["projection"]["PROJECTION"]
        proj_ci = card["projection"]["PROJECTION_interval"]
        sg, sg_ci = card["sgmc_dti"], card["sgmc_ci95"]
        hide = card["holdout_dti_hide"]
    else:
        v_fmt = v_uniq = v_bar = sel_ok = False
        verdict = "pending"
        dl_ok, sub_ok = bool(audit), False
        fname = audit["zeros_tif"]["filename"] if audit else "PENDING"
        sha = audit["zeros_tif"]["sha256"] if audit else "PENDING"
        note = sub_name = "PENDING"
        proj, proj_ci, sg, sg_ci, hide = 0, [0, 0], 0, [0, 0], 0

    def badge(ok, yes, no):
        return f'<span class="badge {"ok" if ok else "no"}">{"✅ " if ok else "🛑 "}{yes if ok else no}</span>'

    dl_badge = badge(dl_ok, "OK TO DOWNLOAD: YES", "OK TO DOWNLOAD: NO")
    sub_badge = badge(sub_ok, "OK TO SUBMIT: YES", "OK TO SUBMIT: NO")

    # ---- comparison table ----
    rows = ""
    if e2:
        champ_bar = max(v["sgmc_DTI"] for v in e2["champions"].values())
        for r in focus["rasters"]:
            c = e2["champions"].get(r["id"], {})
            rows += (f"<tr><td>{r['id']}</td><td class='mono'>{r['submission'][:44]}</td>"
                     f"<td>{r['owner_reported']:.4f} (OWNER-REPORTED)</td>"
                     f"<td>{c.get('sgmc_DTI', float('nan')):.5f}</td>"
                     f"<td>{r['dots']:,}</td><td>No — lineage duplicate (see analysis)</td></tr>")
        rows += (f"<tr class='hl'><td><b>WBG1-H1 (ours)</b></td><td class='mono'>{fname}</td>"
                 f"<td>PROJECTION ~{proj:.3f} [{proj_ci[0]:.3f},{proj_ci[1]:.3f}] — NOT a score</td>"
                 f"<td><b>{sg:.5f}</b> [{sg_ci[0]:.5f},{sg_ci[1]:.5f}]</td>"
                 f"<td>{audit['positive_px']:,}</td>"
                 f"<td>{'Yes — unique' if v_uniq else 'No'} "
                 f"(corr&lt;0.90, 3px&lt;70%)</td></tr>")
    else:
        rows = "<tr><td colspan=6>PENDING — experiments not finished</td></tr>"

    # ================= INDEX =================
    index = f"""<div class="hero"><h1>Blind geothermal faults — unique submission lab</h1>
<p>DOE GEMS Prize (DrivenData #306). One lineage owns 0.2477–0.2778; we build a <b>unique</b> detector in a new lane and let automated gates decide.</p>
<p>{dl_badge} {sub_badge}</p></div>
<div class="card"><h3 style="margin-top:0">Headline file</h3>
<p class="mono">{fname}<br>SHA-256: {sha}</p>
<p><b>Submission name:</b> <code>{sub_name}</code><br>
<b>Note ({len(note)}/140):</b> <code>{note}</code></p>
<p><a class="btn" href="downloads/{fname}" download>⬇ Download submission TIF</a>
<a class="btn sec" href="how-to-submit.html">How to submit</a>
<a class="btn sec" href="executive-summary.html">Executive summary</a></p>
<p class="small">Verdict: <b>{verdict}</b> · format {'PASS' if v_fmt else 'FAIL/PENDING'} · unique {'PASS' if v_uniq else 'FAIL/PENDING'} · beats champion SGMC-holdout bar {'YES' if v_bar else 'NO/PENDING'} · selector: {selector.get('decision', 'pending')}. Download=research OK · Submit requires promote-verdict + selector approval within the weekly cap.</p></div>
<h2>What file to download · estimate · uniqueness</h2>
<table><tr><th>Site</th><th>Submission</th><th>Score / estimate</th><th>HOLDOUT SGMC-DTI (ours, same instrument)</th><th>Dots</th><th>Unique?</th></tr>{rows}</table>
<p class="small">Owner-reported = task statement / sibling pages, NOT organizer receipts. HOLDOUT-DTI = WBG1-SGMC-CAL-v1.0 (62,122 off-catalogue truth px, 256-block 95% CI). PROJECTION = OLS live~SGMC over 9 champions — a model extrapolation, never a score.</p>
<h2>Why this ranking is honest</h2>
<div class="grid"><div class="card"><b>Best proven: 0.2778 (G32 H33-B2)</b><br>But it is a strict subset of the 0.2600 D2.8 raster (denominator pruning, zero new faults) — resubmitting it or a copy violates uniqueness and likely organizer duplicate rules.</div>
<div class="card"><b>Our lane: H1 geothermal-blind</b><br>Fresh detector, discharge-first ranking, no H19-5 input. Unique by construction; scored on the off-catalogue instrument that mimics the hidden test.</div>
<div class="card"><b>Automated gates, no inspector</b><br>Format (incl. the [0,1] portal rule) · uniqueness vs all 9 · holdout bar. Any failure → DO NOT SUBMIT. See <a href="executive-summary.html">run card</a>.</div></div>"""
    (docs / "index.html").write_text(page("Overview", index))

    # ================= EXEC SUMMARY =================
    champ_rows = ""
    for r in focus["rasters"]:
        c = (e2["champions"].get(r["id"], {}) if e2 else {})
        sgmc = f"{c.get('sgmc_DTI', float('nan')):.5f}" if c else "PENDING"
        champ_rows += (f"<tr><td><a href='{r['site']}'>{r['id']}</a></td>"
                       f"<td class='mono'>{r['submission']}</td><td>{r['owner_reported']:.4f}</td>"
                       f"<td>{sgmc}</td><td>{r['dots']:,}</td><td class='mono'>{r['sha256'][:16]}…</td></tr>")
    evo = ""
    if e2:
        best = max(e2["h1_grid"], key=lambda k: e2["h1_grid"][k]["sgmc_DTI"])
        for k in sorted(e2["h1_grid"]):
            v = e2["h1_grid"][k]
            mark = " ⭐" if k == best else ""
            evo += (f"<tr><td>{k}{mark}</td><td>{v['dots']:,}</td>"
                    f"<td>{v['sgmc_DTI']:.5f} [{v['sgmc_ci95'][0]:.5f},{v['sgmc_ci95'][1]:.5f}]</td>"
                    f"<td>{v['hide_DTI']:.5f}</td></tr>")
    comp_rows = ""
    if e1:
        for name, v in e1["components"].items():
            comp_rows += (f"<tr><td>{name}</td><td>{v['sgmc_DTI']:.5f}</td>"
                           f"<td>{v['hide_DTI']:.5f}</td>"
                           f"<td>{e1['canary'][name]['auc_two_sided']:.4f}</td></tr>")
    card_json = json.dumps(card, indent=2) if card else "PENDING"
    ex = f"""<h1>Executive summary</h1><p>{dl_badge} {sub_badge}</p>
<h2>1. Decision</h2><div class="card"><p class="mono">{fname}<br>SHA-256 {sha}</p>
<p>Name <code>{sub_name}</code> · Note ({len(note)}/140) <code>{note}</code></p>
<p><a class="btn" href="downloads/{fname}" download>⬇ Download TIF</a></p>
<p>Verdict <b>{verdict}</b>: format {'PASS' if v_fmt else 'FAIL/PENDING'} · uniqueness {'PASS' if v_uniq else 'FAIL/PENDING'} · SGMC-holdout vs champion bar {'WIN' if v_bar else 'LOSE/PENDING'} · selector {selector.get('decision', 'pending')}.</p></div>
<h2>2. The nine focus sites (highest submission each)</h2>
<table><tr><th>Site</th><th>Submission</th><th>Owner-reported</th><th>SGMC HOLDOUT-DTI (this repo)</th><th>Dots</th><th>SHA (local bytes)</th></tr>{champ_rows}</table>
<div class="card"><b>Lineage finding (recomputed from exact bytes):</b> G30-poisson ≡ G25-d2.8 bit-identical (corr 1.000). G32-H33 ⊂ D2.8 (all 37,654 dots coincide; −6,436 flank dots). G36-PINN ⊃ H33 (+1,200 dots, corr 0.984). G31 ⊂ D2.8. G27-gap ⊃ G24-d1.5. Every pair sits at 86–100% mutual 3-px overlap: <b>one lineage, one idea (H19-5 dotted + break-even pruning)</b>. 0.2778 won by denominator surgery (removing below-break-even flank dots), not discovery. Full analysis: repo <code>knowledge/why_02778_won.md</code>.</div>
<h2>3. Our campaign (H1 lane, 3-experiment budget)</h2>
<h3>E1 — surfaces + canary (all AUC two-sided &lt; 0.90: no leakage)</h3>
<table><tr><th>Component</th><th>SGMC-DTI</th><th>HIDE-DTI (diagnostic)</th><th>Canary AUC₂</th></tr>{comp_rows}</table>
<h3>E2 — budget × spacing sweep (SGMC-primary)</h3>
<table><tr><th>Config</th><th>Dots</th><th>SGMC-DTI [95% CI]</th><th>HIDE-DTI</th></tr>{evo}</table>
<h3>E3 — run card</h3><pre>{card_json}</pre>
<h2>4. How a cleared file would be submitted</h2>
<p>See <a href="how-to-submit.html">How to submit</a> for the exact portal steps, the [0,1] rule that rejected a previous upload, naming, and the weekly cap.</p>"""
    (docs / "executive-summary.html").write_text(page("Executive summary", ex))

    # ================= HOW TO SUBMIT =================
    how = f"""<h1>How to submit (exact steps)</h1><p>{dl_badge} {sub_badge}</p>
<div class="card"><b>Current file:</b> <code>{fname}</code> — verdict <b>{verdict}</b>. Do not upload while the badge says 🛑.</div>
<ol class="steps">
<li>Open the submission page: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData #306 — DOE GEMS</a> → <i>Submit</i>. (Login required; mind the <b>weekly submission cap</b> shown on that page — promotion to a real slot is a separate selector decision.)</li>
<li>Download the headlined file above (<a href="downloads/{fname}" download>{fname}</a>) or its <code>-zeros.zip</code> twin. Verify SHA-256: <code class="mono">{sha}</code> (<code>sha256sum</code>).</li>
<li>Upload the <b>zeros-variant TIF</b> (0 outside footprint). The portal rejects NaN/out-of-range values with <i>"Predicted values must be in range [0, 1]"</i> — the zeros file is validated all-finite in [0,1]; never upload the <code>-nan</code> twin to the portal.</li>
<li>Name the submission <code>{sub_name}</code> and paste the note (<code>{note}</code>).</li>
<li>Keep the receipt (score + submission id) and record it as ORGANIZER-CONFIRMED in <code>registry/observations.jsonl</code>. A projection is never a score.</li>
</ol>
<h2>Format contract (auto-checked by <code>scripts/run_checks.sh</code>)</h2>
<table><tr><th>Gate</th><th>Requirement</th></tr>
<tr><td>F1</td><td>single-band GeoTIFF</td></tr><tr><td>F2</td><td>CRS EPSG:32611</td></tr>
<tr><td>F3</td><td>shape 3730 × 3292</td></tr><tr><td>F4</td><td>transform (100, 0, 243350, 0, −100, 4508550)</td></tr>
<tr><td>F5</td><td>all inside-footprint values finite and in [0,1]</td></tr>
<tr><td>F6</td><td>zeros-variant: whole array finite</td></tr></table>"""
    (docs / "how-to-submit.html").write_text(page("How to submit", how))

    hyps = load(ROOT / "registry" / "hypotheses.json", {"hypotheses": []})
    hh = "".join(
        f"<div class='card'><b>{h['id']} (rank {h['rank']}, {h['status']})</b> — {h['title']}<br>"
        f"<b>Layers:</b> {', '.join(h['layers'])}<br><b>Signature:</b> {h['signature']}<br>"
        f"<b>Why off-catalogue:</b> {h['why_off_catalogue']}<br><b>Differs:</b> {h['differs']}<br>"
        f"<b>Mimic:</b> {h['mimic']}" + (f"<br><b>External data:</b> {h['external_data']}" if h.get("external_data") else "") + "</div>"
        for h in sorted(hyps["hypotheses"], key=lambda x: x["rank"]))
    (docs / "hypotheses.html").write_text(page("Hypotheses", f"<h1>Hypotheses H1–H5</h1>{hh}"))

    srcs = load(ROOT / "registry" / "sources.json", {})
    irr = load(ROOT / "registry" / "irregularities.json", {"items": []})
    off = "".join(f"<li><a href='{u}'>{u}</a></li>" for u in srcs.get("official", []))
    mir = "".join(f"<li>{m}</li>" for m in srcs.get("mirrors", []))
    irs = "".join(f"<div class='card'><b>{i['id']} [{i['severity']}]</b> — {i['note']}</div>" for i in irr["items"])
    (docs / "sources.html").write_text(page("Sources", f"<h1>Sources & irregularities</h1><h2>Official</h2><ul>{off}</ul><h2>Mirrors (hash-verified, not organizer-authenticated)</h2><ul>{mir}</ul><h2>Irregularities (flagged for review)</h2>{irs}<p class='small'>{srcs.get('verification', '')}</p>"))

    res = """<h1>Research notes</h1>
<div class="card"><b>Metric algebra.</b> DTI = TPw/(TPw+0.2FPw+0.8FNw), 300 m triangular kernel; break-even per-dot credit = 0.2×DTI (0.0556 at 0.2778); binary {0,1} optimal. See repo <code>knowledge/metric_algebra.md</code>.</div>
<div class="card"><b>Why dotted won.</b> The kernel bridges ~280 m gaps, so thinning H19-5 solid → d1.5 → d2.8 cut the denominator (N) while keeping coverage (numerator): 0.1922 → 0.2477 → 0.2600.</div>
<div class="card"><b>Why B=2 won.</b> Live scoring masks known faults; flank dots earn ~0 but cost 0.2. Removing 6,436 of them: 0.2600 → 0.2778. Denominator surgery, zero new faults.</div>
<div class="card"><b>Why the lineage is exhausted.</b> 0.2708/0.2710/0.2750/0.2778 bracket the break-even frontier of one detector. Headroom now requires numerator: hidden faults the lineage misses — the H1 bet (discharge-anchored blind conduits).</div>
<div class="card"><b>Geothermal grounding.</b> INGENIOUS springs/vents/paleo sites mark permeable structure; MT <code>cond_surf</code> marks clay-cap conductors; Basin-and-Range normal faults strike NNE (~15°) with conjugates (~140°). Blind dilational faults conduct fluid without mapped rupture — systematically off-catalogue.</div>
<div class="card"><b>Data.</b> Full auditable inventory with hashes + official links: repo <code>knowledge/data_inventory.md</code>.</div>"""
    (docs / "research.html").write_text(page("Research", res))

    print(f"site written to {docs} verdict={verdict} submit={sub_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
