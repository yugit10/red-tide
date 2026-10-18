# -*- coding: utf-8 -*-
"""训后验证: 预检模型在 val 全量 + 真海面25张 + 无关图上的表现 + 与规则流兜底对比"""
import sys, os, json, glob
sys.path.insert(0, r"D:\train\_pylibs")
sys.path.insert(0, r"D:\train\tools")
import numpy as np
from PIL import Image
import mindspore as ms
from mindspore import Tensor
from mindcv import create_model
import fusion

MEAN = [0.485*255, 0.456*255, 0.406*255]
STD  = [0.229*255, 0.224*255, 0.225*255]
CK = r"D:\train\model_precheck\best.ckpt"

def load_net():
    net = create_model("mobilenet_v3_small_100", num_classes=2, pretrained=False, in_channels=3)
    ms.load_param_into_net(net, ms.load_checkpoint(CK))
    net.set_train(False)
    return net

net = load_net()

def cnn_pred(pil_img):
    img = pil_img.convert("RGB").resize((224, 224), Image.BILINEAR)
    a = np.asarray(img).astype(np.float32)
    for i in range(3):
        a[..., i] = (a[..., i] - MEAN[i]) / STD[i]
    logits = net(Tensor(a.transpose(2, 0, 1)[None])).asnumpy()[0]
    p = np.exp(logits - logits.max()); p = p / p.sum()
    return "sea" if p[1] >= 0.5 else "nonsea", float(p[1])  # 类1=sea (目录字母序 nonsea=0)

def eval_dir(label, dirpath, expect_sea, cap=9999):
    files = sorted(glob.glob(os.path.join(dirpath, "**", "*.jpg"), recursive=True))[:cap]
    ok = 0; n = 0; errs = []
    for f in files:
        try:
            pred, prob = cnn_pred(Image.open(f))
        except Exception:
            continue
        n += 1
        good = (pred == ("sea" if expect_sea else "nonsea"))
        ok += good
        if not good and len(errs) < 5:
            errs.append((os.path.basename(f)[:32], round(prob, 3)))
    print(f"{label}: {ok}/{n} = {ok/max(n,1)*100:.1f}%  (期望{'放行' if expect_sea else '拒绝'})")
    for e in errs:
        print("    误判:", e)
    return ok / max(n, 1)

print("=== 预检模型 (best.ckpt) ===")
eval_dir("[val] 真海面", r"D:\train\_macro_dataset\precheck\val\sea", True)
eval_dir("[val] 非海面", r"D:\train\_macro_dataset\precheck\val\nonsea", False)
eval_dir("真海面·raw(25张人工)", r"D:\train\dataset_raw\macro\raw", True, cap=60)
eval_dir("网页非海面抽测", r"D:\train\_macro_scratch\nonsea", False, cap=60)
eval_dir("合成非海面", r"D:\train\_macro_scratch\nonsea_syn", False)

print("\n=== 对比: 规则流兜底(同样本) ===")
def rule_eval(label, paths, expect_sea, cap=9999):
    files = sorted(paths)[:cap]
    ok = 0; n = 0; errs = []
    for f in files:
        try:
            is_sea, src, sc, det = fusion.sea_precheck(Image.open(f))
        except Exception:
            continue
        n += 1
        good = (is_sea == expect_sea)
        ok += good
        if not good and len(errs) < 4:
            errs.append((os.path.basename(f)[:32], sc))
    print(f"{label}: {ok}/{n} = {ok/max(n,1)*100:.1f}%")
    for e in errs:
        print("    误判:", e)
rule_eval("真海面·raw", glob.glob(r"D:\train\dataset_raw\macro\raw\*\keep\*.jpg"), True)
rule_eval("网页非海面", glob.glob(r"D:\train\_macro_scratch\nonsea\*.jpg"), False)
rule_eval("合成非海面", glob.glob(r"D:\train\_macro_scratch\nonsea_syn\*.jpg"), False)

# 训练日志
tl = json.load(open(r"D:\train\model_precheck\train_log.json", encoding="utf-8"))
print("\n训练日志: best_val_acc =", tl.get("best_val_acc"), "| epochs =", tl.get("epochs"),
      "| 用时 =", tl.get("elapsed_sec"), "s")
