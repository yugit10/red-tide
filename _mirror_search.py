# -*- coding: utf-8 -*-
# 搜 Zenodo 藻华数据集的 GitHub / HF 镜像
import urllib.request, ssl, json

ctx = ssl.create_default_context()
out = []
def get(url, n=2500):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'FAIL %s' % str(e)[:100]

for q in ['coastal phytoplankton blooms 21st century', 'phytoplankton bloom dai song hu 2022',
          '藻华 数据集 zenodo', 'harmful algal bloom grid dataset']:
    u = 'https://api.github.com/search/repositories?q=%s&per_page=5' % urllib.parse.quote(q)
    t = get(u, 3000)
    out.append('== GitHub: %s ==' % q)
    try:
        j = json.loads(t)
        for d in j.get('items', [])[:5]:
            out.append('  %-50s ★%s | %s' % (d.get('full_name'), d.get('stargazers_count'), (d.get('description') or '')[:60]))
    except Exception:
        out.append('  ' + t[:200])
    out.append('')

# HF datasets 镜像
for q in ['phytoplankton bloom', 'algal bloom modis', 'coastal bloom']:
    u = 'https://huggingface.co/api/datasets?search=%s&limit=5' % urllib.parse.quote(q)
    t = get(u, 1500)
    out.append('== HF: %s ==' % q)
    try:
        for d in json.loads(t)[:5]:
            out.append('  %-50s dl=%s' % (d.get('id'), d.get('downloads')))
    except Exception:
        out.append('  ' + t[:200])
    out.append('')

with open(r'D:\train\_mirror_search.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
