# -*- coding: utf-8 -*-
import urllib.request, ssl, os, zipfile, json

ctx = ssl.create_default_context()
DL = r'D:\train\_roboflow_dl'
os.makedirs(DL, exist_ok=True)
link = 'https://app.roboflow.com/ds/0pIOv56UBf?key=KjArvmueRW'
zp = os.path.join(DL, 'red-tide-v1.zip')

try:
    req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=600, context=ctx) as r:
        b = r.read()
    with open(zp, 'wb') as f:
        f.write(b)
    print('zip: %.1f MB' % (os.path.getsize(zp) / 1e6))

    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        print('条目数:', len(names))
        # 顶层结构
        tops = sorted(set(n.split('/')[0] for n in names))
        print('顶层:', tops)
        # 图片文件数 & 标注
        imgs = [n for n in names if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        print('图片数:', len(imgs))
        for n in imgs[:12]:
            print('   ', n)
        # 写个清单
        with open(os.path.join(DL, 'filelist.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(names))
        # 解出前几张图 + annot 样例
        ext = os.path.join(DL, 'sample')
        os.makedirs(ext, exist_ok=True)
        cnt = 0
        for n in imgs:
            if cnt >= 8:
                break
            data = z.read(n)
            fn = n.replace('/', '_')
            with open(os.path.join(ext, fn), 'wb') as f:
                f.write(data)
            cnt += 1
        anns = [n for n in names if n.endswith('.json') or 'annot' in n.lower()]
        print('标注文件样例:', anns[:5])
        for a in anns[:1]:
            z.extract(a, ext)
except Exception as e:
    print('ERR', type(e).__name__, str(e)[:200])
print('DONE')
