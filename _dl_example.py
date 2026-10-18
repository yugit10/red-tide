# -*- coding: utf-8 -*-
# 下载 Zenodo example_code.rar (435MB) 到 D:\train\_zenodo\
import urllib.request, ssl, os, time

os.makedirs(r'D:\train\_zenodo', exist_ok=True)
url = 'https://zenodo.org/records/7359262/files/example_code.rar?download=1'
dst = r'D:\train\_zenodo\example_code.rar'
ctx = ssl.create_default_context()

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
start = time.time()
with urllib.request.urlopen(req, timeout=120, context=ctx) as r, open(dst, 'wb') as f:
    total = int(r.headers.get('Content-Length') or 0)
    got = 0
    while True:
        chunk = r.read(1 << 20)
        if not chunk:
            break
        f.write(chunk)
        got += len(chunk)
        el = time.time() - start
        if int(el) % 20 == 0 and got > 0:
            print('... %.1f MB / %s (%.1f MB/s)' % (got / 1e6, total / 1e6, got / 1e6 / max(el, 0.1)), flush=True)
print('DONE %.1f MB in %.0fs' % (os.path.getsize(dst) / 1e6, time.time() - start))
