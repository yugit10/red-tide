# -*- coding: utf-8 -*-
"""app.py —— Streamlit 前端: 海洋微藻智能识别与赤潮风险提示工具(双分支)
主分支: 宏观海面照片 → 水色CV似然 × 现场6题问卷 → 贝叶斯融合 → 致灾类群/风险/建议
次分支: 显微照片 → MobileNetV3-Small(MindSpore) 7类识别(实验室确认)
运行: streamlit run app.py
"""
import os, io, json, tempfile
import streamlit as st
from PIL import Image

st.set_page_config(page_title="海洋微藻智能识别与赤潮风险提示", page_icon="🌊", layout="wide")

MODEL_DIR = r"D:\train\model"


def render_alert(a):
    """醒目四级预警信号卡: 色标 + 等级 + 预警指数 + 含义."""
    st.markdown(
        f'<div style="border-left:8px solid {a["color_hex"]};'
        f'background:{a["color_hex"]}1A;padding:12px 16px;border-radius:6px;margin:6px 0 10px 0;">'
        f'<div style="font-size:22px;font-weight:700;color:{a["color_hex"]};line-height:1.25;">'
        f'{a["color_cn"]}预警 · {a["level"]}级'
        f'<span style="font-size:15px;font-weight:500;">　预警指数 {a["index"]}/100</span></div>'
        f'<div style="font-size:13px;color:#333;margin-top:4px;">{a["meaning"]}</div></div>',
        unsafe_allow_html=True)


def sec_head(n, title, color="#2E75B6"):
    """四段式结论的小节头: 编号+标题+色条, 把结论在视觉上分离成独立区块."""
    st.markdown(
        f'<div style="border-left:6px solid {color};background:{color}14;padding:6px 12px;'
        f'border-radius:4px;margin:14px 0 6px 0;font-weight:700;font-size:15px;color:#222;">'
        f'{n}. {title}</div>',
        unsafe_allow_html=True)


RISK_COLOR = {"高": "🔴", "中—高": "🟠", "低—中": "🟡", "中": "🟡", "低": "🟢", "无": "🟢"}


@st.cache_resource(show_spinner="正在加载显微模型...")
def get_predictor():
    from predict import Predictor
    return Predictor()


