# -*- coding: utf-8 -*-
"""iNaturalist 现象照精细探针: 血红哈卡藻(Akashiwo) + 水华事件观察(Life/无鉴定)
输出: 观察ID / 物种 / 照片数 / 前几张照片URL / 时间地点 —— 供人工目视精选
"""
import urllib.request, urllib.parse, ssl, json, time, os

ctx = ssl.create_default_context()
UA = {'User-Agent': 'Mozilla/5.0 research'}
out = []

def get_json(url, retries=2):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return json.loads(r.read().decode('utf-8', 'ignore'))
        except Exception as e:
            if i == retries - 1:
                return {'__err__': '%s: %s' % (type(e).__name__, str(e)[:100])}
            time.sleep(0.8)
    return {}

def dump_obs(title, url, maxn=30):
    j = get_json(url)
    out.append('== %s ==' % title)
    if '__err__' in j:
        out.append('  ERR ' + j['__err__'])
        out.append('')
        return
    out.append('  总数: %s' % j.get('total_results', '?'))
    for r in j.get('results', [])[:maxn]:
        taxon = (r.get('taxon') or {}).get('name') or '(Life/未鉴定)'
        nph = len(r.get('photos', []))
        if nph == 0:
            continue
        first_urls = []
        for ph in r.get('photos', [])[:3]:
            u = (ph.get('url') or '').replace('square', 'medium')
            first_urls.append(u)
        place = ''
        loc = r.get('location')
        if loc:
            try:
                parts = str(loc).split(',')
                if len(parts) == 2:
                    place = ' %.2f,%.2f' % (float(parts[0]), float(parts[1]))
            except Exception:
                place = ' ' + str(loc)[:20]
        out.append('  obs=%s | %s | 照片%d | %s%s' % (
            r.get('id'), taxon, nph, (r.get('observed_on') or '?'), place))
        for u in first_urls:
            out.append('      ' + u)
    out.append('')

# 1) Akashiwo 属(血红哈卡藻)带照片观察 —— 最可能是赤潮现场
u = ('https://api.inaturalist.org/v1/observations?taxon_id=244182&per_page=50'
     '&photos=true&quality_grade=any&order=desc&order_by=created_at')
dump_obs('Akashiwo sanguinea (血红哈卡藻) 带照片', u)

# 2) 关键词 harmful algal bloom + 照片>=5 且未鉴定(Life) —— 水华事件现场照
u = ('https://api.inaturalist.org/v1/observations?q=%s&per_page=50&photos=true'
     '&taxon_rank=life&order=desc&order_by=created_at' % urllib.parse.quote('red tide water'))
dump_obs('q="red tide water" 未鉴定 + 带照片', u)

# 3) 福建近岸 bbox 内 red tide, 照片多者优先
u = ('https://api.inaturalist.org/v1/observations?q=%s&per_page=50&photos=true'
     '&south=23.5&west=116.5&north=30.5&east=121.5&order=desc&order_by=created_at'
     % urllib.parse.quote('red tide'))
dump_obs('东南沿海 bbox + red tide', u)

with open(r'D:\train\_inat_probe.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
