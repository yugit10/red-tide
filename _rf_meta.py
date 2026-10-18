# -*- coding: utf-8 -*-
import urllib.request, ssl, json, os, time

ctx = ssl.create_default_context()
KEY = open(r'D:\train\_roboflow_key.txt', encoding='utf-8').read().strip()
W, P = 'prowl-turdswerve-2024', 'red-tide'
out = []

def get(url, timeout=90):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

# 1) v9 raw 元数据全文 —— 找 download URL
st, b = get('https://api.roboflow.com/%s/%s/9?api_key=%s' % (W, P, KEY))
out.append('v9 raw: HTTP %s' % st)
try:
    j = json.loads(b)
    out.append(json.dumps(j, ensure_ascii=False, indent=1)[:2500])
except Exception:
    out.append(b[:1500].decode('utf-8', 'ignore'))

out.append('')
# 2) v1 coco 200 的返回 —— 找直链
st, b = get('https://api.roboflow.com/%s/%s/1/coco?api_key=%s' % (W, P, KEY))
out.append('v1 coco: HTTP %s' % st)
try:
    j = json.loads(b)
    out.append(json.dumps(j, ensure_ascii=False, indent=1)[:2500])
except Exception:
    out.append(b[:1500].decode('utf-8', 'ignore'))

with open(r'D:\train\_rf_meta.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
