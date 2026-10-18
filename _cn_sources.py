# -*- coding: utf-8 -*-
import urllib.request, ssl, json, socket

ctx = ssl.create_default_context()
out = []
def probe(label, fn):
    try:
        out.append('%s: OK %s' % (label, fn()))
    except Exception as e:
        out.append('%s: FAIL %s: %s' % (label, type(e).__name__, str(e)[:140]))

# 1) Zenodo 全球1km藻华数据集: 记录元数据 + 文件清单(这个决定它的可用性)
def zenodo():
    req = urllib.request.Request('https://zenodo.org/api/records/7359262',
                                 headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        j = json.loads(r.read().decode('utf-8'))
    files = j.get('files', [])
    lines = ['title: %s' % (j.get('metadata', {}).get('title', '?'))]
    total = 0
    for f in files[:25]:
        sz = f.get('size', 0)
        total += sz
        lines.append('  %s  (%.1f MB)' % (f.get('key'), sz / 1e6))
    lines.append('  共 %d 个文件, 前25个合计 %.1f MB' % (len(files), total / 1e6))
    return ' | '.join(lines)
probe('Zenodo 7359262', zenodo)

# 2) NSOAS 官方 FTP(黄东海50米水色)
def ftp():
    import ftplib
    ftp = ftplib.FTP('osdds-ftp.nsoas.org.cn')
    ftp.login('coloruser', 'SZKfc%Lwxc3d')
    lst = ftp.nlst()
    ftp.quit()
    return '登录成功, 根目录条目: %s' % lst[:15]
probe('NSOAS FTP', ftp)

# 3) NCDC 藻华数据集元数据页
def ncdc():
    req = urllib.request.Request(
        'http://www.ncdc.ac.cn/portal/metadata/6cca03e5-3c71-498a-92bd-fe3a8395059f',
        headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return 'HTTP %s %d bytes' % (r.status, len(r.read()))
probe('NCDC 藻华数据集', ncdc)

# 4) NODA 漂浮藻灾害
def noda():
    import ssl as ssl2
    ctx2 = ssl2.create_default_context()
    ctx2.check_hostname = False
    ctx2.verify_mode = ssl2.CERT_NONE
    req = urllib.request.Request(
        'https://noda.ac.cn/aircas/datasharing/datasetDetails/68786e2c4770616ad5428242',
        headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx2) as r:
        return 'HTTP %s %d bytes' % (r.status, len(r.read()))
probe('NODA 漂浮藻', noda)

with open(r'D:\train\_cn_sources.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
