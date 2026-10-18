# -*- coding: utf-8 -*-
import urllib.request, ssl, json

ctx = ssl.create_default_context()
out = []
HDRS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/126.0 Safari/537.36'),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://zenodo.org/',
}
def tryzen(host):
    u = '%s/api/records/7359262' % host
    try:
        req = urllib.request.Request(u, headers=HDRS)
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            j = json.loads(r.read().decode('utf-8'))
        files = j.get('files', [])
        total = sum(f.get('size', 0) for f in files) / 1e6
        out.append('%s OK: title=%s | %d个文件 合计%.1f MB' % (
            host, (j.get('metadata', {}).get('title', '?') or '?')[:60], len(files), total))
        for f in files[:20]:
            out.append('   %s (%.1f MB)' % (f.get('key'), f.get('size', 0) / 1e6))
        return True
    except Exception as e:
        out.append('%s FAIL %s: %s' % (host, type(e).__name__, str(e)[:120]))
        return False

tryzen('https://zenodo.org')
tryzen('https://zenodo.org/api')
tryzen('https://zenodo.org/records/7359262')
# 也试 records 的另一下载形式
try:
    req = urllib.request.Request('https://zenodo.org/api/records/7359262/files', headers=HDRS)
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        out.append('files端点: %s' % r.read()[:200].decode('utf-8', 'ignore'))
except Exception as e:
    out.append('files端点 FAIL: %s' % str(e)[:100])

with open(r'D:\train\_zenodo_retry.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
