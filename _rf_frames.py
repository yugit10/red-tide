# -*- coding: utf-8 -*-
import zipfile, os, re, collections

DL = r'D:\train\_roboflow_dl'
zp = os.path.join(DL, 'red-tide-v1.zip')

with zipfile.ZipFile(zp) as z:
    names = z.namelist()
    imgs = [n for n in names if n.lower().endswith('.jpg')]

# 提取 GIF 源帧号: ezgif-frame-NNN
pat = re.compile(r'ezgif-frame-(\d+)')
frames = collections.Counter()
for n in imgs:
    m = pat.search(n)
    if m:
        frames[m.group(1)] += 1

out = []
out.append('图片总数: %d' % len(imgs))
out.append('独立 GIF 帧号数: %d' % len(frames))
out.append('每个帧号平均出现次数: %.1f (含3倍增强+3x3切块?)' % (len(imgs) / max(1, len(frames))))
out.append('')
out.append('出现最多的帧号(去重后画面重复度高):')
for k, v in frames.most_common(8):
    out.append('  frame-%s : %d 张' % (k, v))
# 帧号范围
nums = sorted(int(k) for k in frames)
if nums:
    out.append('帧号范围: %d ~ %d' % (nums[0], nums[-1]))

# 尺寸分布(从COCO json)
import json
with zipfile.ZipFile(zp) as z:
    ann = json.loads(z.read('train/_annotations.coco.json').decode('utf-8'))
    sizes = collections.Counter((i['width'], i['height']) for i in ann['images'])
out.append('')
out.append('train 图片尺寸分布:')
for s, c in sizes.most_common(8):
    out.append('  %dx%d : %d' % (s[0], s[1], c))
out.append('')
out.append('license 字段样例: %s' % ann['images'][0].get('license'))
out.append('date_captured 样例: %s' % ann['images'][0].get('date_captured'))

with open(r'D:\train\_rf_frames.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
