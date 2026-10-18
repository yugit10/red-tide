# -*- coding: utf-8 -*-
# 小规模测试: Bing 抓图 -> 下载 -> fusion 伪标签
import sys, os, re, time, json, csv, hashlib, io
sys.path.insert(0, r'D:\train\_pylibs')
sys.path.insert(0, r'D:\train\tools')
import urllib.request, urllib.parse, ssl
from curl_cffi import requests as creq
from PIL import Image
import fusion

ctx = ssl.create_default_context()
OUT = r'D:\train\_macro_scratch'
os.makedirs(OUT, exist_ok=True)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def bing_search(q, first=0, count=35):
    url = 'https://www.bing.com/images/async?q=%s&first=%d&count=%d' % (urllib.parse.quote(q), first, count)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        html = r.read().decode('utf-8', 'ignore')
    murls = re.findall(r'murl&quot;:&quot;(.*?)&quot;', html)
    purls = re.findall(r'purl&quot;:&quot;(.*?)&quot;', html)
    return murls, purls

def dl_img(url, timeout=30):
    try:
        r = creq.get(url, impersonate='chrome', timeout=timeout)
        if r.status_code != 200 or len(r.content) < 4000:
            return None
        return r.content
    except Exception:
        return None

def pseudo_label(pil_img):
    try:
        lab, lik, meta = fusion.image_color_likelihood(pil_img)
        hyp = max(fusion.HYP, key=lambda h: (lik[h], -fusion.HYP.index(h)))
        return lab, hyp, lik, meta
    except Exception as e:
        return None, None, None, {'err': str(e)}

rows = []
stats = {}
for q in ['red tide sea surface', '赤潮 海面']:
    try:
        murls, purls = bing_search(q, 0, 35)
    except Exception as e:
        print('search fail', q, e)
        continue
    print('query:', q, '->', len(murls), 'imgs')
    for i, (mu, pu) in enumerate(zip(murls, purls + ['' for _ in range(len(murls))])):
        data = dl_img(mu)
        if not data:
            continue
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            if min(im.size) < 200:
                continue
        except Exception:
            continue
        lab, hyp, lik, meta = pseudo_label(im)
        if lab is None:
            continue
        fn = '%s_%03d.jpg' % (re.sub(r'[^a-z0-9]', '_', lab), len(rows))
        with open(os.path.join(OUT, fn), 'wb') as f:
            f.write(data)
        rows.append({'query': q, 'file': fn, 'image_url': mu, 'page_url': pu,
                     'color': lab, 'hyp': hyp, 'bytes': len(data)})
        stats[hyp] = stats.get(hyp, 0) + 1
        if len(rows) >= 30:
            break
    if len(rows) >= 30:
        break

with open(os.path.join(OUT, 'provenance_test.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['query','file','image_url','page_url','color','hyp','bytes'])
    w.writeheader()
    w.writerows(rows)
print('TOTAL', len(rows), 'stats:', stats)
