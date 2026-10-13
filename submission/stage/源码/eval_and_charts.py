# -*- coding: utf-8 -*-
"""eval_and_charts.py —— 在验证集上逐类评估 + 生成参赛图表
输出到 D:\\train\\materials\\:
  chart_counts.png    各类 train/val 样本数
  chart_acc_curve.png 验证准确率随 epoch 变化
  chart_confusion.png 混淆矩阵
  chart_perclass.png  逐类验证准确率
  eval_results.json   逐类准确率/混淆矩阵/总体准确率
"""
import os, sys, json, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager as fm
import matplotlib.pyplot as plt

# 中文字体
for fp in [r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"]=fm.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"]=False

DATA=r"D:\train\algae_dataset"; MODEL=r"D:\train\model"; OUT=r"D:\train\materials"
os.makedirs(OUT,exist_ok=True)
sys.path.insert(0,r"D:\train\tools")

cmap=json.load(open(os.path.join(DATA,"class_map.json"),encoding="utf-8"))
classes=cmap["classes"]; N=len(classes)
cn={s:cmap["meta"][s]["cn"] for s in classes}
log=json.load(open(os.path.join(MODEL,"train_log.json"),encoding="utf-8"))

from predict import Predictor
P=Predictor()
cm=np.zeros((N,N),dtype=int)
perclass={}
for i,slug in enumerate(classes):
    fs=sorted(glob.glob(os.path.join(DATA,"val",slug,"*.jpg")))
    ok=0
    for f in fs:
        r=P.predict(f,topk=1)[0]
        j=classes.index(r["slug"]); cm[i,j]+=1
        if j==i: ok+=1
    perclass[slug]=round(ok/len(fs),4) if fs else 0.0
    print(f"{cn[slug]:<8} val={len(fs):>3} acc={perclass[slug]*100:5.1f}%")
total_ok=int(np.trace(cm)); total=int(cm.sum())
overall=total_ok/total
print(f"\n总体验证准确率 {total_ok}/{total} = {overall*100:.2f}%")

json.dump({"classes":classes,"cn":cn,"per_class_acc":perclass,
           "overall_val_acc":round(overall,4),"confusion":cm.tolist(),
           "best_epoch_acc":log["best_val_acc"]},
          open(os.path.join(OUT,"eval_results.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=2)

# ---- 图1 各类样本数 ----
summ=cmap["summary"]
tr=[summ[s]["train"] for s in classes]; va=[summ[s]["val"] for s in classes]
x=np.arange(N); w=0.38
fig,ax=plt.subplots(figsize=(9,4.6),dpi=150)
ax.bar(x-w/2,tr,w,label="训练集",color="#2E75B6")
ax.bar(x+w/2,va,w,label="验证集",color="#F4A261")
ax.set_xticks(x); ax.set_xticklabels([cn[s] for s in classes],fontsize=11)
ax.set_ylabel("图像数"); ax.set_title("各类别样本量(GBIF 真实采集影像)",fontsize=13)
ax.legend(); ax.grid(axis="y",alpha=.3)
for i,(a,b) in enumerate(zip(tr,va)):
    ax.text(i-w/2,a+2,str(a),ha="center",fontsize=9); ax.text(i+w/2,b+2,str(b),ha="center",fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"chart_counts.png")); plt.close(fig)

# ---- 图2 准确率曲线 ----
hist=log["history"]; ep=[h["epoch"] for h in hist]; acc=[h["val_acc"] for h in hist]; ls=[h["loss"] for h in hist]
fig,ax=plt.subplots(figsize=(9,4.6),dpi=150)
ax.plot(ep,acc,"o-",color="#2E75B6",label="验证准确率")
ax.axhline(0.80,color="red",ls="--",lw=1,label="验收线 80%")
ax.set_xlabel("epoch"); ax.set_ylabel("验证准确率"); ax.set_ylim(0.75,1.0)
ax.set_title(f"验证准确率曲线(最佳 {log['best_val_acc']*100:.1f}%)",fontsize=13)
ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"chart_acc_curve.png")); plt.close(fig)

# ---- 图3 混淆矩阵 ----
fig,ax=plt.subplots(figsize=(7,6),dpi=150)
im=ax.imshow(cm,cmap="Blues")
ax.set_xticks(range(N)); ax.set_yticks(range(N))
ax.set_xticklabels([cn[s] for s in classes],rotation=30,ha="right",fontsize=10)
ax.set_yticklabels([cn[s] for s in classes],fontsize=10)
for i in range(N):
    for j in range(N):
        ax.text(j,i,cm[i,j],ha="center",va="center",
                color="white" if cm[i,j]>cm.max()/2 else "black",fontsize=10)
ax.set_xlabel("预测"); ax.set_ylabel("真实"); ax.set_title("验证集混淆矩阵",fontsize=13)
fig.colorbar(im,ax=ax,shrink=.8); fig.tight_layout()
fig.savefig(os.path.join(OUT,"chart_confusion.png")); plt.close(fig)

# ---- 图4 逐类准确率 ----
vals=[perclass[s]*100 for s in classes]
fig,ax=plt.subplots(figsize=(9,4.6),dpi=150)
cols=["#C0392B" if v<80 else "#27AE60" for v in vals]
ax.bar([cn[s] for s in classes],vals,color=cols)
ax.axhline(80,color="red",ls="--",lw=1,label="验收线 80%")
ax.set_ylabel("验证准确率(%)"); ax.set_ylim(0,105)
ax.set_title("逐类验证准确率",fontsize=13); ax.legend(); ax.grid(axis="y",alpha=.3)
for i,v in enumerate(vals): ax.text(i,v+1,f"{v:.0f}%",ha="center",fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"chart_perclass.png")); plt.close(fig)

print("charts saved to",OUT)
