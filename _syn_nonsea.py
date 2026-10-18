# -*- coding: utf-8 -*-
# 合成硬负样本: 纯色/渐变/噪点/文字/网格/条纹/图标风 —— 确保预检模型见过"不可能像海面"的图
import os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import hashlib

OUT = r'D:\train\_macro_scratch\nonsea_syn'
os.makedirs(OUT, exist_ok=True)
random.seed(7)
np.random.seed(7)

SIZE = (256, 256)
made = 0

def save(arr, kind):
    global made
    im = Image.fromarray(arr.astype(np.uint8), 'RGB')
    md5 = hashlib.md5(im.tobytes()).hexdigest()[:8]
    p = os.path.join(OUT, f'{kind}_{md5}.jpg')
    im.save(p, 'JPEG', quality=90)
    made += 1

# 1) 纯色 (含海面类似色做对抗: 纯蓝/纯绿也会被拒? 纯色块无纹理 -> 预检应拦)
for name, rgb in [('flat_red', (220, 40, 40)), ('flat_blue', (40, 90, 220)),
                  ('flat_green', (40, 180, 60)), ('flat_yellow', (230, 200, 30)),
                  ('flat_white', (248, 248, 248)), ('flat_black', (20, 20, 20)),
                  ('flat_brown', (140, 90, 40)), ('flat_pink', (230, 120, 160))]:
    arr = np.zeros((SIZE[1], SIZE[0], 3), dtype=np.uint8)
    arr[:, :, :] = rgb
    for _ in range(4):
        save(arr, name)

# 2) 渐变
for name in ['grad_sky', 'grad_warm', 'grad_green']:
    top, bot = {'grad_sky': ((30, 90, 220), (240, 250, 255)),
                'grad_warm': ((250, 160, 60), (255, 240, 220)),
                'grad_green': ((30, 90, 40), (180, 220, 140))}[name]
    for k in range(3):
        yy = np.linspace(0, 1, SIZE[1])[:, None, None]
        arr = np.array(top, dtype=np.float32) * (1 - yy) + np.array(bot, dtype=np.float32) * yy
        save(arr, name)

# 3) 高斯噪声 (彩色噪点)
for k in range(6):
    arr = np.random.randint(0, 256, (SIZE[1], SIZE[0], 3)).astype(np.uint8)
    save(arr, 'noise')

# 4) 文字文档 (白底黑字)
try:
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 22)
except Exception:
    font = ImageFont.load_default()
for k in range(5):
    im = Image.new('RGB', SIZE, (255, 255, 255))
    d = ImageDraw.Draw(im)
    for i in range(12):
        d.text((8 + (i % 3) * 30, 12 + i * 20), f'合同条款第{i+1}条 甲方乙方 xxx 2026', fill=(30, 30, 30), font=font)
    save(np.asarray(im), 'doc')

# 5) 网格/条纹/棋盘
for k in range(4):
    arr = np.zeros((SIZE[1], SIZE[0], 3), dtype=np.uint8)
    for y in range(0, SIZE[1], 32):
        for x in range(0, SIZE[0], 32):
            if (x // 32 + y // 32) % 2 == 0:
                arr[y:y+32, x:x+32] = (60, 60, 60)
            else:
                arr[y:y+32, x:x+32] = (230, 230, 230)
    save(arr, 'checker')

print('合成负样本完成:', made)
