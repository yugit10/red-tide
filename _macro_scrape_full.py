# -*- coding: utf-8 -*-
# 全量宏观海面抓取: Bing 图像搜索(多类查询词) -> 并行下载 -> fusion 伪标签 -> 溯源 CSV
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

# 每个目标类: 一组查询词(中英混用)
QUERIES = {
    'noctiluca':  ['red tide sea', 'red tide ocean water', '赤潮 海面', '红潮 海水 照片', '赤潮 爆发 海',
                   'red water ocean bloom', 'sea surface red tide aerial', '夜光藻 赤潮'],
    'toxic_dino': ['brown sea water bloom', '褐色 海水 藻华', 'harmful algal bloom brown water',
                   '红褐色 海水', 'brown tide ocean', '鞭毛藻 水华 海'],
    'diatom':     ['diatom bloom sea', '硅藻 水华 海', 'brown algae water surface', '骨条藻 水华',
                   'phytoplankton bloom sea brown', '海水 变黄 藻'],
    'green_tide': ['green tide sea', '绿潮 海面', '浒苔 海面', 'green algae sea surface',
                   'green water bloom ocean', '海水 绿色 藻华 海面'],
    'none':       ['blue sea surface', '正常 海水 海面', 'ocean water surface blue', '大海 蓝色 海面 照片',
                   'clean ocean water surface', '平静 海面 蓝色'],
}
MAX_PAGES = 3            # 每查询翻页数(每页35)
CAP_PER_CLASS = 720      # 每类目标数
CAP_TOTAL = 3400         # 总目标(去重后)
CONCURRENCY = 12
MIN_SIZE = 4000          # 最小字节
MIN_SIDE = 200

lock = threading.Lock()
seen_url = set(); seen_md5 = set()
rows = []               # (image_url, page_url, query)
cnt = {k: 0 for k in QUERIES}
total = 0
stop = False

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
        hyp = max(fusion.HYP, key=lambda h: (lik[h], -fusion.HYP.index(h)))
    except Exception:
        return None
    return {'query': q, 'image_url': mu, 'page_url': pu, 'md5': md5, 'data': data,
            'color': lab, 'hyp': hyp, 'bytes': len(data)}

def collect_urls():
    """生成 (q, target_class, url, page_url) 任务, 直到各类接近上限"""
    jobs = []
    for cls, qs in QUERIES.items():
        if stop: break
        for q in qs:
            if stop: break
            for first in range(0, MAX_PAGES * 35, 35):
                if stop: break
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
                if cnt[cls] >= CAP_PER_CLASS: break
            if cnt[cls] >= CAP_PER_CLASS: break
    return jobs

def main():
    global total, stop
    jobs = collect_urls()
    print('collected', len(jobs), 'url jobs', flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(download_and_label, j): j for j in jobs}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None:
                continue
            with lock:
                md5 = res['md5']
                if md5 in seen_md5:
                    continue
                seen_md5.add(md5)
                cls = res['hyp']
                if cnt[cls] >= CAP_PER_CLASS or total >= CAP_TOTAL:
                    stop = True
                    continue
                fn = '%s_%04d.jpg' % (cls, cnt[cls])
                cnt[cls] += 1; total += 1
                with open(os.path.join(OUT, fn), 'wb') as f:
                    f.write(res['data'])
                rows.append({'query': res['query'], 'file': fn, 'image_url': res['image_url'],
                             'page_url': res['page_url'], 'color': res['color'], 'hyp': cls,
                             'bytes': res['bytes']})
            done += 1
            if total and total % 100 == 0:
                print('... total=%d %s' % (total, cnt), flush=True)
            if stop:
                break
    # 写溯源
    csv_path = os.path.join(OUT, 'provenance.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','color','hyp','bytes'])
        w.writeheader(); w.writerows(rows)
    print('FINAL total=%d stats=%s csv=%s' % (total, cnt, csv_path), flush=True)

if __name__ == '__main__':
    main()
