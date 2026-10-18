# -*- coding: utf-8 -*-
"""_pack_v5.py —— 直接由 sources 组装提交 zip(不经 stage, 输出到可写目录)
结构:
  作品PPT.pptx / 设计文档.docx
  源码/(.py + 藻种知识库.xlsx + make_doc.py 等)
  模型/(best.ckpt, train_log.json, class_map.json)
  数据集/(train/val 224 图 + provenance.csv)
  模型_宏观CNN/(best.ckpt, train_log.json, class_map.json, real_eval.json)
  数据集_宏观扩充/(256px 降采样 train/monitor + provenance_macro.csv + README.md)
  演示说明.txt
输出: D:\\train\\_submission_assets\\学校名称-海洋微藻智能识别与赤潮风险提示工具-队长-13800000000.zip
"""
import os, zipfile, re, sys

ROOT = r"D:\train"
MAT = os.path.join(ROOT, "materials")
TOOLS = os.path.join(ROOT, "tools")
MODEL = os.path.join(ROOT, "model")
DATA = os.path.join(ROOT, "algae_dataset")
GBIF = os.path.join(ROOT, "dataset_raw", "gbif2")
MACRO_MODEL = os.path.join(ROOT, "model_macro")
MACRO_DEMO = r"D:\train\_submission_assets\macro_dataset_demo"
MACRO_CSV = os.path.join(ROOT, "_submission_assets", "macro")  # provenance_macro.csv 放这里
OUTDIR = r"D:\train\_submission_assets"
os.makedirs(OUTDIR, exist_ok=True)

ZIPNAME = "学校名称-海洋微藻智能识别与赤潮风险提示工具-队长-13800000000.zip"
ZPATH = os.path.join(OUTDIR, ZIPNAME)
if os.path.exists(ZPATH):
    os.remove(ZPATH)

def add(z, src, arc):
    if not os.path.exists(src):
        print("!! 缺失:", src); return
    if os.path.isdir(src):
        for dp, _, fns in os.walk(src):
            for fn in fns:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, src)
                z.write(full, os.path.join(arc, rel))
    else:
        z.write(src, arc)

demo = """海洋微藻智能识别与赤潮风险提示工具 —— 演示与运行说明(双分支)

一、环境
  Python 3.10;依赖:mindspore、mindcv、streamlit、pillow、openpyxl、numpy(<2)、matplotlib、python-pptx、python-docx

二、运行演示(推荐)
  1) 将 模型/best.ckpt、模型/class_map.json 与 源码/藻种知识库.xlsx 放到对应路径(默认 D:\\train\\...),
     或直接修改 app.py / predict.py 顶部的路径常量;
  2) 进入 源码/ 目录,执行:  streamlit run app.py
  3) 浏览器访问 http://localhost:8501 ,默认在「拍海面查风险(渔民用)」Tab:
     上传一张海面现状照片 → 图像双证据贝叶斯融合(规则流水色CV为主 × 宏观CNN辅助)
     输出最可能致灾类群、赤潮风险等级、风险说明,并给出四级预警信号(红/橙/黄/蓝)+ 预警指数 + 分级响应措施,
     同时展示后验概率与证据链;纯图像判定,无需填写任何问卷;宏观分支无需训练、秒开;
  4) 切到「显微照片(化验室人员用)」Tab 上传显微照片 → MobileNetV3-Small(MindSpore)
     输出识别类别 + 置信度 + Top-3 + 固有风险等级 + 四级预警信号 + 毒素/生态/养殖影响/爆发规律/监测优先级;
     支持多张批量上传并输出汇总表。

三、复现训练(显微分支)
  python prepare_data.py     # 由 数据集/ 或原始 GBIF 影像重建 train/val
  python train.py --epochs 30
  验证集准确率约 95.4%(详见 模型/train_log.json)。

四、命令行推理
  显微:python predict.py <图像或目录>
  宏观融合:python -c "from PIL import Image; import fusion; print(fusion.fuse(fusion.image_color_likelihood(Image.open('<海面照>'))[1], {}))"

五、数据真实性
  数据集/provenance.csv 逐张记录:类别、GBIF 采集记录号、记录学名、影像原始 URL、许可协议、权利人。
  全部图像来自 GBIF 公开采集影像与 CNKI 学术显微图,真实可溯源;
  宏观融合的问卷/水色似然权重见 源码/藻种知识库.xlsx「宏观融合似然表」sheet,可审计;
  四级预警的风险权重与分级阈值见同文件「预警分级表」sheet,同样可审计。

六、宏观 CNN 弱监督扩充(新增)
  数据集_宏观扩充/:3065 张海面实拍图(256px 降采样版,训练 2760/监控 305),五分类伪标签
  (夜光藻型/有毒甲藻型/硅藻型/绿潮/无赤潮),逐张记录来源 URL(provenance_macro.csv);
  打标方法:可审计规则流(水色CV)伪标签,同类平局按 md5 确定性分配;完整披露见该目录 README.md。
  模型_宏观CNN/:MobileNetV3-Small 冻结骨干训练 10 epochs(伪标签监控准确率 75.4%);
  25 张人工精选真实图验证 80.0%(5类→3类口径),规则流基线 92.0%;
  宏观判定采用保守融合: 规则流(92%)为主, 两路图像证据一致时宏观CNN增强置信度,
  不一致时以规则流为准(CNN 意见以「提示」展示给专家, 不覆盖预警结论), 融合后准确率不低于规则流单独。
  纯图像判定, 现场问卷已移除。
"""
demo_path = os.path.join(OUTDIR, "_demo_v5.txt")
with open(demo_path, "w", encoding="utf-8") as f:
    f.write(demo)

