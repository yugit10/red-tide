# -*- coding: utf-8 -*-
# 验证 fusion.sea_precheck 规则流兜底: 真海面(应放行) vs 非海面(应拒绝)
import sys, os, glob
sys.path.insert(0, r"D:\train\tools")
from PIL import Image
import fusion

def scan(label, paths, expect_sea):
    ok = 0; n = 0; bad = []
    for p in paths:
        try:
            is_sea, src, score, detail = fusion.sea_precheck(Image.open(p))
        except Exception as e:
            continue
        n += 1
        good = (is_sea == expect_sea)
        ok += good
        if not good:
            bad.append((os.path.basename(p)[:36], src, score, detail))
    print(f"{label}: {ok}/{n} 符合预期  ({'放行' if expect_sea else '拒绝'})")
    for b in bad[:6]:
        print("   误判:", b)

# 真海面(正样本, 应放行)
pos = glob.glob(r"D:\train\dataset_raw\macro\raw\*\keep\*.jpg")[:20]
scan("真海面(20张)", pos, True)

# 非海面: 合成(应拒绝)
syn = glob.glob(r"D:\train\_macro_scratch\nonsea_syn\*.jpg")[:20]
scan("合成非海面(20张)", syn, False)

# 非海面: 网页负样本抽样(应拒绝)
neg = sorted(glob.glob(r"D:\train\_macro_scratch\nonsea\*.jpg"))[:20]
scan("网页非海面(20张)", neg, False)
