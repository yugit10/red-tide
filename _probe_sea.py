# -*- coding: utf-8 -*-
"""探针: 统计三组图的 水色占比/颜色多样性/饱和度, 为 sea_precheck 定阈值."""
import os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, r"D:\train\tools")

def signals(img):
    """返回 (f_water, f_blue, colorfulness, n_colors, mean_s)."""
    img = img.convert("RGB")
    w, h = img.size
    crop = img.crop((0, int(h * 0.20), w, h))
    arr = np.asarray(crop).astype(np.float32) / 255.0
    tot = arr.shape[0] * arr.shape[1]
    mx = arr.max(2); mn = arr.min(2); df = mx - mn + 1e-8
    s = np.where(mx > 0, df / (mx + 1e-8), 0)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    m = (mx == r); hue[m] = ((g - b)[m] / df[m]) % 6
    m = (mx == g) & (mx != r); hue[m] = ((b - r)[m] / df[m]) + 2
    m = (mx == b) & (mx != r) & (mx != g); hue[m] = ((r - g)[m] / df[m]) + 4
    hue = hue * 60.0
    # 水色系: 蓝(180-270)/青(150-200 部分)/绿(50-170)/粉(330-360,0-20)/褐(20-50)
    water_m = (((hue >= 180) & (hue <= 270)) |   # 蓝
               ((hue >= 50) & (hue < 180)) |      # 绿+青
               ((hue >= 330) | (hue < 20)) |      # 粉红
               ((hue >= 20) & (hue < 50)))        # 褐
    s_water = water_m & (s > 0.10) & (mx > 0.10)
    f_water = float(s_water.sum()) / tot
    blue_m = (hue >= 180) & (hue <= 270) & (s > 0.08) & (mx > 0.10)
    f_blue = float(blue_m.sum()) / tot
    mean_s = float(s.mean())
    # 颜色多样性: 量化到 3bit/通道 统计不同颜色数 (下采样到 48x48)
    sm = np.asarray(img.resize((48, 48))).astype(np.uint8)
    q = (sm >> 5)  # 3bit
    n_colors = len(np.unique(q.reshape(-1, 3), axis=0))
    # colorfulness (Hasler & Susstrunk)
    R, G, B = sm[..., 0].astype(float), sm[..., 1].astype(float), sm[..., 2].astype(float)
    rg = R - G; yb = 0.5 * (R + G) - B
    colorfulness = float(np.sqrt(rg.std()**2 + yb.std()**2) + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2))
    return round(f_water, 3), round(f_blue, 3), round(colorfulness, 1), n_colors, round(mean_s, 3)

def scan(label, paths):
    print(f"\n== {label} ==")
    for p in paths:
        try:
            im = Image.open(p)
            fw, fb, cf, nc, ms = signals(im)
            print(f"  {os.path.basename(p)[:38]:<40} f_water={fw:<6} f_blue={fb:<6} color={cf:<7} ncol={nc:<3} sat={ms}")
        except Exception as e:
            print(f"  {os.path.basename(p)[:38]} 读取失败: {e}")

# 1) 真海面(暖色水华)
warm = [os.path.join(r"D:\train\dataset_raw\macro\raw\warm\keep", f) for f in os.listdir(r"D:\train\dataset_raw\macro\raw\warm\keep")][:6]
# 2) 真海面(正常蓝色/绿色)
norm = [os.path.join(r"D:\train\dataset_raw\macro\raw\normal\keep", f) for f in os.listdir(r"D:\train\dataset_raw\macro\raw\normal\keep")][:4]
green = [os.path.join(r"D:\train\dataset_raw\macro\raw\green\keep", f) for f in os.listdir(r"D:\train\dataset_raw\macro\raw\green\keep")][:4]
# 3) 无关: 纯色/渐变/文档样图(合成)
synth = []
def make(fn, f):
    p = os.path.join(r"D:\train\_macro_scratch", fn); f(Image.new("RGB", (400, 300))).save(p); synth.append(p)
make("syn_red.jpg", lambda im: (im.paste((200, 30, 30), (0, 0, 400, 300)), im)[1])
make("syn_green.jpg", lambda im: (im.paste((30, 180, 40), (0, 0, 400, 300)), im)[1])
make("syn_gray.jpg", lambda im: (im.paste((128, 128, 128), (0, 0, 400, 300)), im)[1])
make("syn_white.jpg", lambda im: (im.paste((245, 245, 245), (0, 0, 400, 300)), im)[1])

scan("真海面·暖色水华", warm)
scan("真海面·正常蓝", norm)
scan("真海面·绿潮", green)
scan("无关·合成色块(红/绿/灰/白)", synth)
