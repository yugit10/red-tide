# -*- coding: utf-8 -*-
import urllib.request, ssl, json

ctx = ssl.create_default_context()
out = []
def get(url, n=2500):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'FAIL %s: %s' % (type(e).__name__, str(e)[:120])

u = 'https://api.github.com/repos/leejaehee089-star/redtide-dataset'
t = get(u)
out.append('== redtide-dataset 元信息 ==')
try:
    j = json.loads(t)
    if 'message' in j:
        out.append('  ' + str(j['message']))
    else:
        out.append('  %s' % (j.get('description') or '无描述'))
        out.append('  语言: %s | 大小KB: %s | 更新: %s' % (j.get('language'), j.get('size'), j.get('pushed_at')))
        out.append('  默认分支: %s' % j.get('default_branch'))
except Exception as e:
    out.append('  ' + t[:300])

# 根目录内容
br = 'main'
t = get('https://api.github.com/repos/leejaehee089-star/redtide-dataset/contents/?ref=main')
if t.startswith('FAIL') or (t.startswith('[') is False):
    br = 'master'
    t = get('https://api.github.com/repos/leejaehee089-star/redtide-dataset/contents/?ref=master')
out.append('')
out.append('== 根目录 (branch=%s) ==' % br)
try:
    arr = json.loads(t)
    if isinstance(arr, list):
        for d in arr[:30]:
            out.append('  %-35s %s' % (d.get('name'), d.get('type')))
    else:
        out.append('  ' + t[:400])
except Exception:
    out.append('  ' + t[:400])

with open(r'D:\train\_gh_probe.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
