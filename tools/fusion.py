# -*- coding: utf-8 -*-
"""贝叶斯融合引擎: 宏观海面图像水色似然 × 现场6题问卷似然 → 后验(致灾类群/风险/建议).
透明可解释: 每个选项对假设集的似然权重显式声明, 可写入设计文档."""
import colorsys
import numpy as np
from PIL import Image

# 假设集 H
HYP = ["noctiluca", "toxic_dino", "diatom", "green_tide", "none"]
HYP_CN = {
    "noctiluca":  "夜光藻型水华(缺氧致害)",
    "toxic_dino": "有毒甲藻型(亚历山大藻/短裸藻/原甲藻, 产毒)",
    "diatom":     "硅藻型水华(骨条藻/角毛藻, 缺氧/堵塞鳃)",
    "green_tide": "绿潮/绿藻水华(浒苔/石莼)",
    "none":       "无明显赤潮(正常海水)",
}
HYP_RISK = {
    "noctiluca":  ("中—高", "高生物量耗氧致鱼虾窒息, 一般不产毒"),
    "toxic_dino": ("高",    "可产麻痹性/神经性贝毒, 严禁采食贝类, 避免接触"),
    "diatom":     ("中",    "堵塞鱼鳃/耗氧, 养殖区需增氧防损失"),
    "green_tide": ("低—中", "主要影响景观与局部溶氧, 毒性低"),
    "none":       ("无",    "未见赤潮征象"),
}
HYP_ADVICE = {
    "noctiluca":  "建议上报当地海洋渔业部门; 养殖区夜间注意增氧; 无需恐慌性禁食贝类但避免直接接触水华。",
    "toxic_dino": "立即上报; 严禁采捕/食用该海域贝类; 避免皮肤接触与气溶胶吸入; 关注官方贝毒通报。",
    "diatom":     "上报并加密监测; 养殖区启动增氧; 关注鱼虾摄食与鳃部状况。",
    "green_tide": "可上报城管/海洋部门清理; 对游泳影响小, 避免大量聚集区接触。",
    "none":       "无需处置; 若后续出现变色/死鱼请重新上报。",
}

# ===== 四级预警分级 (显式、可审计) =====
# 类群固有风险等级 → 权重 (与 HYP_RISK 的风险字符串对应)
RISK_WEIGHT = {"高": 1.0, "中—高": 0.8, "中": 0.6, "低—中": 0.4, "低": 0.25, "无": 0.0}
# 预警指数 = round(后验置信度 × 风险权重 × 100), 综合"研判有多确定"与"命中类群有多危险"

# 四级预警: 指数区间(下限含、上限不含) / 色标 / 名称 / 含义 / 响应措施
ALERT_LEVELS = [
    {"level": "Ⅰ", "color_cn": "红色", "color_hex": "#C00000", "min": 70,
     "name": "红色预警(Ⅰ级·特别严重)",
     "meaning": "高置信命中高危/产毒类群, 或已现死鱼死贝等致灾征兆, 赤潮危害风险很高。",
     "measures": "立即上报海洋渔业主管部门并启动应急; 受影响海域暂停贝类采捕与上市、待官方贝毒检测合格方可恢复; 加密至每日监测水色与藻密度; 核查麻痹性/腹泻性/失忆性贝毒及鱼毒素; 养殖区应急增氧、必要时转移网箱; 人员避免接触水华与吸入气溶胶。"},
    {"level": "Ⅱ", "color_cn": "橙色", "color_hex": "#ED7D31", "min": 50,
     "name": "橙色预警(Ⅱ级·严重)",
     "meaning": "较高置信命中致灾类群, 赤潮危害风险较高, 需尽快核实与防范。",
     "measures": "48小时内复核研判; 暂停该点位贝类采捕并送检; 每日监测水色、夜间荧光与死鱼死虾情况; 养殖区提前增氧, 关注鱼虾摄食与鳃部状况; 做好上报准备。"},
    {"level": "Ⅲ", "color_cn": "黄色", "color_hex": "#FFC000", "min": 30,
     "name": "黄色预警(Ⅲ级·较重)",
     "meaning": "中等置信或中低危类群, 存在赤潮发生苗头, 需加强观察。",
     "measures": "加强巡查(每2—3天一次); 采集水样镜检确认类群与细胞密度; 留意水色变化、腥味与夜间荧光; 向主管部门通报发展趋势。"},
    {"level": "Ⅳ", "color_cn": "蓝色", "color_hex": "#2E75B6", "min": 0,
     "name": "蓝色预警(Ⅳ级·一般/观察)",
     "meaning": "未见明显赤潮征象, 或仅低风险提示, 维持常规关注即可。",
     "measures": "维持常规监测; 若出现升温、暴雨径流、盐度骤降或水色突变等情况, 请重新研判并上报。"},
]


