# -*- coding: utf-8 -*-
# 降采样宏观数据集到 256px/q85 作为提交样例(压缩体积, 保结构+溯源)
import os, shutil, glob
from PIL import Image

SRC = r'D:\train\_macro_dataset'
DST = r'D:\train\_submission_assets\macro_dataset_demo'
MAX = 256
SQ = 85

if os.path.exists(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

tot = 0; fail = 0
for split in ['train', 'monitor']:
    splt_dir = os.path.join(SRC, split)
    if not os.path.isdir(splt_dir):
        continue
    for cls in sorted(os.listdir(splt_dir)):
        src_c = os.path.join(splt_dir, cls)
        if not os.path.isdir(src_c):
            continue
        dst_c = os.path.join(DST, split, cls)
        os.makedirs(dst_c, exist_ok=True)
        for fn in os.listdir(src_c):
            sp = os.path.join(src_c, fn)
            try:
                im = Image.open(sp).convert('RGB')
                im.thumbnail((MAX, MAX), Image.LANCZOS)
                im.save(os.path.join(dst_c, fn), 'JPEG', quality=SQ, optimize=True)
                tot += 1
            except Exception as e:
                fail += 1
print('OK %d, fail %d' % (tot, fail))
