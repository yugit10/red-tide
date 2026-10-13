# -*- coding: utf-8 -*-
"""train.py —— MindSpore + MindCV MobileNetV3 迁移学习
用法: python train.py [--epochs 30] [--lr 0.001] [--bs 16] [--scratch]
读取 D:\\train\\algae_dataset 下 train/ 与 val/ 与 class_map.json
输出: D:\\train\\model\\best.ckpt, train_log.json
"""
import os, sys, json, time, argparse
import numpy as np
import mindspore as ms
from mindspore import nn, context
import mindspore.dataset as ds
import mindspore.dataset.vision as vision
from mindcv import create_model

DATA = r"D:\train\algae_dataset"
MODEL_DIR = r"D:\train\model"
SIZE = 224
MEAN = [0.485*255, 0.456*255, 0.406*255]
STD  = [0.229*255, 0.224*255, 0.225*255]

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--epochs",type=int,default=30)
    p.add_argument("--lr",type=float,default=1e-3)
    p.add_argument("--bs",type=int,default=16)
    p.add_argument("--scratch",action="store_true",help="不用预训练权重")
    return p.parse_args()

def build_dataset(split, bs, shuffle):
    path=os.path.join(DATA,split)
    dataset=ds.ImageFolderDataset(path,num_parallel_workers=2,shuffle=shuffle)
    trans=[]
    if split=="train":
        trans+= [vision.Decode(),
                 vision.Resize((SIZE+16,SIZE+16)),
                 vision.RandomCrop((SIZE,SIZE)),
                 vision.RandomHorizontalFlip(0.5),
                 vision.Normalize(mean=MEAN,std=STD),
                 vision.HWC2CHW()]
    else:
        trans+= [vision.Decode(),
                 vision.Resize((SIZE,SIZE)),
                 vision.Normalize(mean=MEAN,std=STD),
                 vision.HWC2CHW()]
    dataset=dataset.map(operations=trans,input_columns="image",num_parallel_workers=2)
    dataset=dataset.map(operations=ds.transforms.TypeCast(ms.int32),input_columns="label",num_parallel_workers=2)
    dataset=dataset.batch(bs,drop_remainder=False,num_parallel_workers=2)
    return dataset

def freeze_backbone(net):
    frozen=0; trainable=0
    for name,param in net.parameters_and_names():
        if ("classifier" in name) or ("head" in name) or ("fc" in name):
            param.requires_grad=True; trainable+=1
        else:
            param.requires_grad=False; frozen+=1
    return frozen,trainable

def evaluate(net,loader):
    net.set_train(False)
    tot=0; corr=0
    for img,lab in loader.create_tuple_iterator():
        out=net(img)
        pred=out.argmax(axis=1)
        corr+=(pred==lab).sum().asnumpy().item(); tot+=len(lab)
    net.set_train(True)
    return corr/max(tot,1)

def main():
    args=parse()
    context.set_context(mode=context.PYNATIVE_MODE,device_target="CPU")
    os.makedirs(MODEL_DIR,exist_ok=True)
    cmap=json.load(open(os.path.join(DATA,"class_map.json"),encoding="utf-8"))
    classes=cmap["classes"]; N=len(classes)
    print("类别数:",N,classes)
    assert N>=2,"类别不足, 请先跑 prepare_data.py"

    # 预训练权重下载失败则回退 scratch
    pretrained = not args.scratch
    try:
        net=create_model("mobilenet_v3_small_100",num_classes=N,pretrained=pretrained,in_channels=3)
        print("pretrained=",pretrained)
    except Exception as e:
        print("预训练加载失败, 回退 scratch:",e)
        net=create_model("mobilenet_v3_small_100",num_classes=N,pretrained=False,in_channels=3)
        pretrained=False
    f,t=freeze_backbone(net)
    print(f"冻结参数 {f}, 可训练参数 {t}")

    train=build_dataset("train",args.bs,True)
    val=build_dataset("val",args.bs,False)
    loss_fn=nn.CrossEntropyLoss()
    opt=nn.Adam(net.trainable_params(),learning_rate=args.lr)

    def forward_fn(img, lab):
        return loss_fn(net(img), lab)
    grad_fn = ms.value_and_grad(forward_fn, None, net.trainable_params())

    best=0.0; hist=[]; t0=time.time()
    for ep in range(1,args.epochs+1):
        net.set_train(True); running=0.0; nb=0
        for img,lab in train.create_tuple_iterator():
            loss,grads=grad_fn(img,lab)
            opt(grads)
            running+=loss.asnumpy().item(); nb+=1
        acc=evaluate(net,val)
        hist.append({"epoch":ep,"loss":running/max(nb,1),"val_acc":round(acc,4)})
        tag=""
        if acc>best:
            best=acc
            ms.save_checkpoint(net,os.path.join(MODEL_DIR,"best.ckpt"))
            tag=" *saved"
        print(f"epoch {ep:>2}/{args.epochs} loss {running/max(nb,1):.4f} val_acc {acc:.4f}{tag}")
    with open(os.path.join(MODEL_DIR,"train_log.json"),"w",encoding="utf-8") as fp:
        json.dump({"classes":classes,"best_val_acc":round(best,4),"pretrained":pretrained,
                   "epochs":args.epochs,"lr":args.lr,"bs":args.bs,
                   "elapsed_sec":round(time.time()-t0,1),"history":hist},fp,ensure_ascii=False,indent=2)
    print(f"\n完成. 最佳验证准确率 = {best:.4f}  用时 {time.time()-t0:.0f}s")
    print("best.ckpt / train_log.json 已保存到",MODEL_DIR)

if __name__=="__main__":
    main()
