# -*- coding: utf-8 -*-
"""后台并行: iNaturalist 赤潮水华**现象照**搜索 + GBIF 海面相关记录摸底
只做统计与元数据探测, 不下载正文(bg 阶段先摸清上限与质量线索)
"""
import urllib.request, urllib.parse, ssl, json, time

ctx = ssl.create_default_context()
UA = {'User-Agent': 'Mozilla/5.0 research'}

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

out = []

# 1) iNaturalist: 赤潮水华现象观察(按文本/纬度搜索观察, 带照片)
for q in ['red tide water', 'harmful algal bloom', '赤潮']:
    u = ('https://api.inaturalist.org/v1/observations?q=%s&per_page=20&photos=true'
         % urllib.parse.quote(q))
    j = get_json(u)
    if '__err__' in j:
        out.append('iNat q=%s -> %s' % (q, j['__err__']))
        continue
    total = j.get('total_results', 0)
    rows = []
    for r in j.get('results', [])[:20]:
        taxon = (r.get('taxon') or {}).get('name', '?')
        pics = len(r.get('photos', []))
        loc = (r.get('location') or {})
        rows.append('%s(照片%d) %s' % (taxon, pics, 'loc' if loc else ''))
    out.append('iNat q=%s 总数=%d | %s' % (q, total, '; '.join(rows[:8])))
    out.append('')

# 2) iNaturalist: 福建/东海面观察(places 搜索福建 = 66482?) 先按 bbox 东海沿海
# 用 observations 的 southwest/ northeast 粗框 (福建沿海 bbox 近似)
bbox = '25.5,117.0,28.0,120.5'
u = ('https://api.inaturalist.org/v1/observations?per_page=20&photos=true'
     '&south=%s&west=%s&north=%s&east=%s&q=red%%20tide' % (
         '25.5', '117.0', '28.0', '120.5'))
j = get_json(u)
out.append('iNat 福建bbox red tide 总数=%s' % (j.get('total_results', j.get('__err__', '?'))))

# 3) GBIF: karenia/alexandrium 的 still_image 记录数上限(宏观不需要,但顺手摸底)
for name in ['Karenia mikimotoi', 'Noctiluca scintillans']:
    u = 'https://api.gbif.org/v1/species/match?name=' + urllib.parse.quote(name)
    j = get_json(u)
    key = j.get('usageKey')
    if key:
        u2 = ('https://api.gbif.org/v1/occurrence/search?taxonKey=%d&mediaType=still_image&limit=1'
              % key)
        j2 = get_json(u2)
        out.append('GBIF %s key=%s 带图记录数上限=%s' % (name, key, j2.get('count', '?')))
    else:
        out.append('GBIF %s match失败' % name)

with open(r'D:\train\_bg_probe.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('BG DONE')
