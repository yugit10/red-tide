# -*- coding: utf-8 -*-
# 完整浏览器头下载 Zenodo example_code.rar
import urllib.request, ssl, os, time, http.cookiejar

ctx = ssl.create_default_context()
dst = r'D:\train\_zenodo\example_code.rar'
os.makedirs(r'D:\train\_zenodo', exist_ok=True)

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'),
    ('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8'),
    ('Referer', 'https://zenodo.org/records/7359262'),
    ('Connection', 'keep-alive'),
]

# 先打页面拿 cookie
try:
    opener.open('https://zenodo.org/records/7359262', timeout=30).read()
except Exception as e:
    print('页面访问:', type(e).__name__, str(e)[:80])

url = 'https://zenodo.org/records/7359262/files/example_code.rar?download=1'
try:
    start = time.time()
    with opener.open(url, timeout=600) as r, open(dst, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
    print('OK %.1f MB in %.0fs' % (os.path.getsize(dst) / 1e6, time.time() - start))
except Exception as e:
    print('下载失败:', type(e).__name__, str(e)[:200])
    # 回退: 尝试 API 下载
    try:
        u2 = 'https://zenodo.org/api/records/7359262/files/example_code.rar?download=1'
        with opener.open(u2, timeout=600) as r, open(dst, 'wb') as f:
            while True:
                c = r.read(1 << 20)
                if not c:
                    break
                f.write(c)
        print('API回退 OK %.1f MB' % (os.path.getsize(dst) / 1e6))
    except Exception as e2:
        print('API回退失败:', type(e2).__name__, str(e2)[:150])
