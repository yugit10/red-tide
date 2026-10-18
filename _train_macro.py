# -*- coding: utf-8 -*-
"""train_macro.py —— 宏观海面分支 5 分类 CNN(MindSpore + MindCV MobileNetV3-Small)
训练集: 搜索引擎公开图 + 规则流水色CV伪标签( _macro_dataset/train )
监控集: 同源伪标签( _macro_dataset/monitor ) 仅监控过拟合, 不作为准确率声明
准确率以人工精选真实图(warm/normal/green)验证, 见 eval_macro_real.py
用法: python train_macro.py [--epochs 20] [--lr 0.001] [--bs 32]
输出: D:\train\model_macro\best.ckpt + train_log.json
"""
import os, sys, json, time, argparse
import mindspore as ms
from mindspore import nn, context
import mindspore.dataset as ds
import mindspore.dataset.vision as vision
from mindcv import create_model

DATA = r"D:\train\_macro_dataset"
MODEL_DIR = r"D:\train\model_macro"
SIZE = 224
MEAN = [0.485*255, 0.456*255, 0.406*255]
STD  = [0.229*255, 0.224*255, 0.225*255]

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--bs", type=int, default=32)
    return p.parse_args()

def build_dataset(split, bs, shuffle):
    path = os.path.join(DATA, split)
    d = ds.ImageFolderDataset(path, num_parallel_workers=2, shuffle=shuffle)
    trans = [vision.Decode(),
             vision.Resize((SIZE + 16, SIZE + 16)),
             vision.RandomCrop((SIZE, SIZE)),
             vision.RandomHorizontalFlip(0.5),
             vision.Normalize(mean=MEAN, std=STD),
             vision.HWC2CHW()]
    d = d.map(operations=trans, input_columns="image", num_parallel_workers=2)
    d = d.map(operations=ds.transforms.TypeCast(ms.int32), input_columns="label", num_parallel_workers=2)
    return d.batch(bs, drop_remainder=False, num_parallel_workers=2)

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
    cmap = json.load(open(os.path.join(DATA, "class_map.json"), encoding="utf-8"))
    classes = cmap["classes"]; N = len(classes)
    print("宏观 5 类:", classes)

    try:
        net = create_model("mobilenet_v3_small_100", num_classes=N, pretrained=True, in_channels=3)
        print("pretrained=True")
    except Exception as e:
        print("回退 scratch:", e)
        net = create_model("mobilenet_v3_small_100", num_classes=N, pretrained=False, in_channels=3)

    frozen = 0; trainable = 0
    for name, param in net.parameters_and_names():
        if ("classifier" in name) or ("head" in name) or ("fc" in name):
            param.requires_grad = True; trainable += 1
        else:
            param.requires_grad = False; frozen += 1
    print(f"冻结 {frozen}, 可训练 {trainable}")

    train = build_dataset("train", args.bs, True)
    mon = build_dataset("monitor", args.bs, False)
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
        # 仅用 monitor(伪标签监控集)评估选优, 省去对整训练集的重复前向
        vacc = evaluate(net, mon)
        hist.append({"epoch": ep, "loss": running / max(nb, 1),
                     "monitor_acc": round(vacc, 4)})
        tag = ""
        if vacc > best:
            best = vacc
            ms.save_checkpoint(net, os.path.join(MODEL_DIR, "best.ckpt"))
            tag = " *saved"
        print(f"epoch {ep:>2}/{args.epochs} loss {running/max(nb,1):.4f} monitor {vacc:.4f}{tag}", flush=True)
    with open(os.path.join(MODEL_DIR, "train_log.json"), "w", encoding="utf-8") as fp:
        json.dump({"classes": classes, "best_monitor_acc": round(best, 4),
                   "note": "best 按 monitor(伪标签监控集)选择; 真实准确率见 eval_macro_real.py 的人工精选验证",
                   "epochs": args.epochs, "lr": args.lr, "bs": args.bs,
                   "elapsed_sec": round(time.time() - t0, 1), "history": hist},
                  fp, ensure_ascii=False, indent=2)
    print(f"\n完成. best monitor acc = {best:.4f}  用时 {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
