# -*- coding: utf-8 -*-
# 非海面负样本抓取 v2(增量版): 一个 query 页查到后立即提交下载, 实时出量有进度输出
import sys, os, re, time, csv, hashlib, io, threading, urllib.parse, random
sys.path.insert(0, r'D:\train\_pylibs')
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as creq
from PIL import Image

OUT = r'D:\train\_macro_scratch\nonsea'
os.makedirs(OUT, exist_ok=True)

QUERIES = {
    'grass':      ['green grass field photo', 'lawn texture photo', '草地上 风景照片'],
    'forest':     ['forest trees canopy photo', '树林 森林 风景'],
    'city':       ['city street buildings photo', '城市 街道 高楼 照片'],
    'indoor':     ['indoor living room photo', '室内 房间 客厅 照片'],
    'desk':       ['desk top view office photo', '书桌 桌面 俯拍 照片'],
    'document':   ['white paper document text photo', '白纸 文档 打印 照片'],
    'portrait':   ['person face portrait photo', '人物 人像 脸部 照片'],
    'desert':     ['desert sand dunes photo', '沙漠 沙丘 照片'],
    'snow':       ['snowfield white snow photo', '雪地 白雪 照片'],
    'farm':       ['agricultural field crops photo', '农田 麦田 稻田 照片'],
    'sky':        ['blue sky clouds photo', '蓝天 白云 照片'],
    'mountain':   ['mountain landscape rocks photo', '山峦 岩石 山景 照片'],
}
MAX_PAGES = 3
CAP_CLASS = 160
CAP_TOTAL = 1800
CONCURRENCY = 16
MIN_SIZE = 8000
MIN_SIDE = 64

lock = threading.Lock()
seen_url = set(); seen_md5 = set()
rows = []
cnt = {k: 0 for k in QUERIES}
total = 0

def load_existing():
    global total
    for f in os.listdir(OUT):
        if not f.endswith('.jpg'):
            continue
        try:
            h = hashlib.md5(open(os.path.join(OUT, f), 'rb').read()).hexdigest()
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
        r = creq.get(url, impersonate='chrome', timeout=20)
        if r.status_code != 200:
            return [], []
        html = r.text
    except Exception:
        return [], []
    return re.findall(r'murl&quot;:&quot;(.*?)&quot;', html), re.findall(r'purl&quot;:&quot;(.*?)&quot;', html)

def download(job):
    cls, mu, pu = job
    try:
        r = creq.get(mu, impersonate='chrome', timeout=25)
        if r.status_code != 200 or len(r.content) < MIN_SIZE:
            return None
        data = r.content
        im = Image.open(io.BytesIO(data)); im.load()
        if min(im.size) < MIN_SIDE:
            return None
        md5 = hashlib.md5(data).hexdigest()
    except Exception:
        return None
    return {'cls': cls, 'image_url': mu, 'page_url': pu, 'md5': md5, 'data': data, 'bytes': len(data)}

def main():
    global total
    load_existing()
    t0 = time.time()
    tasks = [(cls, q, first) for cls, qs in QUERIES.items() for q in qs
             for first in range(0, MAX_PAGES * 35, 35)]
    done_urls = 0
    with ThreadPoolExecutor(max_workers=12) as ex_search:
        futs = {}
        for cls, q, first in tasks:
            futs[ex_search.submit((lambda c, qq, f: (c, *bing_search(qq, f))), cls, q, first)] = cls
        # 每个 page 结果一到就并入下载队列(实时出量)
        dl_jobs = []
        for fut in as_completed(futs):
            try:
                cls, murls, purls = fut.result()
            except Exception:
                continue
            done_urls += 1
            with lock:
                for mu, pu in zip(murls, purls + [''] * len(murls)):
                    if mu in seen_url or cnt[cls] >= CAP_CLASS or total >= CAP_TOTAL:
                        continue
                    seen_url.add(mu)
                    dl_jobs.append((cls, mu, pu))
            if done_urls % 10 == 0:
                print(f'[urls {done_urls}/{len(tasks)} 已收集 {len(dl_jobs)} 个待下载]', flush=True)
    print('URL 收集完成:', len(dl_jobs), '个, 开始下载', flush=True)
    random.shuffle(dl_jobs)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex_dl:
        futs2 = {ex_dl.submit(download, j): j for j in dl_jobs[:2200]}
        for fut in as_completed(futs2):
            res = fut.result()
            if res is None:
                continue
            with lock:
                if res['md5'] in seen_md5:
                    continue
                cls = res['cls']
                if cnt[cls] >= CAP_CLASS or total >= CAP_TOTAL:
                    continue
                seen_md5.add(res['md5'])
                fn = '%s_%04d.jpg' % (cls, cnt[cls])
                cnt[cls] += 1; total += 1
                with open(os.path.join(OUT, fn), 'wb') as f:
                    f.write(res['data'])
                rows.append({'query': cls, 'file': fn, 'image_url': res['image_url'],
                             'page_url': res['page_url'], 'bytes': res['bytes']})
                if total and total % 50 == 0:
                    print(f'... total={total} 用时{time.time()-t0:.0f}s {cnt}', flush=True)
    csvp = os.path.join(OUT, 'provenance_nonsea.csv')
    with open(csvp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','bytes'])
        w.writeheader(); w.writerows(rows)
    print('FINAL total=%d %s' % (total, cnt), flush=True)

if __name__ == '__main__':
    main()
