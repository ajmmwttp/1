"""別ウィンドウ案 F / H の PNG を、スマホで見やすい1つの PDF にまとめる"""
from PIL import Image

from turnline_common import OUT

PAGES = ["TurnLine_subpane_hist.png", "TurnLine_subpane_area.png"]

if __name__ == "__main__":
    imgs = [Image.open(OUT / p).convert("RGB") for p in PAGES]
    imgs[0].save(OUT / "TurnLine_subpane_FH.pdf", save_all=True, append_images=imgs[1:], resolution=200,
                 creationDate=None, modDate=None)
    print("saved:", OUT / "TurnLine_subpane_FH.pdf")
