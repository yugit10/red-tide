# -*- coding: utf-8 -*-
# v2: 续跑去重 + diatom 平局修复 + 更多查询词, 目标 3000+
import sys, os, re, time, json, csv, hashlib, io, threading
sys.path.insert(0, r'D:\train\_pylibs')
sys.path.insert(0, r'D:\train\tools')
import urllib.request, urllib.parse, ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as creq
from PIL import Image
import fusion

OUT = r'D:\train\_macro_scratch\web'
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
ctx = ssl.create_default_context()

QUERIES = {
    'noctiluca':  ['red tide sea', 'red tide ocean water', '赤潮 海面', '红潮 海水 照片', '赤潮 爆发 海',
                   'red water ocean bloom', 'sea surface red tide aerial', '夜光藻 赤潮',
                   'red tide beach water', '红色 海水 藻华', 'algal bloom red water shoreline',
                   'red tide satellite ocean'],
    'toxic_dino': ['brown sea water bloom', '褐色 海水 藻华', 'harmful algal bloom brown water',
                   '红褐色 海水', 'brown tide ocean', '鞭毛藻 水华 海', 'karenia brevis water',
                   'brown water algae bloom coast', '赤潮 褐色 海水 照片'],
    'diatom':     ['diatom bloom sea', '硅藻 水华 海', 'brown algae water surface', '骨条藻 水华',
                   'phytoplankton bloom sea brown', '海水 变黄 藻', 'diatom algae water bloom',
                   'pseudo-nitzschia bloom sea', '海水 黄褐色 藻华 照片'],
    'green_tide': ['green tide sea', '绿潮 海面', '浒苔 海面', 'green algae sea surface',
                   'green water bloom ocean', '海水 绿色 藻华 海面', 'green algae bloom coast',
                   '海面 绿藻', 'green sea water algae'],
    'none':       ['blue sea surface', '正常 海水 海面', 'ocean water surface blue', '大海 蓝色 海面 照片',
                   'clean ocean water surface', '平静 海面 蓝色', 'blue ocean water waves',
                   '深海 蓝色 海面', 'blue water sea texture'],
}
MAX_PAGES = 3
CAP_PER_CLASS = 900
CAP_TOTAL = 3600
CONCURRENCY = 14
MIN_SIZE = 4000
MIN_SIDE = 200

lock = threading.Lock()
seen_url = set(); seen_md5 = set()
rows = []
cnt = {k: 0 for k in QUERIES}
total = 0
stop = False

def lab_hyp(lab, lik, md5):
    """伪标签: 平局用 md5 哈希分配, 避免 diatom 系统性饿死"""
    top = max(fusion.HYP, key=lambda h: lik[h])
    tops = [h for h in fusion.HYP if lik[h] == lik[top]]
    if len(tops) == 1:
        return tops[0]
    # 平局: 用 md5 前2字节做确定性分配
    idx = int(md5[:2], 16)
    return tops[idx % len(tops)]

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
        # 类名 = 去掉尾部 _NNNN.jpg
        cls = re.sub(r'_\d{4}\.jpg$', '', f)
        if cls in cnt:
            cnt[cls] += 1; total += 1
    print('existing: total=%d %s' % (total, cnt), flush=True)

def bing_search(q, first):
    url = 'https://www.bing.com/images/async?q=%s&first=%d&count=35' % (urllib.parse.quote(q), first)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            html = r.read().decode('utf-8', 'ignore')
    except Exception:
        return [], []
    murls = re.findall(r'murl&quot;:&quot;(.*?)&quot;', html)
    purls = re.findall(r'purl&quot;:&quot;(.*?)&quot;', html)
    return murls, purls

def download_and_label(job):
    q, mu, pu = job
    try:
        r = creq.get(mu, impersonate='chrome', timeout=30)
        if r.status_code != 200 or len(r.content) < MIN_SIZE:
            return None
        data = r.content
        im = Image.open(io.BytesIO(data))
        im.load()
        if min(im.size) < MIN_SIDE:
            return None
        md5 = hashlib.md5(data).hexdigest()
        lab, lik, meta = fusion.image_color_likelihood(im)
        hyp = lab_hyp(lab, lik, md5)
    except Exception:
        return None
    return {'query': q, 'image_url': mu, 'page_url': pu, 'md5': md5, 'data': data,
            'color': lab, 'hyp': hyp, 'bytes': len(data)}

def collect_urls():
    jobs = []
    for cls, qs in QUERIES.items():
        if stop: break
        for q in qs:
            if stop: break
            for first in range(0, MAX_PAGES * 35, 35):
                if stop: break
                if cnt[cls] >= CAP_PER_CLASS or total >= CAP_TOTAL:
                    break
                try:
                    murls, purls = bing_search(q, first)
                except Exception:
                    continue
                for mu, pu in zip(murls, purls + [''] * len(murls)):
                    with lock:
                        if mu in seen_url or cnt[cls] >= CAP_PER_CLASS or total >= CAP_TOTAL:
                            continue
                        seen_url.add(mu)
                    jobs.append((q, mu, pu))
    return jobs

def main():
    global total, stop
    load_existing()
    jobs = collect_urls()
    print('collected', len(jobs), 'url jobs', flush=True)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(download_and_label, j): j for j in jobs}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None:
                continue
            with lock:
                if res['md5'] in seen_md5:
                    continue
                cls = res['hyp']
                if cnt[cls] >= CAP_PER_CLASS or total >= CAP_TOTAL:
                    continue
                seen_md5.add(res['md5'])
                fn = '%s_%04d.jpg' % (cls, cnt[cls])
                cnt[cls] += 1; total += 1
                with open(os.path.join(OUT, fn), 'wb') as f:
                    f.write(res['data'])
                rows.append({'query': res['query'], 'file': fn, 'image_url': res['image_url'],
                             'page_url': res['page_url'], 'color': res['color'], 'hyp': cls,
                             'bytes': res['bytes']})
                if total and total % 100 == 0:
                    print('... total=%d %s' % (total, cnt), flush=True)
    csvp = os.path.join(OUT, 'provenance_v2.csv')
    with open(csvp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','color','hyp','bytes'])
        w.writeheader(); w.writerows(rows)
    print('FINAL total=%d %s csv=%s' % (total, cnt, csvp), flush=True)

if __name__ == '__main__':
    main()