def alert_from(risk, confidence):
    """由命中类群固有风险(risk字符串)与后验置信度(0—1)计算四级预警. 返回 alert dict."""
    w = RISK_WEIGHT.get(risk, 0.0)
    index = int(round(float(confidence) * w * 100))
    lv = next((a for a in ALERT_LEVELS if index >= a["min"]), ALERT_LEVELS[-1])
    return {
        "index": index, "level": lv["level"], "color_cn": lv["color_cn"],
        "color_hex": lv["color_hex"], "name": lv["name"], "meaning": lv["meaning"],
        "measures": lv["measures"], "risk_weight": w,
        "trigger": "预警指数 %d = 置信度%.0f%% × 风险权重%.2f × 100 → %s(≥%d)"
                   % (index, confidence * 100, w, lv["color_cn"], lv["min"]),
    }


# 水色标签 → 似然 (与Q1选项共用)
COLOR_LIK = {
    "pink_red":   {"noctiluca": 4.0, "toxic_dino": 2.0, "diatom": 1.0, "green_tide": 0.3, "none": 0.2},
    "brown_gold": {"noctiluca": 1.0, "toxic_dino": 3.0, "diatom": 3.0, "green_tide": 0.3, "none": 0.2},
    "green":      {"noctiluca": 0.3, "toxic_dino": 0.5, "diatom": 1.5, "green_tide": 4.0, "none": 0.3},
    "foam_white": {"noctiluca": 2.0, "toxic_dino": 1.0, "diatom": 2.0, "green_tide": 0.5, "none": 0.5},
    "normal_blue":{"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 0.3, "none": 4.0},
}
COLOR_CN = {"pink_red": "粉红/砖红", "brown_gold": "褐黄/酱色", "green": "翠绿/墨绿",
            "foam_white": "乳白/泡沫", "normal_blue": "灰蓝/正常"}

# 6题问卷: 每题选项带似然权重
QUESTIONS = [
    {"id": "color", "text": "1. 海水整体颜色更接近?", "options": [
        {"label": "粉红/砖红",   "lik": COLOR_LIK["pink_red"]},
        {"label": "褐黄/酱色",   "lik": COLOR_LIK["brown_gold"]},
        {"label": "翠绿/墨绿",   "lik": COLOR_LIK["green"]},
        {"label": "乳白/泡沫多", "lik": COLOR_LIK["foam_white"]},
        {"label": "灰蓝/清澈正常","lik": COLOR_LIK["normal_blue"]}]},
    {"id": "glow", "text": "2. 夜间或搅动水面时是否发蓝绿光?", "options": [
        {"label": "是",   "lik": {"noctiluca": 5.0, "toxic_dino": 0.5, "diatom": 0.5, "green_tide": 0.5, "none": 0.2}},
        {"label": "否",   "lik": {"noctiluca": 0.6, "toxic_dino": 1.0, "diatom": 1.0, "green_tide": 1.0, "none": 1.0}},
        {"label": "不确定","lik": {h: 1.0 for h in HYP}}]},
    {"id": "mortality", "text": "3. 是否见死鱼/死虾蟹/贝类开口异常?", "options": [
        {"label": "有", "lik": {"noctiluca": 3.0, "toxic_dino": 4.0, "diatom": 3.0, "green_tide": 1.0, "none": 0.2}},
        {"label": "无", "lik": {"noctiluca": 0.8, "toxic_dino": 0.8, "diatom": 0.8, "green_tide": 1.0, "none": 1.2}}]},
    {"id": "floating", "text": "4. 水面漂浮物情况?", "options": [
        {"label": "绿色藻团/菜叶状", "lik": {"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 5.0, "none": 0.3}},
        {"label": "褐色膜/泡沫",     "lik": {"noctiluca": 1.5, "toxic_dino": 2.0, "diatom": 2.5, "green_tide": 0.5, "none": 0.4}},
        {"label": "油污感(非藻类)",  "lik": {"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 0.3, "none": 2.0}},
        {"label": "无明显漂浮物",    "lik": {h: 1.0 for h in HYP}}]},
    {"id": "smell", "text": "5. 现场气味?", "options": [
        {"label": "明显腥臭", "lik": {"noctiluca": 2.5, "toxic_dino": 2.0, "diatom": 2.5, "green_tide": 1.5, "none": 0.2}},
        {"label": "轻微气味", "lik": {h: 1.0 for h in HYP}},
        {"label": "无明显气味","lik": {"noctiluca": 0.8, "toxic_dino": 0.8, "diatom": 0.8, "green_tide": 0.8, "none": 1.5}}]},
    {"id": "env", "text": "6. 近期环境背景?", "options": [
        {"label": "内湾/养殖区+高温晴朗", "lik": {"noctiluca": 2.0, "toxic_dino": 2.5, "diatom": 2.0, "green_tide": 1.0, "none": 0.5}},
        {"label": "大雨后/河口附近",     "lik": {"noctiluca": 1.0, "toxic_dino": 1.5, "diatom": 2.5, "green_tide": 2.0, "none": 0.6}},
        {"label": "开阔近岸+降温大风",   "lik": {"noctiluca": 0.7, "toxic_dino": 0.7, "diatom": 0.7, "green_tide": 0.7, "none": 2.0}},
        {"label": "不确定",             "lik": {h: 1.0 for h in HYP}}]},
]


def image_color_likelihood(pil_img):
    """经典CV: 取下部水体区域HSV统计→水色标签→似然. 返回(label, lik, meta)."""
    img = pil_img.convert("RGB")
    w, h = img.size
    # 水体区域: 取中段水平带, 避开天空(上)与前景沙滩/船体(下)
    crop = img.crop((0, int(h * 0.20), w, h))  # 去天空
    arr = np.asarray(crop).astype(np.float32) / 255.0
    tot_px = arr.shape[0] * arr.shape[1]
    # 向量化 RGB->HSV
    mx = arr.max(axis=2); mn = arr.min(axis=2); df = mx - mn + 1e-8
    v = mx
    s = np.where(mx > 0, df / (mx + 1e-8), 0)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    m = (mx == r); hue[m] = ((g - b)[m] / df[m]) % 6
    m = (mx == g) & (mx != r); hue[m] = ((b - r)[m] / df[m]) + 2
    m = (mx == b) & (mx != r) & (mx != g); hue[m] = ((r - g)[m] / df[m]) + 4
    hue = hue * 60.0
    mean_s = float(s.mean()); mean_v = float(v.mean())
    # 水华色块存在性: 各色系饱和像素占比
    pink_m  = ((hue >= 330) | (hue < 20)) & (s > 0.30) & (v > 0.15)
    brown_m = (hue >= 20) & (hue < 50) & (s > 0.30) & (v > 0.20) & (v < 0.85)
    green_m = (hue >= 50) & (hue < 170) & (s > 0.30)
    foam_m  = (s < 0.10) & (v > 0.80)
    f_pink  = float(pink_m.sum()) / tot_px
    f_brown = float(brown_m.sum()) / tot_px
    f_green = float(green_m.sum()) / tot_px
    f_foam  = float(foam_m.sum()) / tot_px
    if f_pink > 0.02:
        label = "pink_red"
    elif f_green > 0.05:
        label = "green"
    elif f_brown > 0.08:
        label = "brown_gold"
    elif f_foam > 0.30:
        label = "foam_white"
    else:
        label = "normal_blue"
    meta = {"f_pink": round(f_pink, 3), "f_brown": round(f_brown, 3),
            "f_green": round(f_green, 3), "f_foam": round(f_foam, 3),
            "sat": round(mean_s, 3), "val": round(mean_v, 3),
            "color_cn": COLOR_CN[label]}
    return label, dict(COLOR_LIK[label]), meta


def fuse(image_lik=None, answers=None, image_weight=2.0):
    """answers: {qid: option_label}. 返回后验dict+top+risk+advice."""
    post = {h: 1.0 for h in HYP}  # 均匀先验
    evid = []
    if image_lik:
        for h in HYP:
            post[h] *= image_lik[h] ** image_weight
        evid.append("图像水色")
    for q in QUESTIONS:
        lab = (answers or {}).get(q["id"])
        if not lab:
            continue
        opt = next((o for o in q["options"] if o["label"] == lab), None)
        if not opt:
            continue
        for h in HYP:
            post[h] *= opt["lik"][h]
        evid.append(q["text"].split(".")[0])
    tot = sum(post.values()) or 1.0
    post = {h: post[h] / tot for h in HYP}
    top = max(post, key=post.get)
    risk, risk_note = HYP_RISK[top]
    alert = alert_from(risk, post[top])
    return {
        "posterior": {h: round(post[h], 4) for h in HYP},
        "top": top, "top_cn": HYP_CN[top], "confidence": round(post[top], 4),
        "risk": risk, "risk_note": risk_note, "advice": HYP_ADVICE[top],
        "alert": alert,
        "evidence": evid,
    }
