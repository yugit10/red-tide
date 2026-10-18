# -*- coding: utf-8 -*-
import urllib.request, ssl, json

ctx = ssl.create_default_context()
UA = {'User-Agent': 'Mozilla/5.0 research'}
out = []

def get(url, n=600):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'FAIL %s: %s' % (type(e).__name__, str(e)[:120])

# 1) HF datasets 里搜 red tide / harmful algae bloom / sea surface
for q in ['red tide', 'algae bloom', 'harmful algal', 'sea surface']:
    u = 'https://huggingface.co/api/datasets?search=%s&limit=8' % urllib.parse.quote(q)
    t = get(u)
    out.append('== HF datasets search: %s ==' % q)
    try:
        arr = json.loads(t)
        for d in arr[:8]:
            out.append('  %-60s 下载量: %s' % (d.get('id', '?'), d.get('downloads', '?')))
    except Exception:
        out.append('  ' + t[:300])
    out.append('')

# 2) Tick Tick Bloom 仓库的 data 目录
out.append('== Tick Tick Bloom repo (drivendataorg) ==')
u = 'https://api.github.com/repos/drivendataorg/tick-tick-bloom/contents/'
t = get(u, 1200)
try:
    for d in json.loads(t):
        out.append('  %-40s %s' % (d.get('name'), d.get('type')))
except Exception:
    out.append('  ' + t[:400])

# 3) GitHub 搜 red tide dataset 仓库
out.append('')
out.append('== GitHub search: red tide dataset ==')
u = 'https://api.github.com/search/repositories?q=red+tide+dataset&per_page=8'
t = get(u, 2000)
try:
    j = json.loads(t)
    for d in j.get('items', [])[:8]:
        out.append('  %-55s ★%s %s' % (d.get('full_name'), d.get('stargazers_count'), (d.get('description') or '')[:50]))
except Exception:
    out.append('  ' + t[:400])

out.append('')
out.append('== GitHub search: algae bloom image ==')
u = 'https://api.github.com/search/repositories?q=algae+bloom+image&per_page=8'
t = get(u, 2000)
try:
    j = json.loads(t)
    for d in j.get('items', [])[:8]:
        out.append('  %-55s ★%s %s' % (d.get('full_name'), d.get('stargazers_count'), (d.get('description') or '')[:50]))
except Exception:
    out.append('  ' + t[:400])

with open(r'D:\train\_dataset_search.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
