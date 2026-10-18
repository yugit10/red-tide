# -*- coding: utf-8 -*-
# 整理宏观伪标签数据集: 扁平 jpg -> {class}/ 目录 + class_map.json
# 统一重编码为真 JPEG(PIL), 避免 WebP/PNG 伪装成 .jpg 导致 MindSpore Decode 失败
import os, csv, json, shutil, random, collections, sys, io
from PIL import Image

WEB = r'D:\train\_macro_scratch\web'
DST = r'D:\train\_macro_dataset'
os.makedirs(DST, exist_ok=True)

WEB = r'D:\train\_macro_scratch\web'
DST = r'D:\train\_macro_dataset'
os.makedirs(DST, exist_ok=True)

rows = []
for csvf in ['provenance.csv', 'provenance_v2.csv', 'provenance_v3.csv', 'provenance_v4.csv']:
    p = os.path.join(WEB, csvf)
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                rows.append(r)
print('溯源总行数:', len(rows))

byfile = {r['file']: r for r in rows}
classes = sorted({r['hyp'] for r in rows})
cnt_class = collections.Counter(r['hyp'] for r in rows)
print('类别:', classes)
print('各类原始行数:', dict(cnt_class))

# 平衡: 每类最多 BAL(900; 保持自然分布, 轻微不均衡符合真实先验)
BAL = 900
per_class = {}
for c in classes:
    files = [r['file'] for r in rows if r['hyp'] == c]
    random.seed(42); random.shuffle(files)
    per_class[c] = files[:BAL]
print('平衡后:', {c: len(v) for c, v in per_class.items()})

for split in ['train', 'monitor']:
    for c in classes:
        os.makedirs(os.path.join(DST, split, c), exist_ok=True)

missing = 0
for c, files in per_class.items():
    n = len(files)
    n_mon = max(1, int(n * 0.1))
    for i, fn in enumerate(files):
        src = os.path.join(WEB, fn)
        if not os.path.exists(src):
            missing += 1
            continue
        split = 'monitor' if i < n_mon else 'train'
        try:
            im = Image.open(src)
            im = im.convert('RGB')
            # 输出文件名统一 jpg (重编码; 转不了就跳过)
            im.save(os.path.join(DST, split, c, fn), 'JPEG', quality=92)
        except Exception:
            missing += 1
print('重编码/缺文件:', missing)

c_train, c_mon = {}, {}
for c in classes:
    c_train[c] = len(os.listdir(os.path.join(DST, 'train', c)))
    c_mon[c] = len(os.listdir(os.path.join(DST, 'monitor', c)))
print('train:', c_train)
print('monitor:', c_mon)

class_map = {
    "classes": classes,
    "HYP_CN": {"diatom": "硅藻型水华", "green_tide": "绿潮/绿藻水华", "noctiluca": "夜光藻型水华",
               "none": "无明显赤潮", "toxic_dino": "有毒甲藻型"},
    "note": "宏观5类训练集: 搜索引擎公开图经规则流水色CV伪标签(透明披露)。monitor=同源伪标签仅监控训练; 准确率验证以人工精选真实图(warm/normal/green)为口径。",
    "summary": {c: {"train": c_train[c], "monitor": c_mon[c]} for c in classes},
}
with open(os.path.join(DST, 'class_map.json'), 'w', encoding='utf-8') as f:
    json.dump(class_map, f, ensure_ascii=False, indent=2)
print('saved', os.path.join(DST, 'class_map.json'))
