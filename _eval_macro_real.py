# -*- coding: utf-8 -*-
"""eval_macro_real.py —— 宏观 CNN 在 25 张人工精选真实图上的验证
真实标签口径(3 类): warm=赤潮(暖色水华) / green=绿潮 / normal=正常海水
CNN 5 类→3 类映射: noctiluca|toxic_dino|diatom → warm; green_tide → green; none → normal
与规则流(image_color_likelihood)基线对比, 诚实并列报告。
用法: python eval_macro_real.py [--ckpt best.ckpt]
"""
import os, sys, json, argparse
import numpy as np
from PIL import Image
import mindspore as ms
from mindcv import create_model

DATA = r"D:\train\_macro_dataset"
MODEL_DIR = r"D:\train\model_macro"
SIZE = 224
MEAN = [0.485*255, 0.456*255, 0.406*255]
STD  = [0.229*255, 0.224*255, 0.225*255]

# 真实图: keep 目录, 文件名前缀 = 真实标签(warm/normal/green)
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
KEEP_ROOT = r"D:\train\dataset_raw\macro\raw"  # keep 图所在(文件名前缀是真实类, 文件夹是旧分组)

# 5类（按 class_map.json）与 warm/green/normal 映射
HYP_TO_COARSE = {"noctiluca": "warm", "toxic_dino": "warm", "diatom": "warm",
                 "green_tide": "green", "none": "normal"}
COARSE_ORDER = ["warm", "green", "normal"]


def load_real():
    items = []
    # 预扫描所有 keep 目录的文件路径
    path_by_name = {}
    for folder in ["warm", "normal", "green"]:
        for keep_dir in ["keep", "drop_curated"]:
            base = os.path.join(KEEP_ROOT, folder, keep_dir)
            if not os.path.isdir(base):
                continue
            for fn in os.listdir(base):
                path_by_name.setdefault(fn, os.path.join(base, fn))
    for coarse, names in REAL.items():
        for fn in names:
            p = path_by_name.get(fn)
            if p:
                items.append((p, coarse, fn))
            else:
                print("  警告: 找不到真实图", fn)
    return items


def preprocess(pil_img):
    img = pil_img.convert("RGB").resize((SIZE, SIZE), Image.BILINEAR)
    a = np.asarray(img).astype(np.float32)
    for i in range(3):
        a[..., i] = (a[..., i] - MEAN[i]) / STD[i]
    return a.transpose(2, 0, 1)[None]


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--ckpt", default=os.path.join(MODEL_DIR, "best.ckpt"))
    args = args.parse_args()

    cmap = json.load(open(os.path.join(DATA, "class_map.json"), encoding="utf-8"))
    classes = cmap["classes"]; N = len(classes)
    net = create_model("mobilenet_v3_small_100", num_classes=N, pretrained=False, in_channels=3)
    ms.load_param_into_net(net, ms.load_checkpoint(args.ckpt))

    items = load_real()
    print("找到真实验证图:", len(items))

    # 规则流基线
    sys.path.insert(0, r"D:\train\tools")
    import fusion
    cnn_corr = 0; rule_corr = 0; detail = []
    for p, coarse, fn in items:
        im = Image.open(p)
        # 规则流: 图片→水色→似然→argmax(HYP)
        lab, lik, meta = fusion.image_color_likelihood(im)
        rule_hyp = max(fusion.HYP, key=lambda h: (lik[h], -fusion.HYP.index(h)))
        rule_coarse = HYP_TO_COARSE[rule_hyp]
        # CNN
        out = net(ms.Tensor(preprocess(im)))
        hyp_idx = int(out.argmax().asnumpy())
        cnn_hyp = classes[hyp_idx]; cnn_coarse = HYP_TO_COARSE[cnn_hyp]
        cnn_corr += (cnn_coarse == coarse)
        rule_corr += (rule_coarse == coarse)
        detail.append((fn, coarse, "rule->%s" % rule_coarse, "cnn->%s(%s)" % (cnn_coarse, cnn_hyp),
                       rule_coarse == coarse, cnn_coarse == coarse))
    n = len(items)
    print(f"\nCNN 真实验证: {cnn_corr}/{n} = {cnn_corr/n*100:.1f}% (5类->3类映射)")
    print(f"规则流基线:  {rule_corr}/{n} = {rule_corr/n*100:.1f}%")
    print("\n逐张明细:")
    for d in detail:
        print("  %-40s %-6s | %-14s | %-18s | rule=%s cnn=%s" % (d[0], d[1], d[2], d[3], d[4], d[5]))

    with open(os.path.join(MODEL_DIR, "real_eval.json"), "w", encoding="utf-8") as f:
        json.dump({"n": n, "cnn_corr": cnn_corr, "cnn_acc": round(cnn_corr/n, 4),
                   "rule_corr": rule_corr, "rule_acc": round(rule_corr/n, 4),
                   "detail": [{"file": d[0], "true": d[1], "rule": d[2], "cnn": d[3],
                               "rule_ok": d[4], "cnn_ok": d[5]} for d in detail]},
                  f, ensure_ascii=False, indent=2)
    print("\nsaved", os.path.join(MODEL_DIR, "real_eval.json"))


if __name__ == "__main__":
    main()
