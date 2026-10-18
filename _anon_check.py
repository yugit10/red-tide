# -*- coding: utf-8 -*-
import zipfile, re, os

PAT = re.compile(r'宁德师范|队长|13800000000|200705023|nick0000000|指导老师|指导教师|队长|(1[3-9]\d{9})')

def scan_office(path, label):
    out = ['== %s ==' % label]
    try:
        z = zipfile.ZipFile(path)
        hits = []
        for n in z.namelist():
            if not (n.endswith('.xml') or n.endswith('.rels')):
                continue
            try:
                data = z.read(n).decode('utf-8', errors='ignore')
            except Exception:
                continue
            for m in PAT.finditer(data):
                hits.append((n, m.group(0)))
        seen = set()
        for n, g in hits:
            k = (n, g)
            if k not in seen:
                seen.add(k)
                out.append('  %s -> %s' % (n, g))
        if not hits:
            out.append('  未发现个人信息关键词')
    except Exception as e:
        out.append('  读取失败: %s' % e)
    return '\n'.join(out)

r = []
r.append(scan_office(r'D:\train\materials\设计文档.docx', '设计文档.docx'))
r.append(scan_office(r'D:\train\materials\作品PPT.pptx', '作品PPT.pptx'))
r.append(scan_office(r'D:\train\藻种知识库.xlsx', '藻种知识库.xlsx'))
# CSV 纯文本也扫一遍(虽然 package.py 扫过)
for f in [r'D:\train\dataset_raw\gbif2\provenance.csv']:
    try:
        t = open(f, encoding='utf-8', errors='ignore').read()
        m = PAT.findall(t)
        r.append('== %s == 命中: %s' % (os.path.basename(f), m[:5] if m else '无'))
    except Exception as e:
        r.append('== %s == %s' % (os.path.basename(f), e))

with open(r'D:\train\_anon_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(r))
print('DONE')
