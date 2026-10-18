# -*- coding: utf-8 -*-
# 合并 macro 溯源 v1-v4 -> _submission_assets/macro/provenance_macro.csv
import os, csv

WEB = r'D:\train\_macro_scratch\web'
OUTDIR = r'D:\train\_submission_assets\macro'
os.makedirs(OUTDIR, exist_ok=True)

rows = []
for csvf in ['provenance.csv', 'provenance_v2.csv', 'provenance_v3.csv', 'provenance_v4.csv']:
    p = os.path.join(WEB, csvf)
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig') as f:
            rows.extend(list(csv.DictReader(f)))
print('溯源行数:', len(rows))
with open(os.path.join(OUTDIR, 'provenance_macro.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['query', 'file', 'image_url', 'page_url', 'color', 'hyp', 'bytes'])
    w.writeheader()
    w.writerows(rows)
print('OK ->', os.path.join(OUTDIR, 'provenance_macro.csv'))
