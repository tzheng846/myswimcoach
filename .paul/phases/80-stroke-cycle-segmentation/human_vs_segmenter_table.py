"""
Phase 80 — two-column HUMAN vs SEGMENTER stroke-label table, per session.

Left column  = human arm-entry marks (ground truth), in seconds.
Right column = segmenter labels = bias=0.0 wavelet-ridge stroke detector.

Rows are aligned by the same optimal matcher used for scoring
(segmenter_eval.match_series, tol=0.15 s):
    matched  -> human time | segmenter time (+delta ms)
    missed   -> human time | (blank)         (detector dropped it)
    extra    -> (blank)     | segmenter time  (detector over-counted)

All times are clamped to the human [stroke_start_s, finish_s] window (D5).

Writes a self-contained HTML page (path printed at the end).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np                     # noqa: E402
import visualize_freestyle_seg as vz   # noqa: E402
import segmenter_eval as se            # noqa: E402

TOL = vz.TOL
BIAS = 0.0
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "figs" / "human_vs_segmenter.html"


def rows_for(d):
    a, b = vz._win(d)
    lo, hi = a / d["fs"], b / d["fs"]
    marks = [mk for mk in d["marks"] if lo <= mk <= hi]
    if len(marks) < 4:
        return None
    det = sorted(vz.strokes_wavelet(d, BIAS))
    pairs, extra, missed = se.match_series(det, marks, TOL)
    # pairs: (pred, truth, abs_err) — build a unified, time-sorted row list
    rows = []
    for p, t, _ in pairs:
        rows.append(dict(kind="match", human=t, seg=p, key=t))
    for t in missed:
        rows.append(dict(kind="miss", human=t, seg=None, key=t))
    for p in extra:
        rows.append(dict(kind="extra", human=None, seg=p, key=p))
    rows.sort(key=lambda r: r["key"])
    cov = se.coverage(marks, lo, hi)["ratio"]
    true_rate = 60.0 / np.mean(np.diff(marks)) if len(marks) >= 2 else float("nan")
    det_rate = 60.0 / np.mean(np.diff(det)) if len(det) >= 2 else float("nan")
    return dict(
        rows=rows, marks=marks, det=det,
        true_n=len(marks), det_n=len(det), dcount=len(det) - len(marks),
        n_match=len(pairs), n_miss=len(missed), n_extra=len(extra),
        true_rate=true_rate, det_rate=det_rate,
        rate_err=100 * (det_rate - true_rate) / true_rate if np.isfinite(det_rate) else float("nan"),
        cov=cov, well=bool(cov and 0.7 <= cov <= 1.4),
    )


def card_html(d, r):
    dcol = {0: "var(--ok)", 1: "var(--warn)"}.get(abs(r["dcount"]), "var(--bad)")
    if not r["well"]:
        dcol = "var(--muted)"
    body = []
    for row in r["rows"]:
        if row["kind"] == "match":
            delta = (row["seg"] - row["human"]) * 1000.0
            body.append(
                f'<tr class="match"><td>{row["human"]:.2f}</td>'
                f'<td>{row["seg"]:.2f}<span class="d">{delta:+.0f} ms</span></td></tr>')
        elif row["kind"] == "miss":
            body.append(
                f'<tr class="miss"><td>{row["human"]:.2f}</td>'
                f'<td class="empty">— dropped</td></tr>')
        else:
            body.append(
                f'<tr class="extra"><td class="empty">— extra</td>'
                f'<td>{row["seg"]:.2f}</td></tr>')
    tag = "" if r["well"] else ' · <span class="muted">partial-label</span>'
    return f"""<section class="card">
  <h2>{d['swimmer']} <span class="when">{d['when'][5:16].replace('T',' ')}</span></h2>
  <div class="meta">
    human <b>{r['true_n']}</b> · seg <b style="color:{dcol}">{r['det_n']} ({r['dcount']:+d})</b>
    · matched {r['n_match']} · miss {r['n_miss']} · extra {r['n_extra']}<br>
    rate {r['true_rate']:.0f} → {r['det_rate']:.0f} spm ({r['rate_err']:+.0f}%){tag}
  </div>
  <table>
    <thead><tr><th>Human (s)</th><th>Segmenter (s)</th></tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</section>"""


def main():
    data = vz.load_freestyle()
    cards = []
    for d in sorted(data, key=lambda d: (d["swimmer"], d["when"])):
        if d["ss"] is None or d["fin"] is None:
            continue
        r = rows_for(d)
        if r:
            cards.append(card_html(d, r))
    html = TEMPLATE.replace("{{CARDS}}", "\n".join(cards)).replace("{{N}}", str(len(cards)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT)


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Human vs Segmenter</title>
<style>
:root{
  --bg:#ffffff; --fg:#1a1a1a; --muted:#8a8a8a; --line:#e6e6e6; --card:#fafafa;
  --ok:#1a8a3a; --warn:#c97a00; --bad:#c0202a;
  --miss-bg:#fdeaea; --extra-bg:#fff6e6;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#141414; --fg:#e8e8e8; --muted:#909090; --line:#2c2c2c; --card:#1c1c1c;
  --ok:#4cc46a; --warn:#e0a24a; --bad:#e5626c;
  --miss-bg:#331b1b; --extra-bg:#332a17;
}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);margin:0;padding:24px;
  font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:18px;margin:0 0 4px}
.lede{color:var(--muted);margin:0 0 20px;max-width:70ch}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.card{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:12px 14px}
.card h2{font-size:14px;margin:0 0 2px}
.when{color:var(--muted);font-weight:400}
.meta{color:var(--fg);font-size:12px;margin:0 0 8px;line-height:1.4}
.muted{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
th{text-align:right;color:var(--muted);font-weight:600;border-bottom:1px solid var(--line);
  padding:2px 6px}
td{text-align:right;padding:2px 6px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.d{color:var(--muted);font-size:10.5px;margin-left:6px}
.empty{color:var(--muted);font-style:italic}
tr.miss{background:var(--miss-bg)}
tr.extra{background:var(--extra-bg)}
.legend{margin:16px 0 0;color:var(--muted);font-size:12px}
.sw{display:inline-block;width:11px;height:11px;border-radius:2px;vertical-align:-1px;margin:0 4px 0 12px}
</style></head><body>
<h1>Human vs Segmenter stroke labels — {{N}} freestyle sessions</h1>
<p class="lede">Left = human arm-entry marks. Right = segmenter (bias=0.0 wavelet-ridge stroke detector).
Rows aligned by optimal matcher at 0.15 s tolerance, clamped to the human [stroke_start, finish] window.
A <b>dropped</b> row = a human stroke the detector missed; an <b>extra</b> row = a detection with no
human stroke within tolerance.</p>
<div class="grid">{{CARDS}}</div>
<p class="legend">
<span class="sw" style="background:var(--miss-bg)"></span>dropped (detector missed a human stroke)
<span class="sw" style="background:var(--extra-bg)"></span>extra (detector over-counted)
</p>
</body></html>"""


if __name__ == "__main__":
    main()
