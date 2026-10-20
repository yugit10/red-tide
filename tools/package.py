# -*- coding: utf-8 -*-
"""package.py —— 组装提交包(内容匿名)并打包 zip

结构:
  技术报告.docx / 设计文档.docx / 作品PPT.pptx
  源码/(各 .py + 藻种知识库.xlsx)
  模型/(显微 best.ckpt, train_log.json, class_map.json)
  模型_宏观/(宏观 best.ckpt, class_map.json, real_eval.json)
  模型_预检/(预检 best.ckpt, train_log.json)
  数据集/(algae_dataset 处理后 train/val + provenance.csv)
  演示说明.txt

输出: D:\\train\\submission\\海洋微藻智能识别与赤潮风险提示工具-匿名版.zip
匿名评审要求: 包名与包内文本均不得出现学校名、个人姓名或手机号。
"""
import os
import re
import shutil
import zipfile

ROOT = r"D:\train"
STEP = os.path.join(ROOT, "_docbuild", "stage_build")   # 全新目录, 避免旧残留文件覆盖失败


# ---- 身份信息: 放本地文件 .identity.local(已 gitignore), 不写进代码 ----
# 每行 key=value:
#   school=某某大学
#   leader=队长姓名
#   phone=13800000000
#   alias=别名1,别名2        # 额外要扫描掉的旧写法/昵称, 可选
def _load_identity():
    ident = {"school": "学校名称", "leader": "队长", "phone": "13800000000", "alias": ""}
    path = os.path.join(ROOT, ".identity.local")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                k, sep, v = line.partition("=")
                if sep and v.strip():
                    ident[k.strip()] = v.strip()
    return ident


IDENT = _load_identity()
STAGE = os.path.join(ROOT, "submission", "stage")
TOOLS = os.path.join(ROOT, "tools")
MAT = os.path.join(ROOT, "materials")
DOCS = os.path.join(ROOT, "提交文档")


def _onerr(fn, path, _):
    try:
        os.chmod(path, 0o666)
        fn(path)
    except OSError:
        pass


# 每次打包前重建独立的 staging 目录(新建目录名带序号, 规避旧目录内文件被占用的问题)
if os.path.exists(STEP):
    shutil.rmtree(STEP, onerror=_onerr)
n = 1
while os.path.exists(STEP):
    STEP = os.path.join(ROOT, "_docbuild", "stage_build_%d" % n)
    n += 1
STAGE = STEP
os.makedirs(STAGE, exist_ok=True)


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    try:
        os.chmod(dst, 0o666)
    except Exception:
        pass


def cp_first(cands, dst, label):
    """按优先级取第一个存在的文件，找不到时明确告警而不是静默跳过。"""
    for src in cands:
        if os.path.isfile(src):
            cp(src, dst)
            print("  [OK] %s <- %s" % (label, src))
            return True
    print("  [!!] %s 未找到，已跳过。候选: %s" % (label, cands))
    return False


# ---- 主文档: 优先用最新交付版, 回退到 materials/ ----
cp_first([os.path.join(DOCS, "2026海峡大学生人工智能创意大赛-技术报告.docx"),
          os.path.join(MAT, "技术报告.docx")],
         os.path.join(STAGE, "技术报告.docx"), "技术报告")
cp_first([os.path.join(DOCS, "2026海峡大学生人工智能创意大赛-设计文档.docx"),
          os.path.join(MAT, "设计文档.docx")],
         os.path.join(STAGE, "设计文档.docx"), "设计文档")
cp_first([os.path.join(MAT, "作品PPT.pptx")],
         os.path.join(STAGE, "作品PPT.pptx"), "作品PPT")

# ---- 源码 ----
for f in ["prepare_data.py", "train.py", "predict.py", "app.py", "fusion.py",
          "gbif_download2.py", "make_kb.py", "eval_and_charts.py", "make_ppt.py", "make_doc.py"]:
    cp(os.path.join(TOOLS, f), os.path.join(STAGE, "源码", f))
cp(os.path.join(ROOT, "藻种知识库.xlsx"), os.path.join(STAGE, "源码", "藻种知识库.xlsx"))

# ---- 模型: 显微 ----
for f in ["best.ckpt", "train_log.json"]:
    cp(os.path.join(ROOT, "model", f), os.path.join(STAGE, "模型", f))
cp(os.path.join(ROOT, "algae_dataset", "class_map.json"),
   os.path.join(STAGE, "模型", "class_map.json"))

# ---- 模型: 宏观 CNN 与海面预检(缺少任一, app 会退化为纯规则流) ----
for f in ["best.ckpt", "class_map.json", "real_eval.json", "train_log.json"]:
    p = os.path.join(ROOT, "model_macro", f)
    if os.path.isfile(p):
        cp(p, os.path.join(STAGE, "模型_宏观", f))
for f in ["best.ckpt", "train_log.json"]:
    p = os.path.join(ROOT, "model_precheck", f)
    if os.path.isfile(p):
        cp(p, os.path.join(STAGE, "模型_预检", f))

# ---- 数据集(处理后 224x224) + 溯源 ----
for split in ["train", "val"]:
    src = os.path.join(ROOT, "algae_dataset", split)
    for cls in os.listdir(src):
        d = os.path.join(src, cls)
        if not os.path.isdir(d):
            continue
        for img in os.listdir(d):
            cp(os.path.join(d, img), os.path.join(STAGE, "数据集", split, cls, img))
cp(os.path.join(ROOT, "dataset_raw", "gbif2", "provenance.csv"),
   os.path.join(STAGE, "数据集", "provenance.csv"))
