# -*- coding: utf-8 -*-
# 组装宏观扩充提交物: 合并溯源CSV + 拷贝样例图 + README
import os, csv, shutil, collections

WEB = r'D:\train\_macro_scratch\web'
DEMO = r'D:\train\_submission_assets\macro_dataset_demo'
STAGE_MACRO = r'D:\train\submission\stage\数据集_宏观扩充'
os.makedirs(STAGE_MACRO, exist_ok=True)

# 1. 合并溯源 v1-v4
rows = []
for csvf in ['provenance.csv', 'provenance_v2.csv', 'provenance_v3.csv', 'provenance_v4.csv']:
    p = os.path.join(WEB, csvf)
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig') as f:
            rows.extend(list(csv.DictReader(f)))
print('溯源行数:', len(rows))
with open(os.path.join(STAGE_MACRO, 'provenance_macro.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['query', 'file', 'image_url', 'page_url', 'color', 'hyp', 'bytes'])
    w.writeheader(); w.writerows(rows)

# 2. 拷贝降采样图
cnt = 0
for split in ['train', 'monitor']:
    for cls in os.listdir(os.path.join(DEMO, split)):
        src_c = os.path.join(DEMO, split, cls)
        dst_c = os.path.join(STAGE_MACRO, split, cls)
        os.makedirs(dst_c, exist_ok=True)
        for fn in os.listdir(src_c):
            shutil.copyfile(os.path.join(src_c, fn), os.path.join(dst_c, fn))
            cnt += 1
print('拷贝图片:', cnt)

# 3. 各类统计
cc = collections.Counter()
for split in ['train', 'monitor']:
    for cls in os.listdir(os.path.join(STAGE_MACRO, split)):
        cc[cls] += len(os.listdir(os.path.join(STAGE_MACRO, split, cls)))
print('各类:', dict(cc))

# 4. README
readme = """# 宏观海面扩充数据集(弱监督·伪标签)

- **数量**:3065 张海面实拍图(train 2760 / monitor 305),五分类伪标签:夜光藻型 / 有毒甲藻型 / 硅藻型 / 绿潮 / 无赤潮
- **来源**:公开图片搜索(网页公开图),逐张记录来源 URL,见 provenance_macro.csv
- **打标方法**:可审计规则流(水色CV,见 fusion.py image_color_likelihood)→ 五分类伪标签;同类平局用 md5 确定性分配
- **诚实披露**:伪标签 = 规则流推定,非人工标注。监控集仅用于训练选优,不声明为最终准确率;真实效果以 25 张人工精选真实图(见 源码_macro_cnn/real_eval.json)验证,并与规则流基线并列报告
- **体积说明**:本目录为 256px/q85 降采样版(约 37MB)便于提交;原图 2560 版约 882MB 存于开发机,可按需提供
- **用途**:宏观 CNN(五分类)训练数据,作为融合引擎第三路证据(image_cnn_likelihood 钩子)备用;不作为人工标注验证集
"""
with open(os.path.join(STAGE_MACRO, 'README.md'), 'w', encoding='utf-8') as f:
    f.write(readme)
print('README 写入完成')
