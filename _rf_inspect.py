# -*- coding: utf-8 -*-
import zipfile, json, os
from PIL import Image

DL = r'D:\train\_roboflow_dl'
out = []

# 1) README
with zipfile.ZipFile(os.path.join(DL, 'red-tide-v1.zip')) as z:
    for rn in ['README.dataset.txt', 'README.roboflow.txt']:
        out.append('==== %s ====' % rn)
        try:
            t = z.read(rn).decode('utf-8', 'ignore')
            out.append(t[:2000])
        except Exception as e:
            out.append('ERR %s' % e)
        out.append('')

# 2) COCO 标注类别
with zipfile.ZipFile(os.path.join(DL, 'red-tide-v1.zip')) as z:
    ann = json.loads(z.read('train/_annotations.coco.json').decode('utf-8'))
    out.append('==== COCO 标注 ====')
    out.append('categories: %s' % json.dumps(ann.get('categories', []), ensure_ascii=False))
    imgs = ann.get('images', [])
    out.append('train images: %d' % len(imgs))
    if imgs:
        out.append('first img keys: %s' % list(imgs[0].keys()))
        out.append('first img: %s' % json.dumps({k: imgs[0][k] for k in ('file_name', 'width', 'height')}, ensure_ascii=False))

    # 3) 样例图的色彩统计(判断:海面蓝 / 珊瑚多彩 / 显微)
    out.append('')
    out.append('==== 样例图色彩统计 ====')
    ext = os.path.join(DL, 'sample')
    for fn in sorted(os.listdir(ext)):
        if not fn.lower().endswith('.jpg'):
            continue
        p = os.path.join(ext, fn)
        try:
            im = Image.open(p).convert('RGB')
            small = im.resize((64, 64))
            px = list(small.getdata())
            n = len(px)
            rs = sum(c[0] for c in px) / n
            gs = sum(c[1] for c in px) / n
            bs = sum(c[2] for c in px) / n
            # 饱和度估: max-min
            sat = sum(max(c) - min(c) for c in px) / n
            out.append('%s | %dx%d | RGB(%.0f,%.0f,%.0f) | 平均饱和度%.0f' % (
                fn, im.width, im.height, rs, gs, bs, sat))
        except Exception as e:
            out.append('%s ERR %s' % (fn, e))

with open(r'D:\train\_rf_inspect.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
