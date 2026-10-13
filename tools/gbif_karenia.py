# -*- coding: utf-8 -*-
"""gbif_karenia.py —— 下载 Karenia(米氏凯伦藻为代表) 图像到 gbif2/karenia, 追加 provenance.
合并 K. mikimotoi(种) + K. brevis(同属) 两个 key, 属级协议, provenance 记录实际种名.
"""
import os, time, hashlib, csv, requests

ROOT = r"D:\train\dataset_raw\gbif2"
PROV = os.path.join(ROOT, "provenance.csv")
D = os.path.join(ROOT, "karenia")
os.makedirs(D, exist_ok=True)
UA = {"User-Agent": "redtide-dl/1.0 (research)"}
MIN_BYTES = 5000
KEYS = [(7454879, "Karenia mikimotoi"), (5424511, "Karenia brevis")]

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

# 已有md5去重集合: 实算现有jpg
seen = set()
for cls in os.listdir(ROOT):
    cd = os.path.join(ROOT, cls)
    if not os.path.isdir(cd):
        continue
    for f in os.listdir(cd):
        if f.endswith(".jpg"):
            try:
                seen.add(hashlib.md5(open(os.path.join(cd, f), "rb").read()).hexdigest())
            except Exception:
                pass
existing = {f for f in os.listdir(D) if f.endswith(".jpg")}
idx = len(existing)

field = ["slug", "class_cn", "class_sci", "level", "occurrence_key", "record_scientificName",
         "media_url", "license", "rightsHolder", "file", "bytes"]
newrows = []
for key, sci in KEYS:
    offset = 0
    got = 0
    while got < 40:
        u = (f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}"
             f"&mediaType=still_image&limit=60&offset={offset}")
        r = get(u)
        if not r:
            break
        res = r.json().get("results", [])
        if not res:
            break
        for occ in res:
            for m in occ.get("media", []):
                if m.get("type") != "StillImage":
                    continue
                url = m.get("identifier")
                if not url:
                    continue
                rr = get(url, tries=2, timeout=30)
                if not rr or len(rr.content) < MIN_BYTES:
                    continue
                md5 = hashlib.md5(rr.content).hexdigest()
                if md5 in seen:
                    continue
                seen.add(md5)
                fn = f"karenia_{idx:04d}.jpg"; idx += 1
                with open(os.path.join(D, fn), "wb") as fp:
                    fp.write(rr.content)
                newrows.append({"slug": "karenia", "class_cn": "凯伦藻属", "class_sci": "Karenia(代表:米氏凯伦藻 K. mikimotoi)",
                                "level": "species", "occurrence_key": occ.get("key"),
                                "record_scientificName": occ.get("scientificName"),
                                "media_url": url, "license": m.get("license"),
                                "rightsHolder": m.get("rightsHolder"), "file": fn,
                                "bytes": len(rr.content), "md5": md5})
                got += 1
                time.sleep(0.3)
        offset += 60
        if offset > 240:
            break
    print(f"{sci}: 下载 {got} 张")

if newrows:
    w = csv.DictWriter(open(PROV, "a", encoding="utf-8-sig", newline=""), fieldnames=field, extrasaction="ignore")
    for row in newrows:
        w.writerow(row)
print("新增溯源行", len(newrows), "karenia 目录现有", len(os.listdir(D)), "个文件")
