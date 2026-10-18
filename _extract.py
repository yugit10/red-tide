# -*- coding: utf-8 -*-
import fitz, docx, sys

io_path = sys.stdout

# ---- PDF ----
out = []
pdf = fitz.open(r'D:\train\_比赛通知.pdf')
out.append('PDF 页数: %d' % pdf.page_count)
out.append('=' * 30)
for i, page in enumerate(pdf):
    t = page.get_text().strip()
    out.append('----- 第 %d 页 -----' % (i + 1))
    out.append(t if t else '[本页无可提取文本,可能是扫描图]')
with open(r'D:\train\_notice_text.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

# ---- DOCX ----
d = docx.Document(r'D:\train\_执行计划书.docx')
out2 = []
out2.append('DOCX 段落数: %d' % len(d.paragraphs))
out2.append('=' * 30)
for p in d.paragraphs:
    if p.text.strip():
        out2.append(p.text)
for ti, table in enumerate(d.tables):
    out2.append('----- 表格 %d -----' % (ti + 1))
    for row in table.rows:
        out2.append(' | '.join(c.text.strip() for c in row.cells))
with open(r'D:\train\_plan_text.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out2))
print('DONE')