def load_train_log():
    p = os.path.join(MODEL_DIR, "train_log.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {}


# ---------- 侧边栏 ----------
with st.sidebar:
    st.title("🌊 海洋微藻识别")
    st.caption("赤潮风险提示工具 · 双分支 · MindSpore")
    log = load_train_log()
    st.divider()
    st.subheader("分支一 · 宏观海面(主)")
    st.write("- 水色CV色块检测(无需训练)")
    st.write("- × 现场6题问卷似然")
    st.write("- → 贝叶斯融合后验")
    st.subheader("分支二 · 显微(实验室确认)")
    if log:
        st.metric("显微验证集准确率", f"{log.get('best_val_acc', 0) * 100:.1f}%")
        st.write(f"- MobileNetV3-Small / MindSpore")
        st.write(f"- 类别数:{len(log.get('classes', []))}")
    else:
        st.info("显微模型未训练")
    st.divider()
    with st.expander("数据来源与真实性说明"):
        st.markdown(
            "本工具图像与判定依据均来自**可公开溯源**的真实数据:\n\n"
            "- **GBIF**(全球生物多样性信息网络)采集影像,逐张记录采集记录号、学名、许可协议与权利人;\n"
            "- **CNKI 学术图片库**期刊/学位论文显微图,标注图注与文献来源;\n"
            "- 宏观分支的现场问卷似然权重依据赤潮监测公开规程与致灾类群生态学特征显式声明,可审计。\n\n"
            "所有图片溯源信息见 `provenance.csv`。")
    st.caption("仅供科研/教学演示,不能替代专业鉴定与官方通报。")

# ---------- 主页 ----------
st.title("海洋微藻智能识别与赤潮风险提示工具")
st.markdown("**推荐上传海面现状照片**(岸边/船上拍摄即可),结合现场6题问卷给出赤潮风险;"
            "如有显微照片可切到第二分支做实验室级确认。")

tab_macro, tab_micro = st.tabs(["🌊 宏观海面照片(推荐)", "🔬 显微照片(实验室确认)"])

# ================= 分支一: 宏观 =================
with tab_macro:
    import fusion
    ups = st.file_uploader("上传海面照片(可多张)", type=["jpg", "jpeg", "png"],
                           accept_multiple_files=True, key="macro_up")
    st.markdown("##### 现场特征问卷(与图像证据融合)")
    answers = {}
    qcols = st.columns(2)
    for i, q in enumerate(fusion.QUESTIONS):
        with qcols[i % 2]:
            labels = [o["label"] for o in q["options"]]
            sel = st.selectbox(q["text"], ["未选择"] + labels, key=f"q_{q['id']}")
            answers[q["id"]] = None if sel == "未选择" else sel
    n_ans = sum(1 for v in answers.values() if v)
    st.caption(f"已答 {n_ans}/6 题。答得越多融合越准; 不答则仅用图像水色证据。")

    if not ups:
        st.info("👆 上传一张海面照片开始分析。")
        st.stop()

    for uf in ups:
        img = Image.open(io.BytesIO(uf.getvalue())).convert("RGB")
        label, lik, meta = fusion.image_color_likelihood(img)
        # 场景自动提示: 低饱和→疑似显微明场
        if meta["sat"] < 0.10:
            st.warning(f"《{uf.name}》整体饱和度很低({meta['sat']}), 疑似**显微明场照片**而非海面照, "
                       "建议切到「显微照片」分支。")
        res = fusion.fuse(lik, answers)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(img, caption=uf.name, use_container_width=True)
            st.caption(f"图像水色证据:{meta['color_cn']} "
                       f"(粉色块{meta['f_pink']:.0%}/褐{meta['f_brown']:.0%}/"
                       f"绿{meta['f_green']:.0%}/泡沫{meta['f_foam']:.0%})")
        with c2:
            a = res["alert"]
            sec_head(1, "可能藻种")
            st.markdown(f"{res['top_cn']}　(融合置信度 {res['confidence'] * 100:.1f}%)")
            st.progress(min(res["confidence"], 1.0))
            _top3 = sorted(res["posterior"].items(), key=lambda kv: -kv[1])[:3]
            st.caption("后验Top3:" + "、".join(f"{fusion.HYP_CN[h]} {p * 100:.1f}%" for h, p in _top3))
            sec_head(2, "相关危害", "#ED7D31")
            st.markdown(res["risk_note"])
            sec_head(3, "严重性", "#C00000")
            render_alert(a)
            sec_head(4, "应对措施", "#34A853")
            st.markdown(a["measures"])
            st.markdown(res["advice"])
            with st.expander("📊 证据链与预警依据"):
                for h, p in sorted(res["posterior"].items(), key=lambda kv: -kv[1]):
                    st.write(f"- {fusion.HYP_CN[h]}:{p * 100:.1f}%")
                st.caption("参与融合的证据:" + "、".join(res["evidence"]))
                st.caption(a["trigger"])
        st.divider()

# ================= 分支二: 显微 =================
with tab_micro:
    st.markdown("上传海洋微藻**显微照片**,由 MobileNetV3-Small(MindSpore) 做7类识别, 作为实验室级确认。")
    mups = st.file_uploader("选择显微图像(可多选)", type=["jpg", "jpeg", "png"],
                            accept_multiple_files=True, key="micro_up")
    if mups:
        pred = get_predictor()
        for uf in mups:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(uf.getbuffer()); tmp.close()
            img = Image.open(tmp).convert("RGB")
            r = pred.predict(tmp, topk=3)
            os.unlink(tmp)
            top = r[0]
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(img, caption=uf.name, use_container_width=True)
            with c2:
                a2 = fusion.alert_from(top.get("risk", "无"), top["prob"])
                sec_head(1, "可能藻种")
                st.markdown(f"{top['cn']}　*{top.get('sci', '')}*　(置信度 {top['prob'] * 100:.1f}%)")
                st.progress(min(top["prob"], 1.0))
                st.caption("Top3:" + "、".join(f"{x['cn']} {x['prob'] * 100:.1f}%" for x in r))
                sec_head(2, "相关危害", "#ED7D31")
                st.markdown(f"毒素类型:{top.get('toxin', '—')}")
                st.markdown(f"对养殖/人体影响:{top.get('impact', '—')}")
                sec_head(3, "严重性", "#C00000")
                render_alert(a2)
                sec_head(4, "应对措施", "#34A853")
                st.markdown(a2["measures"])
                st.caption(f"监测优先级:{top.get('priority', '—')}")
                with st.expander("🔎 生态特性/爆发规律与预警依据"):
                    st.markdown(f"**生态特性**:{top.get('eco', '—')}")
                    st.markdown(f"**爆发规律**:{top.get('pattern', '—')}")
                    st.caption(a2["trigger"])
            st.divider()

st.caption("宏观分支:水色CV+贝叶斯融合 | 显微分支:MobileNetV3-Small / MindSpore | "
           "数据:GBIF + CNKI | 仅供科研教学演示")
