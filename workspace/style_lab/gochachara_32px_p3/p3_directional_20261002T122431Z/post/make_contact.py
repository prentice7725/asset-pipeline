from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

run = Path(r"C:\workspace\asset-pipeline\workspace\style_lab\gochachara_32px_p3\p3_directional_20261002T122431Z")
post = run / "post"
methods = [
    ("P1_NN_THEN_MEDIANCUT_16", "NN>16"),
    ("P1_NN_THEN_MEDIANCUT_32", "NN>32"),
    ("P1_MEDIANCUT_16_THEN_NN", "16>NN"),
    ("P1_MEDIANCUT_32_THEN_NN", "32>NN"),
    ("P2_OE_CONTRAST_0", "OE0"),
    ("P3_OE_CONTRAST_2", "OE2"),
]
gens = [
    ("G01", "ARCHER standard"),
    ("G02", "ARCHER Pixelate"),
    ("G03", "ORC standard"),
    ("G04", "ORC Pixelate"),
]
views = ["south_front", "west_profile", "north_back"]
font = ImageFont.load_default()

def build(scale, mode, name):
    tile = 32 * scale
    x0, y0, label_w, header = 8, 8, 190, 48
    gap, label_h = 6, 20
    sheet = Image.new("RGB", (x0 + label_w + len(methods)*(tile+gap) + 8, y0+header+12*(tile+label_h+gap)+8), (230,230,230))
    draw = ImageDraw.Draw(sheet)
    for ci, (_, label) in enumerate(methods):
        draw.text((x0+label_w+ci*(tile+gap), y0), label, fill=(0,0,0), font=font)
    for gi, (gid, glabel) in enumerate(gens):
        for vi, view in enumerate(views):
            row = gi*3+vi
            y = y0+header+row*(tile+label_h+gap)
            direction = ("S/front", "W/side", "N/back")[vi]
            draw.text((x0,y+max(0,(tile-16)//2)),glabel+"\n"+direction,fill=(0,0,0),font=font)
            for ci,(method,_) in enumerate(methods):
                x=x0+label_w+ci*(tile+gap)
                suffix="32px_binary_alpha.png" if mode=="rgba" else "32px_opaque_white.png"
                p=post/gid/view/method/suffix
                if p.exists():
                    im=Image.open(p)
                    if mode=="rgba":
                        bg=Image.new("RGB",(32,32),(230,230,230))
                        dd=ImageDraw.Draw(bg)
                        for yy in range(0,32,4):
                            for xx in range(0,32,4):
                                if ((xx//4)+(yy//4))%2: dd.rectangle((xx,yy,xx+3,yy+3),fill=(190,190,190))
                        bg.paste(im.convert("RGBA"),(0,0),im.convert("RGBA").getchannel("A"))
                        im=bg
                    else:
                        im=im.convert("RGB")
                    if scale>1: im=im.resize((tile,tile),Image.Resampling.NEAREST)
                    sheet.paste(im,(x,y))
                    draw.rectangle((x,y,x+tile-1,y+tile-1),outline=(30,30,30))
                else:
                    draw.rectangle((x,y,x+tile-1,y+tile-1),fill=(205,205,205),outline=(90,90,90))
                    draw.text((x+2,y+tile//2-4),"N/A",fill=(65,35,35),font=font)
    sheet.save(post/name)

build(1,"opaque","gallery_native1x_opaque.png")
build(1,"rgba","gallery_native1x_rgba_checker.png")
build(4,"opaque","gallery_nearest4x_opaque.png")
build(4,"rgba","gallery_nearest4x_rgba_checker.png")
print("contact sheets created")


