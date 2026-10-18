# -*- coding: utf-8 -*-
# 用 curl_cffi 完整下载 zenodo 文件
import sys
sys.path.insert(0, r'D:\train\_pylibs')
from curl_cffi import requests
import os, time

dst = r'D:\train\_zenodo\example_code.rar'
os.makedirs(r'D:\train\_zenodo', exist_ok=True)
url = 'https://zenodo.org/records/7359262/files/example_code.rar?download=1'

start = time.time()
r = requests.get(url, impersonate='chrome', stream=True, timeout=600)
r.raise_for_status()
try:
    with open(dst, 'wb') as f:
        got = 0
        for chunk in r.iter_content(chunk_size=1 << 20):
            if chunk:
                f.write(chunk)
                got += len(chunk)
finally:
    r.close()
print('OK %d bytes (%.1f MB) in %.0fs' % (got, got / 1e6, time.time() - start))