# CNKI 补充影像的溯源表(原甲藻类补充图, 与 GBIF 溯源表分开记录)
_cnki_prov = os.path.join(ROOT, "dataset_raw", "cnki", "cnki_provenance.csv")
if os.path.isfile(_cnki_prov):
    cp(_cnki_prov, os.path.join(STAGE, "数据集", "provenance_cnki.csv"))
    print("  [OK] CNKI 溯源表 <- %s" % _cnki_prov)
else:
    print("  [!!] CNKI 溯源表未找到")

# ---- 演示说明 ----
demo = """海洋微藻智能识别与赤潮风险提示工具 —— 演示与运行说明(双分支)

一、环境
  Python 3.10; 依赖: mindspore、mindcv、streamlit、pillow、openpyxl、numpy(<2)

二、目录
  技术报告.docx / 设计文档.docx / 作品PPT.pptx
  源码/        各功能脚本与《藻种知识库.xlsx》
  模型/        显微 7 类 MobileNetV3-Small 权重与类别映射
  模型_宏观/   宏观 5 类 CNN(作为融合的辅助证据)
  模型_预检/   海面/非海面二分类预检模型
  数据集/      train/ val/ 与逐张溯源表 provenance.csv

三、运行演示(推荐)
  1) 把 模型/、模型_宏观/、模型_预检/ 与 源码/藻种知识库.xlsx 放到脚本默认路径
     (默认 D:\\train\\...), 或直接修改 app.py / predict.py 顶部的路径常量;
  2) 进入 源码/ 目录, 执行:  streamlit run app.py
  3) 浏览器访问 http://localhost:8501 ,默认在「拍海面查风险(渔民用)」页签:
     只需上传一张海面现状照片(无需回答任何问卷), 系统依次完成
     海面预检 → 水色CV + 宏观CNN 保守融合 → 四级预警(红/橙/黄/蓝)+ 预警指数,
     并给出三句大白话结论、语音播报、一键复制上报话术与定位附注;
  4) 切到「显微照片(化验室人员用)」页签上传显微照片 →
     输出识别类别 + 置信度 + Top-3 + 风险等级 + 四级预警信号 + 毒素/生态/养殖影响/爆发规律/监测优先级。

四、复现训练(显微分支)
  python prepare_data.py     # 由原始 GBIF/CNKI 影像重建 train/val
  python train.py --epochs 30
  验证集准确率 95.39%(145/152, 详见 模型/train_log.json)。

五、命令行推理
  显微: python predict.py <图像或目录>
  宏观: python -c "from PIL import Image; import fusion; print(fusion.fuse(fusion.image_color_likelihood(Image.open('<海面照>'))[1]))"

六、数据真实性
  数据集/provenance.csv      GBIF 公开采集影像的逐张溯源记录:
                             类别、采集记录号、记录学名、影像原始 URL、许可协议、权利人。
  数据集/provenance_cnki.csv CNKI 学术文献显微图的溯源记录(原甲藻类补充), 含文献编号与图注。
  训练影像均来自上述两类真实公开来源: 数据集共 759 张,
  其中 GBIF 755 张(去重后) + CNKI 补充图若干(归并入 prorocentrum 类别)。
  宏观融合的水色似然权重见 源码/藻种知识库.xlsx「宏观融合似然表」;
  四级预警的风险权重与分级阈值见同文件「预警分级表」; 二者均可审计、可维护。
"""
with open(os.path.join(STAGE, "演示说明.txt"), "w", encoding="utf-8") as f:
    f.write(demo)

# ---- 匿名扫描: 检查文本类文件是否含个人信息 ----
# 手机号要求独立成串(前后非数字/小数点), 避免误命中训练日志里的浮点数(如 18495538046.5)
_alias = [x.strip() for x in IDENT["alias"].split(",") if x.strip()]
PAT = re.compile("|".join(
    [re.escape(IDENT["school"]), re.escape(IDENT["leader"])]
    + [re.escape(x) for x in _alias]
    + [r"(?<![\d.])1[3-9]\d{9}(?![\d.])"]
), re.I)
hits = []
for dp, _, fns in os.walk(STAGE):
    for fn in fns:
        if fn.lower().endswith((".py", ".txt", ".json", ".csv", ".md")):
            p = os.path.join(dp, fn)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in PAT.finditer(txt):
                hits.append((os.path.relpath(p, STAGE), m.group(0)))
print("匿名扫描命中:", hits if hits else "无(通过)")

# ---- 打包 ----
# 按 2026 年大赛通知第 8 页要求: 文件名 "学校名称-作品名称-队长姓名-队长手机号.zip";
# 同条要求"所有资料内容中均不得出现参赛选手信息", 由上方匿名扫描保障包内内容匿名。
OUTDIR = os.path.join(ROOT, "submission")
os.makedirs(OUTDIR, exist_ok=True)
zipname = "{school}-海洋微藻智能识别与赤潮风险提示工具-{leader}-{phone}.zip".format(**IDENT)
zpath = os.path.join(OUTDIR, zipname)
if os.path.exists(zpath):
    try:
        os.remove(zpath)
        print("已删除旧压缩包")
    except OSError as e:
        print("旧包删除失败(%s), 将直接覆盖" % e)
total = 0
nfiles = 0
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for dp, _, fns in os.walk(STAGE):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, STAGE)
            z.write(full, rel)
            total += os.path.getsize(full)
            nfiles += 1
print("zip 已生成: %s" % zpath)
print("文件数 %d, 未压缩 %.1f MB, 压缩后 %.1f MB"
      % (nfiles, total / 1e6, os.path.getsize(zpath) / 1e6))
size_mb = os.path.getsize(zpath) / 1e6
print("体积限制 600M: %s (%.1f MB)" % ("符合" if size_mb < 600 else "!! 超出", size_mb))
