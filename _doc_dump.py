# -*- coding: utf-8 -*-
import docx, io, sys

d = docx.Document(r'D:\train\materials\设计文档.docx')
paras = [p for p in d.paragraphs if p.text.strip()]
buf = []
for i, p in enumerate(paras[:170], 1):
    st = p.style.name if p.style else ''
    t = p.text.strip().replace('\n', '\\n')
    tag = '[H]' if st.lower().startswith(('heading', '标题')) else '   '
    buf.append('%3d %s %s' % (i, tag, t[:90]))
with open(r'D:\train\_doc_dump.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(buf))
print('DONE')

