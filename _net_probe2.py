# -*- coding: utf-8 -*-
import urllib.request, ssl, socket, sys

ctx = ssl.create_default_context()
ctx.check_hostname = True
urls = [
    'https://api.roboflow.com/',
    'https://universe.roboflow.com/prowl-turdswerve-2024/red-tide',
    'https://github.com/',
    'https://raw.githubusercontent.com/',
    'https://huggingface.co/',
    'https://api.gbif.org/v1/species?name=karenia',
]
out = []
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 research'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            body = r.read(400).decode('utf-8', 'ignore')
            out.append('%s\n  -> %s | %s' % (u, r.status, body[:220].replace('\n', ' ')))
    except Exception as e:
        out.append('%s\n  -> FAIL %s: %s' % (u, type(e).__name__, str(e)[:140]))
with open(r'D:\train\_net_probe2.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
