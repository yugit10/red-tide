# -*- coding: utf-8 -*-
# 非海面负样本抓取: 12 类真实场景 (草地/森林/城市/室内/文档/人像/沙漠/雪地/农田/天空/街道/山峦)
import sys, os, re, time, csv, hashlib, io, threading, urllib.parse
sys.path.insert(0, r'D:\train\_pylibs')
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as creq
from PIL import Image

OUT = r'D:\train\_macro_scratch\nonsea'
os.makedirs(OUT, exist_ok=True)

QUERIES = {
    'grass':      ['green grass field', 'lawn texture', '草地 草坪'],
    'forest':     ['forest trees canopy', '树林 森林'],
    'city':       ['city street buildings', '城市 街道 高楼'],
    'indoor':     ['indoor room living room', '室内 房间 客厅'],
    'desk':       ['desk top view office', '书桌 桌面 俯拍'],
    'document':   ['white paper document text', '白纸 文档 打印'],
    'portrait':   ['person face portrait photo', '人物 人像 脸部'],
    'desert':     ['desert sand dunes', '沙漠 沙丘'],
    'snow':       ['snowfield white snow', '雪地 白雪'],
    'farm':       ['agricultural field crops', '农田 麦田 稻田'],
    'sky':        ['blue sky clouds', '蓝天 白云'],
    'mountain':   ['mountain landscape rocks', '山峦 岩石 山景'],
}
MAX_PAGES = 3
CAP_CLASS = 150
CAP_TOTAL = 1700
CONCURRENCY = 16
MIN_SIZE = 8000
MIN_SIDE = 64

lock = threading.Lock()
seen_url = set(); seen_md5 = set()
rows = []
cnt = {k: 0 for k in QUERIES}
total = 0
stop = False

def load_existing():
    global cnt, total
    for f in os.listdir(OUT):
        if not f.endswith('.jpg'):
            continue
        p = os.path.join(OUT, f)
        try:
            h = hashlib.md5(open(p, 'rb').read()).hexdigest()
            seen_md5.add(h)
        except Exception:
            pass
        cls = re.sub(r'_\d{4}\.jpg$', '', f)
        if cls in cnt:
            cnt[cls] += 1; total += 1
    print('existing: total=%d %s' % (total, cnt), flush=True)

def bing_search(q, first):
    url = 'https://www.bing.com/images/async?q=%s&first=%d&count=35' % (urllib.parse.quote(q), first)
    try:
        r = creq.get(url, impersonate='chrome', timeout=25)
        if r.status_code != 200:
            return [], []
        html = r.text
    except Exception:
        return [], []
    return re.findall(r'murl&quot;:&quot;(.*?)&quot;', html), re.findall(r'purl&quot;:&quot;(.*?)&quot;', html)

# query 字符串 -> 类名 (反向查找, 启动时构建一次)
QUERY_TO_CLS = {}
for _cls, _qs in QUERIES.items():
    for _q in _qs:
        QUERY_TO_CLS[_q] = _cls

def download(job):
    q, mu, pu = job
    try:
        r = creq.get(mu, impersonate='chrome', timeout=30)
        if r.status_code != 200 or len(r.content) < MIN_SIZE:
            return None
        data = r.content
        im = Image.open(io.BytesIO(data)); im.load()
        if min(im.size) < MIN_SIDE:
            return None
        md5 = hashlib.md5(data).hexdigest()
    except Exception:
        return None
    return {'query': q, 'image_url': mu, 'page_url': pu, 'md5': md5, 'data': data, 'bytes': len(data)}

def collect_urls():
    """并行抓取所有 URL 页, 再统一按类名去重入队."""
    tasks = []
    for cls, qs in QUERIES.items():
        for q in qs:
            for first in range(0, MAX_PAGES * 35, 35):
                tasks.append((cls, q, first))
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(lambda cq: (cq[0], *bing_search(cq[1], cq[2])), t): t for t in tasks}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception:
                pass
    jobs = []
    for cls, murls, purls in results:
        for mu, pu in zip(murls, purls + [''] * len(murls)):
            with lock:
                if mu in seen_url or cnt[cls] >= CAP_CLASS or total >= CAP_TOTAL:
                    continue
                seen_url.add(mu)
            jobs.append((cls, mu, pu))
    return jobs


def main():
    global total, stop
    load_existing()
    jobs = collect_urls()
    print('collected', len(jobs), 'url jobs', flush=True)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(download, j): j for j in jobs}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None:
                continue
            with lock:
                if res['md5'] in seen_md5:
                    continue
                cls = res['query']  # collect_urls 传入的即类名
                if cnt[cls] >= CAP_CLASS or total >= CAP_TOTAL:
                    continue

def main():
    global total, stop
    load_existing()
    jobs = collect_urls()
    print('collected', len(jobs), 'url jobs', flush=True)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(download, j): j for j in jobs}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None:
                continue
            with lock:
                if res['md5'] in seen_md5:
                    continue
                cls = QUERY_TO_CLS.get(res['query'])
                if cls is None:
                    continue
                if cnt[cls] >= CAP_CLASS or total >= CAP_TOTAL:
                    continue
                seen_md5.add(res['md5'])
                fn = '%s_%04d.jpg' % (cls, cnt[cls])
                cnt[cls] += 1; total += 1
                with open(os.path.join(OUT, fn), 'wb') as f:
                    f.write(res['data'])
                rows.append({'query': res['query'], 'file': fn, 'image_url': res['image_url'],
                             'page_url': res['page_url'], 'bytes': res['bytes']})
                if total and total % 50 == 0:
                    print('... total=%d %s' % (total, cnt), flush=True)
    csvp = os.path.join(OUT, 'provenance_nonsea.csv')
    with open(csvp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','bytes'])
        w.writeheader(); w.writerows(rows)
    print('FINAL total=%d %s csv=%s' % (total, cnt, csvp), flush=True)

if __name__ == '__main__':
    main()
