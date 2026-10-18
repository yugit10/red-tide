# -*- coding: utf-8 -*-
# 组装海面/非海面二分类数据集: 正=3065宏观海面(已有组织好的JPEG), 负=网页nonsea + 合成, 全部重编码224px JPEG
import os, shutil, random, hashlib
from PIL import Image

random.seed(3)

SRC_POS = r'D:\train\_macro_dataset'          # train/{class}/ + monitor/{class}/ (3065)
SRC_NEG_WEB = r'D:\train\_macro_scratch\nonsea'
SRC_NEG_SYN = r'D:\train\_macro_scratch\nonsea_syn'
OUT = r'D:\train\_macro_dataset\precheck'
SIZE = 224

os.makedirs(os.path.join(OUT, 'train', 'sea'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'train', 'nonsea'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'val', 'sea'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'val', 'nonsea'), exist_ok=True)

def reencode(src, dst, size=SIZE):
    im = Image.open(src).convert('RGB')
    im = im.resize((size, size), Image.BILINEAR)
    im.save(dst, 'JPEG', quality=90)
    return dst

def collect_pos():
    out = []
    for split in ['train', 'monitor']:
        base = os.path.join(SRC_POS, split)
        for cls in os.listdir(base):
            cdir = os.path.join(base, cls)
            if os.path.isdir(cdir):
                out += [os.path.join(cdir, f) for f in os.listdir(cdir) if f.lower().endswith('.jpg')]
    return out

def collect_neg():
    out = []
    if os.path.isdir(SRC_NEG_WEB):
        out += [os.path.join(SRC_NEG_WEB, f) for f in os.listdir(SRC_NEG_WEB) if f.lower().endswith('.jpg')]
    if os.path.isdir(SRC_NEG_SYN):
        out += [os.path.join(SRC_NEG_SYN, f) for f in os.listdir(SRC_NEG_SYN) if f.lower().endswith('.jpg')]
    return out

pos = collect_pos()
neg = collect_neg()
print('正样本(海面):', len(pos), ' 负样本(非海面):', len(neg))
random.shuffle(pos); random.shuffle(neg)

n_pos_val = max(1, int(len(pos) * 0.15))
n_neg_val = max(1, int(len(neg) * 0.15))
pos_val, pos_tr = pos[:n_pos_val], pos[n_pos_val:]
neg_val, neg_tr = neg[:n_neg_val], neg[n_neg_val:]

count = {'train_sea': 0, 'train_nonsea': 0, 'val_sea': 0, 'val_nonsea': 0}
for i, p in enumerate(pos_tr):
    reencode(p, os.path.join(OUT, 'train', 'sea', f'sea_{i:05d}.jpg')); count['train_sea'] += 1
for i, p in enumerate(neg_tr):
    reencode(p, os.path.join(OUT, 'train', 'nonsea', f'n_{i:05d}.jpg')); count['train_nonsea'] += 1
for i, p in enumerate(pos_val):
    reencode(p, os.path.join(OUT, 'val', 'sea', f'sea_{i:05d}.jpg')); count['val_sea'] += 1
for i, p in enumerate(neg_val):
    reencode(p, os.path.join(OUT, 'val', 'nonsea', f'n_{i:05d}.jpg')); count['val_nonsea'] += 1

print('组装完成:', count)
print('总计 train:', count['train_sea'] + count['train_nonsea'], ' val:', count['val_sea'] + count['val_nonsea'])
