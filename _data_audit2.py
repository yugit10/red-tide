# -*- coding: utf-8 -*-
import os, hashlib, json, collections, urllib.request, ssl, socket

out = []

# 1) 网络可达性(GBIF API / iNaturalist API)
out.append('==== 网络可达性 ====')
probes = [
    ('GBIF', 'https://api.gbif.org/v1/species?name=karenia'),
    ('iNaturalist', 'https://api.inaturalist.org/v1/taxa?q=Karenia'),
]
for name, url in probes:
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 research'})
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            body = r.read(200).decode('utf-8', 'ignore')
            out.append('%s: 可达 %s | 前200字节: %s' % (name, r.status, body[:200].replace('\n', ' ')))
    except Exception as e:
        out.append('%s: 不可达 -> %s: %s' % (name, type(e).__name__, str(e)[:120]))

# 2) gbif 第一轮 skeletonema_costatum 21 张 与 gbif2/skeletonema 40 张 的 md5 去重情况
out.append('')
out.append('==== gbif第一轮 vs gbif2 去重 ====')
def hashes(dirpath):
    d = {}
    for dp, _, fns in os.walk(dirpath):
        for f in fns:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                p = os.path.join(dp, f)
                d[p] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    return d
r1 = hashes(r'D:\train\dataset_raw\gbif\skeletonema_costatum')
r2 = hashes(r'D:\train\dataset_raw\gbif2\skeletonema')
set2 = set(r2.values())
new1 = {p: h for p, h in r1.items() if h not in set2}
out.append('gbif第一轮 skeletonema: %d 张, 其中与 gbif2 不重复: %d 张' % (len(r1), len(new1)))
# 顺带 noctiluca
n1 = hashes(r'D:\train\dataset_raw\gbif\noctiluca_scintillans')
n2 = hashes(r'D:\train\dataset_raw\gbif2\noctiluca')
setn2 = set(n2.values())
newn = {p: h for p, h in n1.items() if h not in setn2}
out.append('gbif第一轮 noctiluca: %d 张, 其中与 gbif2 不重复: %d 张' % (len(n1), len(newn)))

# 3) D:\algae_dataset\microscope 153 张: 目录结构/命名 -> 推测类别
out.append('')
out.append('==== D:\\algae_dataset\\microscope 结构 ====')
mic = r'D:\algae_dataset\microscope'
if os.path.isdir(mic):
    for dp, _, fns in sorted(os.walk(mic)):
        rel = os.path.relpath(dp, mic)
        nimg = sum(1 for f in fns if f.lower().endswith(('.jpg', '.jpeg', '.png')))
        if nimg:
            out.append('   %-20s %d' % (rel if rel != '.' else '(根)', nimg))
out.append('')
out.append('==== D:\\algae_dataset\\curated_micro 6 张 ====')
cur = r'D:\algae_dataset\curated_micro'
if os.path.isdir(cur):
    for f in sorted(os.listdir(cur)):
        out.append('   ' + f)

with open(r'D:\train\_data_audit2.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
