# -*- coding: utf-8 -*-
"""数据预处理: 去重 -> 校验 -> 统一 224x224 -> 划分 train/val
输入: D:\\train\\dataset_raw\\gbif2\\<slug>\\*.jpg  (+ cnki 补充)
输出: D:\\train\\algae_dataset\\train\\<slug>\\  与  val\\<slug>\\
类别映射写入 D:\\train\\algae_dataset\\class_map.json
"""
import os, sys, json, hashlib, random, shutil
from PIL import Image

random.seed(42)
RAW_GBIF = r"D:\train\dataset_raw\gbif2"
RAW_CNKI = r"D:\train\dataset_raw\cnki"
DST = r"D:\train\algae_dataset"
SIZE = 224
VAL_RATIO = 0.2
MIN_PER_CLASS = 20   # 低于此数的类别将被警告

# slug -> (中文显示名, 学名/代表种)
CLASS_META = {
    "noctiluca":      ("夜光藻",     "Noctiluca scintillans"),
    "prorocentrum":   ("原甲藻属",   "Prorocentrum (代表种:东海原甲藻 P. donghaiense)"),
    "chaetoceros":    ("角毛藻属",   "Chaetoceros (代表种:旋链角毛藻 C. curvisetus)"),
    "pseudonitzschia":("拟菱形藻属", "Pseudo-nitzschia (代表种:尖刺拟菱形藻 P. pungens)"),
    "skeletonema":    ("骨条藻属",   "Skeletonema (代表种:中肋骨条藻 S. costatum)"),
    "alexandrium":    ("亚历山大藻属","Alexandrium (代表种:塔玛亚历山大藻 A. tamarense)"),
    "karenia":        ("凯伦藻属",   "Karenia (代表种:米氏凯伦藻 K. mikimotoi)"),
}
# CNKI 目录 slug -> gbif slug 归并
CNKI_MAP = {"prorocentrum_donghaiense": "prorocentrum"}

def load_hashes():
    return set()

def collect_source_images():
    """返回 {slug: [文件路径,...]} 合并 gbif + cnki"""
    buckets = {s: [] for s in CLASS_META}
    if os.path.isdir(RAW_GBIF):
        for slug in os.listdir(RAW_GBIF):
            d = os.path.join(RAW_GBIF, slug)
            if os.path.isdir(d) and slug in buckets:
                for f in os.listdir(d):
                    if f.lower().endswith((".jpg",".jpeg",".png")):
                        buckets[slug].append(os.path.join(d,f))
    if os.path.isdir(RAW_CNKI):
        for slug in os.listdir(RAW_CNKI):
            d = os.path.join(RAW_CNKI, slug)
            if os.path.isdir(d):
                tgt = CNKI_MAP.get(slug, slug)
                if tgt in buckets:
                    for f in os.listdir(d):
                        if f.lower().endswith((".jpg",".jpeg",".png")):
                            buckets[tgt].append(os.path.join(d,f))
    return buckets

def process():
    buckets = collect_source_images()
    for split in ("train","val"):
        os.makedirs(os.path.join(DST,split), exist_ok=True)
    summary = {}
    for slug, files in buckets.items():
        if not files:
            print(f"[warn] {slug} 无图片, 跳过"); continue
        # 内容去重
        seen=set(); uniq=[]
        for p in files:
            try:
                h=hashlib.md5(open(p,"rb").read()).hexdigest()
            except Exception:
                continue
            if h in seen: continue
            seen.add(h); uniq.append(p)
        random.shuffle(uniq)
        n_val=max(2,int(round(len(uniq)*VAL_RATIO))) if len(uniq)>=10 else max(1,len(uniq)//5 or 1)
        val=uniq[:n_val]; train=uniq[n_val:]
        for split,arr in (("train",train),("val",val)):
            od=os.path.join(DST,split,slug); os.makedirs(od,exist_ok=True)
            for i,src in enumerate(arr):
                try:
                    im=Image.open(src).convert("RGB")
                    # 中心裁剪为正方形再缩放, 避免拉伸失真
                    w,h=im.size; s=min(w,h)
                    im=im.crop(((w-s)//2,(h-s)//2,(w-s)//2+s,(h-s)//2+s)).resize((SIZE,SIZE),Image.LANCZOS)
                    im.save(os.path.join(od,f"{slug}_{split}_{i:04d}.jpg"),quality=92)
                except Exception as e:
                    print(f"  bad img {src} :: {e}")
        summary[slug]={"cn_display":CLASS_META[slug][0],"sci":CLASS_META[slug][1],
                       "raw":len(files),"dedup":len(uniq),"train":len(train),"val":len(val)}
        flag=" [偏少!]" if len(uniq)<MIN_PER_CLASS else ""
        print(f"{CLASS_META[slug][0]:<8}({slug}) 原始{len(files)} 去重后{len(uniq)} train{len(train)}/val{len(val)}{flag}")
    # class_map.json (仅保留有数据的类) —— 必须按字母序, 与 ImageFolderDataset 的标签索引一致
    kept=sorted(summary.keys())
    cmap={"classes":kept,"meta":{s:{"cn":CLASS_META[s][0],"sci":CLASS_META[s][1]} for s in kept},
          "size":SIZE,"summary":summary}
    with open(os.path.join(DST,"class_map.json"),"w",encoding="utf-8") as f:
        json.dump(cmap,f,ensure_ascii=False,indent=2)
    print("\n保留类别数:",len(kept),"->",kept)
    print("class_map.json 已写入")

if __name__=="__main__":
    process()
