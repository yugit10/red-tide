# -*- coding: utf-8 -*-
"""从GBIF按物种批量下载带物种标注的图像，并记录来源(provenance)。
用法: D:\Python310\python.exe -X utf8 gbif_download.py
输出: D:\train\dataset_raw\gbif\<species_slug>\*.jpg + gbif_provenance.csv
"""
import json, os, csv, time, urllib.request, urllib.parse

SPECIES = {
    'skeletonema_costatum':   ('Skeletonema costatum',   3193374, 200),
    'noctiluca_scintillans':  ('Noctiluca scintillans',  8063862, 300),
    'prorocentrum_donghaiense': ('Prorocentrum donghaiense', 7418015, 200),
    'alexandrium_tamarense':  ('Alexandrium tamarense',  7632200, 200),
    'chaetoceros_curvisetus': ('Chaetoceros curvisetus', 4275417, 200),
    'pseudo_nitzschia_pungens': ('Pseudo-nitzschia pungens', 2628756, 200),
}
ROOT = r'D:\train\dataset_raw\gbif'
UA = {'User-Agent': 'train-edu-project/1.0 (student competition; contact: 200705023@qq.com)'}
OK_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp')


def get(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    rows = []
    for slug, (name, key, cap) in SPECIES.items():
        d = os.path.join(ROOT, slug)
        os.makedirs(d, exist_ok=True)
        n = 0
        offset = 0
        while n < cap and offset <= 2000:
            u = 'https://api.gbif.org/v1/occurrence/search?' + urllib.parse.urlencode(
                {'taxonKey': key, 'mediaType': 'still_image', 'limit': 100, 'offset': offset})
            try:
                data = json.loads(get(u, timeout=30))
            except Exception as e:
                print(slug, 'search error', e, flush=True)
                break
            res = data.get('results', [])
            if not res:
                break
            for occ in res:
                for media in occ.get('media', []):
                    ident = media.get('identifier')
                    if not ident or not ident.startswith('http'):
                        continue
                    ext = os.path.splitext(urllib.parse.urlparse(ident).path)[1].lower()
                    if ext not in OK_EXT:
                        ext = '.jpg'
                    fn = f'{slug}_{n:04d}{ext}'
                    try:
                        blob = get(ident)
                        if len(blob) < 5000:  # 过小: 缩略图或错误页
                            continue
                        with open(os.path.join(d, fn), 'wb') as f:
                            f.write(blob)
                        rows.append([slug, name, occ.get('key'), ident,
                                     media.get('license', ''), media.get('rightsHolder', ''),
                                     fn, len(blob)])
                        n += 1
                        if n >= cap:
                            break
                    except Exception:
                        continue
            offset += 100
            time.sleep(0.5)
        print(slug, 'downloaded', n, flush=True)
    prov = os.path.join(ROOT, 'gbif_provenance.csv')
    with open(prov, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['slug', 'species', 'occurrence_key', 'media_url', 'license',
                    'rights_holder', 'file', 'bytes'])
        w.writerows(rows)
    print('DONE total', len(rows), flush=True)


if __name__ == '__main__':
    main()
