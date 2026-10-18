# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, ssl, json, os

ctx = ssl.create_default_context()
KEY = open(r'D:\train\_roboflow_key.txt', encoding='utf-8').read().strip()
W, P = 'prowl-turdswerve-2024', 'red-tide'
out = []

def try_get(label, url, timeout=90):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            b = r.read()
            out.append('%s -> HTTP %s | CT=%s | %d bytes | head: %s' % (
                label, r.status, r.getheader('Content-Type'), len(b),
                b[:90].decode('utf-8', 'ignore').replace('\n', ' ')))
            return r.status, b
    except urllib.error.HTTPError as e:
        b = e.read()
        out.append('%s -> HTTP %s | %s' % (label, e.code, b[:120].decode('utf-8', 'ignore')))
        return e.code, b
    except Exception as e:
        out.append('%s -> ERR %s: %s' % (label, type(e).__name__, str(e)[:100]))
        return None, None

cands = [
    ('api v9 raw', 'https://api.roboflow.com/%s/%s/9?api_key=%s' % (W, P, KEY)),
    ('api v9 coco', 'https://api.roboflow.com/%s/%s/9/coco?api_key=%s' % (W, P, KEY)),
    ('api v9 yolo', 'https://api.roboflow.com/%s/%s/9/yolov8?api_key=%s' % (W, P, KEY)),
    ('api v1 coco', 'https://api.roboflow.com/%s/%s/1/coco?api_key=%s' % (W, P, KEY)),
    ('api v9 folder', 'https://api.roboflow.com/%s/%s/9/folder?api_key=%s' % (W, P, KEY)),
]
for lab, u in cands:
    st, b = try_get(lab, u)
    out.append('')
    if st == 200 and b and b[:3] == b'PK':
        zp = r'D:\train\_roboflow_dl\red-tide-%s.zip' % lab.split()[1]
        with open(zp, 'wb') as f:
            f.write(b)
        out.append('  !! 下载成功 -> %s (%.1f MB)' % (zp, os.path.getsize(zp) / 1e6))

with open(r'D:\train\_rf_try.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
