# -*- coding: utf-8 -*-
import pymupdf, os

os.makedirs(r'D:\train\_notice_pages', exist_ok=True)
pdf = pymupdf.open(r'D:\train\_比赛通知.pdf')
for i, page in enumerate(pdf):
    pix = page.get_pixmap(dpi=180)
    out = r'D:\train\_notice_pages\page_%02d.png' % (i + 1)
    pix.save(out)
    print(i + 1, page.rect, pix.width, pix.height)
print('TOTAL', pdf.page_count)
