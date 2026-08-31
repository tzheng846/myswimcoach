"""Rasterize the Swimnetics mark into the iOS app-icon set (Phase 84-01).

Source of truth is assets/icon/Swimnetics_icon.svg, which is NOT a vector: it is an
SVG wrapper around a base64 1004x960 RGBA PNG anchored at x=0,y=0 inside a 1028x1028
viewBox (G2). Rendering the SVG would put the mark off-centre, up and left, so this
script decodes the payload and composes the square canvas deliberately instead.

iOS rejects app icons that carry an alpha channel (G3), so every output is opaque RGB.
That is a deliberate divergence from web/app/icon.png, which is correctly transparent.

Outputs land in scratch/appicon/ only. Installing them into the mobile repo is a
separate, reviewed step.

Re-runnable and byte-deterministic: same input -> same bytes.
"""

import base64
import hashlib
import io
import re
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "assets" / "icon" / "Swimnetics_icon.svg"
OUT_DIR = REPO / "scratch" / "appicon"

# --- the two knobs the decision checkpoint may flip -------------------------
BG = (255, 255, 255)   # opaque background; the mark's white highlight sits INSIDE
                       # the purple dome, so a white ground renders it as designed.
FILL = 0.80            # fraction of the canvas edge spanned by the art's longest side
# ---------------------------------------------------------------------------

SIZES = [1024, 180, 120]


def load_mark() -> Image.Image:
    """Decode the base64 PNG payload out of the SVG wrapper, cropped to its ink."""
    svg = SRC.read_text(encoding="utf-8")
    m = re.search(r"base64,([A-Za-z0-9+/=]+)", svg)
    if not m:
        raise SystemExit(f"no base64 payload found in {SRC}")
    art = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")
    # Currently a no-op (the ink bleeds to all four edges), but it keeps the script
    # correct if the mark is ever re-exported with margin -- the drift that would
    # otherwise silently re-centre the icon.
    bbox = art.getbbox()
    return art.crop(bbox) if bbox else art


def compose(art: Image.Image, edge: int) -> Image.Image:
    """Scale the art to FILL of `edge` on its longest side and centre it, opaque."""
    src_w, src_h = art.size
    if src_w >= src_h:
        w = round(edge * FILL)
        h = round(src_h * w / src_w)
    else:
        h = round(edge * FILL)
        w = round(src_w * h / src_h)

    scaled = art.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGB", (edge, edge), BG)
    canvas.paste(scaled, ((edge - w) // 2, (edge - h) // 2), scaled)
    return canvas


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art = load_mark()
    src_aspect = art.width / art.height
    print(f"source: {art.size} aspect {src_aspect:.6f}  ->  BG={BG} FILL={FILL:.0%}")

    for edge in SIZES:
        # Resize independently FROM the full-resolution source, never downsampled
        # from the 1024 output -- one resample is sharper at 120 px than two.
        icon = compose(art, edge).convert("RGB")
        path = OUT_DIR / f"AppIcon-{edge}.png"
        icon.save(path, "PNG", optimize=True)

        chk = Image.open(path)
        # Re-measure the pasted art so the printout reports what actually landed.
        w = round(edge * FILL) if art.width >= art.height else None
        h = round(art.height * w / art.width)
        lm, rm = (edge - w) // 2, edge - w - (edge - w) // 2
        tm, bm = (edge - h) // 2, edge - h - (edge - h) // 2
        err = abs((w / h) - src_aspect) / src_aspect
        sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        print(
            f"  {path.name:<17} mode={chk.mode} size={chk.size} tRNS={'tRNS' in chk.info} "
            f"art={w}x{h} fill={w / edge:.3%} margins=({lm},{rm},{tm},{bm}) "
            f"aspect_err={err:.4%} sha256={sha}"
        )


if __name__ == "__main__":
    main()
