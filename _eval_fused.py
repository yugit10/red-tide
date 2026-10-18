# -*- coding: utf-8 -*-
# 验证新融合链路: 规则流×CNN(纯图像) 在 25 张人工真实图上的三类口径准确率
import sys, os, io
sys.path.insert(0, r'D:\train\tools')
from PIL import Image
import fusion

REAL = {
    "warm": ["warm_gbnoct_noctiluca_0000.jpg", "warm_gbnoct_noctiluca_0014.jpg",
             "warm_gbnoct_noctiluca_0015.jpg", "warm_gbnoct_noctiluca_0032.jpg",
             "warm_gbnoct_noctiluca_0081.jpg", "warm_gbnoct_noctiluca_0082.jpg",
             "warm_gbnoct_noctiluca_0086.jpg", "warm_gbnoct_noctiluca_0110.jpg",
             "warm_gbnoct_noctiluca_0111.jpg", "warm_gbnoct_noctiluca_0112.jpg",
             "warm_gbnoct_noctiluca_0113.jpg", "warm_gbnoct_noctiluca_0114.jpg",
             "warm_gbnoct_noctiluca_0122.jpg", "warm_gbnoct_noctiluca_0131.jpg",
             "warm_algae_FujianCoast_FIELD_02.jpg", "warm_algae_FujianCoast_FIELD_14.jpg",
             "warm_algae_Xiamen_2007_FIELD_01.jpg", "warm_gbif01_039041df.jpg",
             "warm_gbif14_a635a9a3.jpg"],
    "normal": ["normal_algae_Quanzhou_2017_FIELD_01.jpg", "normal_gbnoct_noctiluca_0133.jpg",
               "normal_gbnoct_noctiluca_0134.jpg"],
    "green":  ["green_algae_FujianCoast_FIELD_05.jpg", "green_gbnoct_noctiluca_0098.jpg",
               "green_gbnoct_noctiluca_0099.jpg"],
}
KEEP_ROOT = r"D:\train\dataset_raw\macro\raw"
HYP_TO_COARSE = {"noctiluca": "warm", "toxic_dino": "warm", "diatom": "warm",
                 "green_tide": "green", "none": "normal"}
COARSE2CN = {"warm": "暖色水华", "green": "绿潮", "normal": "正常海水"}

path_by_name = {}
for folder in ["warm", "normal", "green"]:
    for keep_dir in ["keep", "drop_curated"]:
        base = os.path.join(KEEP_ROOT, folder, keep_dir)
        if os.path.isdir(base):
            for fn in os.listdir(base):
                path_by_name.setdefault(fn, os.path.join(base, fn))

items = []
for coarse, names in REAL.items():
    for fn in names:
        if fn in path_by_name:
            items.append((path_by_name[fn], coarse, fn))

rule_ok = fused_ok = cnn_ok = 0
detail = []
for p, coarse, fn in items:
    im = Image.open(p)
    lab, lik, meta = fusion.image_color_likelihood(im)
    rule_hyp = max(fusion.HYP, key=lambda h: (lik[h], -fusion.HYP.index(h)))
    rule_c = HYP_TO_COARSE[rule_hyp]
    ok_cnn, cnn_lik = fusion.image_cnn_likelihood(im)
    fused = fusion.fuse(lik, None, cnn_lik=cnn_lik)
    fused_c = HYP_TO_COARSE[fused["top"]]
    cnn_hyp = max(cnn_lik, key=lambda h: (cnn_lik[h], -fusion.HYP.index(h)))
    cnn_c = HYP_TO_COARSE[cnn_hyp]
    rule_ok += (rule_c == coarse); fused_ok += (fused_c == coarse); cnn_ok += (cnn_c == coarse)
    detail.append((fn, coarse, rule_c, fused_c, cnn_c, rule_c == coarse, fused_c == coarse, cnn_c == coarse))

n = len(items)
print("25 张人工真实图,3类口径:")
print(f"  规则流单独: {rule_ok}/{n} = {rule_ok/n*100:.1f}%")
print(f"  融合(规则×CNN): {fused_ok}/{n} = {fused_ok/n*100:.1f}%")
print(f"  CNN单独: {cnn_ok}/{n} = {cnn_ok/n*100:.1f}%")
print("\n逐张(真实 | 规则 | 融合 | CNN):")
for d in detail:
    mark = "✓" if d[6] else "✗"
    print(f"  {d[0][:44]:<46} {d[1]:<6} | {d[2]:<6} | {d[3]:<6} | {d[4]:<6} {mark}")
