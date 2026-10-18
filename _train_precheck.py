# -*- coding: utf-8 -*-
"""train_precheck.py —— 海面/非海面 二分类预检 CNN(MindSpore + MindCV MobileNetV3-Small)
正样本: 3065 张宏观海面(伪标签五分类数据集, 全作"海面")
负样本: 网页真实场景(草地/森林/城市/室内/文档/人像等) + 合成硬负例(纯色/噪点/文字/网格)
用途: app 上传照片先过预检, 判定"非海面" → 拒绝出藻类结论, 不进入融合
输出: D:\train\model_precheck\best.ckpt + train_log.json
用法: python train_precheck.py [--epochs 12] [--lr 0.0008] [--bs 32]
"""
import os, sys, json, time, argparse
import mindspore as ms
from mindspore import nn, context
import mindspore.dataset as ds
import mindspore.dataset.vision as vision
from mindcv import create_model

DATA = r"D:\train\_macro_dataset\precheck"
MODEL_DIR = r"D:\train\model_precheck"
SIZE = 224
MEAN = [0.485*255, 0.456*255, 0.406*255]
STD  = [0.229*255, 0.224*255, 0.225*255]

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--lr", type=float, default=6e-4)
    p.add_argument("--bs", type=int, default=32)
    return p.parse_args()

def build_dataset(split, bs, shuffle, train_aug=False):
    path = os.path.join(DATA, split)
    # 单 worker: 规避 MindSpore CPU 版 dataset pipeline 偶发死锁
    d = ds.ImageFolderDataset(path, num_parallel_workers=1, shuffle=shuffle)
    if train_aug:
        trans = [vision.Decode(),
                 vision.Resize((SIZE + 16, SIZE + 16)),
                 vision.RandomCrop((SIZE, SIZE)),
                 vision.RandomHorizontalFlip(0.5),
                 vision.RandomColorAdjust(brightness=0.2, saturation=0.2),
                 vision.Normalize(mean=MEAN, std=STD),
                 vision.HWC2CHW()]
    else:
        trans = [vision.Decode(),
                 vision.Resize((SIZE, SIZE)),
                 vision.CenterCrop((SIZE, SIZE)),
                 vision.Normalize(mean=MEAN, std=STD),
                 vision.HWC2CHW()]
    d = d.map(operations=trans, input_columns="image", num_parallel_workers=1)
    d = d.map(operations=ds.transforms.TypeCast(ms.int32), input_columns="label", num_parallel_workers=1)
    return d.batch(bs, drop_remainder=False, num_parallel_workers=1)

def evaluate(net, loader):
    net.set_train(False)
    tot = 0; corr = 0
    for img, lab in loader.create_tuple_iterator():
        out = net(img)
        corr += (out.argmax(axis=1) == lab).sum().asnumpy().item()
        tot += len(lab)
    return corr / max(tot, 1)

def main():
    args = parse()
    context.set_context(mode=context.PYNATIVE_MODE, device_target="CPU")
    os.makedirs(MODEL_DIR, exist_ok=True)
    classes = ["sea", "nonsea"]
    print("预检 2 类:", classes)

    try:
        net = create_model("mobilenet_v3_small_100", num_classes=2, pretrained=True, in_channels=3)
        print("pretrained=True")
    except Exception as e:
        print("回退 scratch:", e)
        net = create_model("mobilenet_v3_small_100", num_classes=2, pretrained=False, in_channels=3)

    train = build_dataset("train", args.bs, True, train_aug=True)
    val = build_dataset("val", args.bs, False)
    loss_fn = nn.CrossEntropyLoss()
    opt = nn.Adam(net.trainable_params(), learning_rate=args.lr)

    def forward_fn(img, lab):
        return loss_fn(net(img), lab)
    grad_fn = ms.value_and_grad(forward_fn, None, net.trainable_params())

    best = 0.0; hist = []; t0 = time.time()
    for ep in range(1, args.epochs + 1):
        net.set_train(True); running = 0.0; nb = 0
        for img, lab in train.create_tuple_iterator():
            loss, grads = grad_fn(img, lab)
            opt(grads)
            running += loss.asnumpy().item(); nb += 1
        vacc = evaluate(net, val)
        hist.append({"epoch": ep, "loss": running / max(nb, 1), "val_acc": round(vacc, 4)})
        tag = ""
        if vacc > best:
            best = vacc
            ms.save_checkpoint(net, os.path.join(MODEL_DIR, "best.ckpt"))
            tag = " *saved"
        print(f"epoch {ep:>2}/{args.epochs} loss {running/max(nb,1):.4f} val {vacc:.4f}{tag}", flush=True)
    with open(os.path.join(MODEL_DIR, "train_log.json"), "w", encoding="utf-8") as fp:
        json.dump({"classes": classes, "best_val_acc": round(best, 4), "data": DATA,
                   "note": "预检: 判定海面/非海面; 非海面直接拒绝出藻类结论",
                   "epochs": args.epochs, "lr": args.lr, "bs": args.bs,
                   "elapsed_sec": round(time.time() - t0, 1), "history": hist},
                  fp, ensure_ascii=False, indent=2)
    print(f"\n完成. best val acc = {best:.4f}  用时 {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
