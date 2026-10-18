# -*- coding: utf-8 -*-
# v3: 聚焦补 toxic_dino + diatom 两类(其余类已足够), 目标总 3000+
import sys, os, re, time, csv, hashlib, io, threading
sys.path.insert(0, r'D:\train\_pylibs')
sys.path.insert(0, r'D:\train\tools')
import urllib.request, urllib.parse, ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as creq
from PIL import Image
import fusion

OUT = r'D:\train\_macro_scratch\web'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
ctx = ssl.create_default_context()

QUERIES = {
    'toxic_dino': ['brown sea water bloom', '褐色 海水 藻华', '红褐色 海水', 'brown tide ocean',
                   'karenia brevis bloom water', 'brown water algae bloom coast', '赤潮 褐色 海水',
                   'brown foam sea shore', 'harmful algal bloom brown water sea'],
    'diatom':     ['diatom bloom sea', '硅藻 水华 海', 'brown algae water surface', '骨条藻 水华',
                   'pseudo-nitzschia bloom', '海水 黄褐色 藻华', 'diatom algae sea water',
                   'brown phytoplankton sea', 'yellow brown sea water', '硅藻 爆发 海水',
                   'diatom red tide water', 'skeletonema bloom sea'],
}
MAX_PAGES = 4
CAP_CLASS = {'toxic_dino': 400, 'diatom': 400}
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
    top = max(fusion.HYP, key=lambda h: lik[h])
    tops = [h for h in fusion.HYP if lik[h] == lik[top]]
    if len(tops) == 1:
        return tops[0]
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

def download_and_label(job):
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
                if cnt[cls] >= CAP_CLASS[cls] or total >= CAP_TOTAL:
                    break
                try:
                    murls, purls = bing_search(q, first)
                except Exception:
                    continue
                for mu, pu in zip(murls, purls + [''] * len(murls)):
                    with lock:
                        if mu in seen_url or cnt[cls] >= CAP_CLASS[cls] or total >= CAP_TOTAL:
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
                if cls not in CAP_CLASS:
                    continue
                if cnt[cls] >= CAP_CLASS[cls] or total >= CAP_TOTAL:
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
    csvp = os.path.join(OUT, 'provenance_v3.csv')
    with open(csvp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','color','hyp','bytes'])
        w.writeheader(); w.writerows(rows)
    print('FINAL total=%d %s csv=%s' % (total, cnt, csvp), flush=True)

if __name__ == '__main__':
    main()
