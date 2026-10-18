# -*- coding: utf-8 -*-
import os, json, collections

RAW = r'D:\train\dataset_raw'
D2 = r'D:\algae_dataset'

out = []
out.append('==== 现有训练/验证(藻类数据集) ====')
cm = json.load(open(r'D:\train\algae_dataset\class_map.json', encoding='utf-8'))
for slug, s in cm['summary'].items():
    out.append('%-16s raw=%d dedup=%d train=%d val=%d' % (slug, s['raw'], s['dedup'], s['train'], s['val']))

out.append('')
out.append('==== dataset_raw 各目录现存量(按顶层的类目录统计图片数) ====')
imgs = ('.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.bmp', '.webp')
for root_name in ['gbif', 'gbif2', 'cnki', 'macro', 'macro_probe']:
    base = os.path.join(RAW, root_name)
    if not os.path.isdir(base):
        out.append('%s: (不存在)' % root_name)
        continue
    cnt = collections.Counter()
    for dp, _, fns in os.walk(base):
        cls = os.path.relpath(dp, base).split(os.sep)[0]
        n = sum(1 for f in fns if f.lower().endswith(imgs))
        if n:
            cnt[cls] += n
    out.append('%s: 共 %d 张' % (root_name, sum(cnt.values())))
    for k, v in sorted(cnt.items()):
        out.append('   %-28s %d' % (k, v))

out.append('')
out.append('==== D:\\algae_dataset 是否存在 ====')
if os.path.isdir(D2):
    for root_name in sorted(os.listdir(D2)):
        p = os.path.join(D2, root_name)
        if os.path.isdir(p):
            n = sum(1 for _, _, fns in os.walk(p) for f in fns if f.lower().endswith(imgs))
            out.append('   %-30s %d 张' % (root_name, n))
else:
    out.append('   不存在')

with open(r'D:\train\_data_audit.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