with zipfile.ZipFile(ZPATH, "w", zipfile.ZIP_DEFLATED) as z:
    # 主文档
    add(z, os.path.join(MAT, "作品PPT.pptx"), "作品PPT.pptx")
    add(z, os.path.join(MAT, "设计文档.docx"), "设计文档.docx")
    # 源码
    for f in ["prepare_data.py", "train.py", "predict.py", "app.py", "fusion.py",
              "gbif_download2.py", "make_kb.py", "eval_and_charts.py", "make_ppt.py",
              "make_doc.py"]:
        p = os.path.join(TOOLS, f)
        add(z, p, os.path.join("源码", f))
    add(z, os.path.join(ROOT, "_train_macro.py"), os.path.join("源码", "train_macro.py"))
    add(z, os.path.join(ROOT, "_eval_macro_real.py"), os.path.join("源码", "eval_macro_real.py"))
    add(z, os.path.join(ROOT, "藻种知识库.xlsx"), os.path.join("源码", "藻种知识库.xlsx"))
    add(z, os.path.join(ROOT, "submission", "stage", "源码", "README.md"), os.path.join("源码", "README.md"))
    # 显微模型
    for f in ["best.ckpt", "train_log.json"]:
        add(z, os.path.join(MODEL, f), os.path.join("模型", f))
    add(z, os.path.join(DATA, "class_map.json"), os.path.join("模型", "class_map.json"))
    # 显微数据集(224px)
    for split in ["train", "val"]:
        add(z, os.path.join(DATA, split), os.path.join("数据集", split))
    add(z, os.path.join(GBIF, "provenance.csv"), os.path.join("数据集", "provenance.csv"))
    # 宏观 CNN 模型
    for f in ["best.ckpt", "train_log.json", "class_map.json", "real_eval.json"]:
        add(z, os.path.join(MACRO_MODEL, f), os.path.join("模型_宏观CNN", f))
    # 宏观扩充数据集(256px demo)
    add(z, MACRO_DEMO, "数据集_宏观扩充")
    add(z, os.path.join(MACRO_DEMO, "..", "macro", "provenance_macro.csv"),
        os.path.join("数据集_宏观扩充", "provenance_macro.csv"))
    add(z, os.path.join(OUTDIR, "macro", "_README_macro.md"),
        os.path.join("数据集_宏观扩充", "README.md"))
    add(z, demo_path, "演示说明.txt")

# 匿名扫描
PAT = re.compile(r"队长|队长|200705023|nick0000000|宁德师范|1[3-9]\d{9}", re.I)
srcs = [MAT, TOOLS, MODEL, MACRO_MODEL, DATA, os.path.join(ROOT, "submission", "stage", "源码")]
hits = []
for s in srcs:
    if not os.path.isdir(s):
        continue
    for dp, _, fns in os.walk(s):
        for fn in fns:
            if fn.lower().endswith((".py", ".txt", ".json", ".csv", ".md", ".docx", ".pptx")):
                p = os.path.join(dp, fn)
                try:
                    data = open(p, "rb").read()
                except Exception:
                    continue
                txt = data.decode("utf-8", "ignore")
                for m in PAT.finditer(txt):
                    hits.append((os.path.relpath(p, ROOT), m.group(0)))
print("匿名扫描命中:", hits if hits else "无(通过)")

print("zip 已生成:", ZPATH)
print("大小: %.1f MB" % (os.path.getsize(ZPATH) / 1e6))
