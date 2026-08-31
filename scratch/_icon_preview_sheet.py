"""Throwaway: contact sheet for the 84-01 decision checkpoint (bg x fill)."""
import importlib.util, sys
from PIL import Image, ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location("mk", "scratch/make_app_icons.py")
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)

art = mk.load_mark()
BGS  = [("#FFFFFF", (255,255,255)), ("#F4EDFF", (244,237,255)), ("#E4D3FF", (228,211,255))]
FILLS = [0.72, 0.80, 0.88]

def tile(bg, fill, edge):
    mk.BG, mk.FILL = bg, fill
    im = mk.compose(art, edge).convert("RGB")
    mask = Image.new("L", (edge*4, edge*4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,edge*4-1,edge*4-1], radius=int(edge*4*0.2237), fill=255)
    im.putalpha(mask.resize((edge, edge), Image.LANCZOS))
    return im

font  = ImageFont.load_default(size=15)
small = ImageFont.load_default(size=12)
BIG, SM, PAD, GAP = 240, 120, 30, 26
cw = BIG + GAP + SM
sheet = Image.new("RGB", (PAD*2 + cw*3 + GAP*2, 74 + (BIG + 46)*3 + PAD), (176,176,186))
d = ImageDraw.Draw(sheet)
d.text((PAD, 18), "Swimnetics app icon — background x fill.  Large tile = 240px (detail);  small tile = 120px ACTUAL home-screen size.",
       font=font, fill=(20,20,24))
d.text((PAD, 42), "Judge the SMALL one hardest — that is roughly where the tentacles thin out first.", font=small, fill=(50,50,58))

for r,(hexname,bg) in enumerate(BGS):
    for c,fill in enumerate(FILLS):
        x, y = PAD + c*(cw+GAP), 74 + r*(BIG+46)
        sheet.paste(tile(bg,fill,BIG), (x,y), tile(bg,fill,BIG))
        sheet.paste(tile(bg,fill,SM), (x+BIG+GAP, y+BIG-SM), tile(bg,fill,SM))
        star = "   <-- current default" if (r==0 and c==1) else ""
        d.text((x, y+BIG+8), f"bg {hexname}   fill {fill:.0%}{star}", font=small, fill=(20,20,24))

sheet.save("scratch/appicon/_preview_sheet.png")
print("wrote scratch/appicon/_preview_sheet.png", sheet.size)
