# -*- coding: utf-8 -*-
"""宏观海面赤潮图像可行性探测: 对候选致灾类群从GBIF拉少量带图记录, 下载样本并拼montage供目视判断宏观比例与水色."""
import os, io, json, time, hashlib, requests
from PIL import Image

ROOT = r"D:\train\dataset_raw\macro_probe"
os.makedirs(ROOT, exist_ok=True)
SAMPLE = 12
UA = {"User-Agent": "redtide-probe/1.0 (research; contact: student)"}

TAXA = [
    ("noctiluca",   "夜光藻",       "Noctiluca scintillans"),
    ("karenia",     "卡伦藻/短裸藻", "Karenia brevis"),
    ("margalef",    "多纹边沟藻",   "Margalefidinium polykrikoides"),
    ("akashiwo",    "血赤潮藻",     "Akashiwo sanguinea"),
    ("ulva",        "浒苔/石莼",    "Ulva prolifera"),
    ("phaeocystis", "球等鞭金藻/棕囊藻", "Phaeocystis globosa"),
    ("heterocapsa", "圆斑隐藻",     "Heterocapsa circularisquama"),
]

def get(url, tries=2, timeout=25):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
        except Exception:
            pass
        time.sleep(0.6)
    return None

def match_key(name):
    r = get("https://api.gbif.org/v1/species/match?name=" + requests.utils.quote(name))
    if not r:
        return None
    j = r.json()
    return j.get("usageKey") or j.get("speciesKey")

def probe(slug, cn, sci):
    d = os.path.join(ROOT, slug)
    os.makedirs(d, exist_ok=True)
    key = match_key(sci)
    if not key:
        print(f"[{slug}] 无法匹配 {sci}")
        return
    rows = []
    offset = 0
    while len(rows) < SAMPLE:
        u = (f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}"
             f"&mediaType=still_image&limit=60&offset={offset}")
        r = get(u)
        if not r:
            break
        j = r.json()
        res = j.get("results", [])
        if not res:
            break
        for occ in res:
            for m in occ.get("media", []):
                if m.get("type") != "StillImage":
                    continue
                url = m.get("identifier")
                if not url:
                    continue
                rows.append({"occ": occ.get("key"), "sci": occ.get("scientificName"),
                             "url": url, "lic": m.get("license"), "rh": m.get("rightsHolder")})
                if len(rows) >= SAMPLE:
                    break
        offset += 60
        if offset > 300:
            break
    print(f"[{slug}] {sci} 取到媒体 {len(rows)} 条, 开始下载样本")
    prov = []
    for i, row in enumerate(rows):
        rr = get(row["url"], tries=2, timeout=30)
        if not rr or len(rr.content) < 5000:
            continue
        md5 = hashlib.md5(rr.content).hexdigest()
        fn = os.path.join(d, f"{slug}_{i:02d}.jpg")
        with open(fn, "wb") as fp:
            fp.write(rr.content)
        prov.append(dict(row, file=os.path.basename(fn), md5=md5, bytes=len(rr.content)))
        time.sleep(0.3)
    with open(os.path.join(d, "probe_provenance.json"), "w", encoding="utf-8") as fp:
        json.dump(prov, fp, ensure_ascii=False, indent=1)
    # montage 4x3
    thumbs = []
    for p in prov:
        try:
            im = Image.open(os.path.join(d, p["file"])).convert("RGB")
            im.thumbnail((300, 300))
            thumbs.append(im)
        except Exception:
            pass
    if thumbs:
        cols, rowsn = 4, 3
        W, H = 300, 300
        canvas = Image.new("RGB", (cols*W, rowsn*H), (255, 255, 255))
        for idx, im in enumerate(thumbs[:cols*rowsn]):
            x, y = (idx % cols)*W, (idx//cols)*H
            canvas.paste(im, (x, y))
        canvas.save(os.path.join(ROOT, f"montage_{slug}.jpg"), quality=85)
    print(f"[{slug}] 下载 {len(prov)} 张, montage已生成")

if __name__ == "__main__":
    for slug, cn, sci in TAXA:
        probe(slug, cn, sci)
    print("探测完成")
