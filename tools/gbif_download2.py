# -*- coding: utf-8 -*-
"""GBIF 属级/物种级赤潮藻影像下载器 v2
逐张记录溯源: 采集记录号 / 记录学名 / 影像URL / 许可 / 权利人 / 字节数
"""
import os, sys, time, json, csv, hashlib, urllib.request, urllib.parse

ROOT = r"D:\train\dataset_raw\gbif2"
os.makedirs(ROOT, exist_ok=True)
PROV = os.path.join(ROOT, "provenance.csv")
LOG  = os.path.join(ROOT, "download.log")

# slug, 中文名, 学名, 层级, 本次目标新增上限
# 其余类已下载完成(alexandrium28/skeletonema40/pseudonitzschia120/chaetoceros177/noctiluca171),
# 本轮只补关键缺口: 原甲藻属
TAXA = [
    ("prorocentrum",  "原甲藻属",     "Prorocentrum",          "genus",   260),
]

UA = {"User-Agent": "Mozilla/5.0 (train-research; contact student project)"}
MIN_BYTES = 5000
START = time.time()
TIME_BUDGET = 60 * 75   # 最多跑75分钟

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get(url, tries=2, timeout=25):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            if t == tries - 1:
                log(f"  GET fail {url[:70]} :: {e}")
                return None
            time.sleep(0.6)

def match_key(name):
    u = "https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(name)
    d = get(u)
    if not d:
        return None
    j = json.loads(d)
    return j.get("usageKey")

def resolve_prov_header():
    if not os.path.exists(PROV):
        with open(PROV, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow([
                "slug","class_cn","class_sci","level","occurrence_key",
                "record_scientificName","media_url","license","rightsHolder","file","bytes"])

def download_taxon(slug, cn, sci, level, cap):
    key = match_key(sci)
    if not key:
        log(f"[{cn}] 无法匹配 taxonKey, 跳过"); return 0
    outdir = os.path.join(ROOT, slug)
    os.makedirs(outdir, exist_ok=True)
    seen_url = set(); seen_hash = set()
    # 载入已下载的，避免重复
    idx = len([x for x in os.listdir(outdir) if x.endswith(".jpg")])
    saved = idx
    log(f"[{cn}] taxonKey={key} 已有{idx}张, 目标+{cap}")
    offset = 0; page = 300
    while saved - idx < cap and offset < 6000:
        if time.time() - START > TIME_BUDGET:
            log("  时间预算耗尽, 停止该物种"); break
        u = (f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}"
             f"&mediaType=still_image&limit={page}&offset={offset}")
        d = get(u)
        if not d:
            offset += page; continue
        j = json.loads(d)
        results = j.get("results", [])
        if not results:
            break
        for occ in results:
            if saved - idx >= cap: break
            okey = occ.get("key")
            rec_sci = occ.get("scientificName") or occ.get("species") or sci
            for m in occ.get("media", []):
                if saved - idx >= cap: break
                if str(m.get("type","")).lower() not in ("stillimage","still image"): continue
                mid = m.get("identifier")
                if not mid or mid in seen_url: continue
                seen_url.add(mid)
                blob = get(mid, tries=2, timeout=40)
                if not blob or len(blob) < MIN_BYTES: continue
                h = hashlib.md5(blob).hexdigest()
                if h in seen_hash: continue
                seen_hash.add(h)
                fn = f"{slug}_{saved:04d}.jpg"
                with open(os.path.join(outdir, fn), "wb") as fp:
                    fp.write(blob)
                with open(PROV, "a", newline="", encoding="utf-8-sig") as fp:
                    csv.writer(fp).writerow([slug,cn,sci,level,okey,rec_sci,mid,
                        m.get("license",""), m.get("rightsHolder",""), fn, len(blob)])
                saved += 1
        total = j.get("count", 0)
        offset += page
        if offset >= total: break
        time.sleep(0.3)
    log(f"[{cn}] 本次新增 {saved-idx} 张, 目录合计 {saved}")
    return saved

def main():
    resolve_prov_header()
    log("==== GBIF 下载器 v2 启动 ====")
    grand = 0
    for slug, cn, sci, level, cap in TAXA:
        if time.time() - START > TIME_BUDGET:
            log("全局时间预算耗尽, 提前结束"); break
        grand += download_taxon(slug, cn, sci, level, cap)
    log(f"==== 全部完成, 各类累计文件数合计 {grand} ====")

if __name__ == "__main__":
    main()
