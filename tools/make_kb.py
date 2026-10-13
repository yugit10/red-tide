# -*- coding: utf-8 -*-
"""生成《藻种知识库.xlsx》 —— 赤潮藻分类/风险/生态/养殖影响/爆发规律
内容依据公开文献与赤潮毒素常识整理, 供工具风险提示模块调用。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusion
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

ROWS = [
 # 中文名, 学名, 分类, 训练类别对应, 风险等级, 生态特性, 对养殖影响, 毒素类型, 爆发规律, 监测优先级, 图像数据来源
 ["夜光藻","Noctiluca scintillans","甲藻门 双鞭毛虫纲","noctiluca(种)","中",
  "异养性甲藻,细胞球形,直径可达数百至上千微米,肉眼可见;受机械刺激发出蓝绿色荧光;广温广盐,喜近岸河口富营养化水域。",
  "本身不产藻毒素,但高密度赤潮大量消耗溶解氧,藻体死亡分解产生氨,导致鱼、虾、贝窒息死亡;可堵塞养殖网箱。",
  "不产毒(缺氧+氨致害)","福建沿海春夏季(3—6月)高发,水温约18—25℃、富营养化叠加盐度骤变时易爆发,常形成红色/粉红色水华。",
  "常规监测","GBIF采集影像"],
 ["东海原甲藻","Prorocentrum donghaiense","甲藻门 原甲藻目","prorocentrum(属)","中—高",
  "小型甲藻,细胞卵形约10—15微米,由两片壳板组成;近岸底层分布;为长江口—东海—福建近岸春季赤潮优势种之一。",
  "高密度赤潮致水体缺氧、干扰滤食性贝类摄食;原甲藻属部分种(如P. lima、P. minimum)可产腹泻性贝毒,东海原甲藻本身毒性较低,但大规模爆发严重危害渔业。",
  "属内部分种产DSP(腹泻性贝毒);本种低毒","春季(4—5月)东海、福建近岸大规模赤潮,常与中肋骨条藻等形成复合赤潮。",
  "重点监测","GBIF采集影像 + 知网文献显微图"],
 ["旋链角毛藻","Chaetoceros curvisetus","硅藻门 角毛藻目","chaetoceros(属)","低—中",
  "链状硅藻,细胞具角状刺毛,群体呈链状;广布于近岸暖水海域。",
  "刺毛可机械损伤鱼类鳃组织,高密度时致鳃部损伤、呼吸困难甚至窒息;一般不产藻毒素。",
  "不产毒(机械损伤鳃部)","夏秋季暖水期常见,多见于富营养化近岸水域。",
  "常规监测","GBIF采集影像"],
 ["尖刺拟菱形藻","Pseudo-nitzschia pungens","硅藻门 舟形藻目","pseudonitzschia(属)","高",
  "针状硅藻,细胞相互重叠成链,末端具细长尖刺;广温广盐,近岸至外海均有分布。",
  "拟菱形藻属多种可产软骨藻酸(Domoic acid,DA),经贝类富集后致人失忆性贝毒ASP(记忆障碍、神经症状);尖刺拟菱形藻部分株系产DA,与贝类养殖区重叠时风险高。",
  "产软骨藻酸DA→失忆性贝毒ASP","春、秋季福建、浙江近岸可形成赤潮;因涉贝毒,为重点监测对象。",
  "重点监测(产毒)","GBIF采集影像"],
 ["中肋骨条藻","Skeletonema costatum","硅藻门 骨条藻目","skeletonema(属)","低",
  "小型链状硅藻,细胞圆盘状,以骨状突起相连成链,直径约5—10微米;广布,是典型富营养化指示种。",
  "一般无毒,可作为部分养殖贝类饵料;但高密度赤潮后期藻体死亡分解耗氧,易致底层水体缺氧。",
  "基本无毒(高密度缺氧致害)","春夏季河口、内湾等富营养化水域最常见的优势种之一。",
  "常规监测(指示种)","GBIF采集影像"],
 ["塔玛亚历山大藻","Alexandrium tamarense","甲藻门 膝沟藻目","alexandrium(属)","高",
  "球形甲藻,直径约20—40微米,具顶孔板;近岸底层分布,可形成休眠囊越冬。",
  "产麻痹性贝毒PST(石房蛤毒素saxitoxin等),经贝类富集,人误食可致口唇四肢麻痹、严重者呼吸衰竭死亡;为福建沿海重点监测有毒种。",
  "产麻痹性贝毒PST(石房蛤毒素)","春季(3—5月)闽江口、三都澳等半封闭海湾易发赤潮。",
  "重点监测(剧毒)","GBIF采集影像"],
 ["米氏凯伦藻","Karenia mikimotoi","甲藻门 裸甲藻目 凯伦藻科","karenia(属)","高",
  "无壳板裸甲藻类,细胞背腹扁平、具顶沟与斜横沟,约20—40微米;近岸广布,喜富营养化与适宜温盐窗口。",
  "产溶血性毒素与鱼毒素(karlotoxins等),可直接造成鱼类、海洋无脊椎动物大量死亡,是对水产养殖危害最大的藻种之一;福建沿海最主要的有毒赤潮藻。",
  "溶血性毒素+鱼毒素(karlotoxins)","近十年在福建累计引发21起赤潮、占同期总数约11.6%,闽中沿海分布最集中;夏秋季高温期易发。",
  "重点监测(产毒)","GBIF采集影像"],
]

HEAD = ["藻种名称","学名","分类地位","训练类别(slug)","赤潮风险等级","生态特性",
        "对养殖影响","毒素类型","爆发规律(季节/海域)","监测优先级","图像数据来源"]

def main():
    wb=Workbook(); ws=wb.active; ws.title="藻种知识库"
    thin=Side(style="thin",color="BBBBBB")
    border=Border(left=thin,right=thin,top=thin,bottom=thin)
    hf=PatternFill("solid",fgColor="2E75B6"); hfont=Font(bold=True,color="FFFFFF",size=11)
    for c,h in enumerate(HEAD,1):
        cell=ws.cell(1,c,h); cell.fill=hf; cell.font=hfont
        cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=border
    risk_fill={"高":"F8CBAD","中—高":"FCE4D6","低—中":"FFF2CC","中":"FFF2CC","低":"E2EFDA"}
    for r,row in enumerate(ROWS,2):
        for c,v in enumerate(row,1):
            cell=ws.cell(r,c,v); cell.border=border
            cell.alignment=Alignment(vertical="top",wrap_text=True,horizontal="center" if c in(1,3,4,5,10) else "left")
            if c==5:
                fg=risk_fill.get(v); 
                if fg: cell.fill=PatternFill("solid",fgColor=fg)
                cell.font=Font(bold=True)
    widths=[12,24,16,16,10,40,44,20,34,14,22]
    from openpyxl.utils import get_column_letter
    for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
    ws.row_dimensions[1].height=32
    ws.freeze_panes="A2"

    # ---- sheet2: 宏观融合似然表(可审计) ----
    ws2=wb.create_sheet("宏观融合似然表")
    hyp_cn=[fusion.HYP_CN[h] for h in fusion.HYP]
    def head2(rowidx, cols):
        for c,h in enumerate(cols,1):
            cell=ws2.cell(rowidx,c,h); cell.fill=hf; cell.font=hfont
            cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=border
    r=1
    ws2.cell(r,1,"一、假设集与风险/处置").font=Font(bold=True,size=12); r+=1
    head2(r,["假设","中文名","风险等级","风险说明","处置建议"]); r+=1
    for h in fusion.HYP:
        rk,rn=fusion.HYP_RISK[h]
        for c,v in enumerate([h,fusion.HYP_CN[h],rk,rn,fusion.HYP_ADVICE[h]],1):
            cell=ws2.cell(r,c,v); cell.border=border
            cell.alignment=Alignment(vertical="top",wrap_text=True)
        r+=1
    r+=1
    ws2.cell(r,1,"二、水色类别似然(图像证据)").font=Font(bold=True,size=12); r+=1
    head2(r,["水色类别"]+hyp_cn); r+=1
    for lab,d in fusion.COLOR_LIK.items():
        vals=[fusion.COLOR_CN[lab]]+[d[h] for h in fusion.HYP]
        for c,v in enumerate(vals,1):
            cell=ws2.cell(r,c,v); cell.border=border
            cell.alignment=Alignment(horizontal="center" if c>1 else "left",vertical="center")
        r+=1
    r+=1
    ws2.cell(r,1,"三、现场问卷似然(6题)").font=Font(bold=True,size=12); r+=1
    head2(r,["题号/题干","选项"]+hyp_cn); r+=1
    for q in fusion.QUESTIONS:
        for o in q["options"]:
            vals=[q["text"],o["label"]]+[o["lik"][h] for h in fusion.HYP]
            for c,v in enumerate(vals,1):
                cell=ws2.cell(r,c,v); cell.border=border
                cell.alignment=Alignment(horizontal="center" if c>2 else "left",vertical="center",wrap_text=c<=2)
            r+=1
    from openpyxl.utils import get_column_letter as gcl
    for i,w in enumerate([26,26,10,40,40],1): ws2.column_dimensions[gcl(i)].width=w
    for i in range(6,6+len(fusion.HYP)+1): ws2.column_dimensions[gcl(i)].width=14
    ws2.freeze_panes="A2"

    # ---- sheet3: 四级预警分级表(可审计) ----
    ws3=wb.create_sheet("预警分级表")
    def head3(rowidx, cols):
        for c,h in enumerate(cols,1):
            cell=ws3.cell(rowidx,c,h); cell.fill=hf; cell.font=hfont
            cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=border
    r=1
    ws3.cell(r,1,"一、类群固有风险权重(用于计算预警指数)").font=Font(bold=True,size=12); r+=1
    head3(r,["风险等级","权重"]); r+=1
    for k,v in fusion.RISK_WEIGHT.items():
        ws3.cell(r,1,k).border=border
        cw=ws3.cell(r,2,v); cw.border=border; cw.alignment=Alignment(horizontal="center")
        r+=1
    ws3.cell(r,1,"预警指数 = round(后验置信度 × 风险权重 × 100)").font=Font(italic=True); r+=2
    ws3.cell(r,1,"二、四级预警信号(阈值 / 色标 / 响应措施)").font=Font(bold=True,size=12); r+=1
    head3(r,["等级","色标","指数下限","名称","含义","响应措施"]); r+=1
    lv_fill={"Ⅰ":"F4B6B0","Ⅱ":"FBD5B5","Ⅲ":"FFF2CC","Ⅳ":"D6E4F0"}
    for a in fusion.ALERT_LEVELS:
        vals=[a["level"],a["color_cn"],("≥%d"%a["min"]),a["name"],a["meaning"],a["measures"]]
        for c,v in enumerate(vals,1):
            cell=ws3.cell(r,c,v); cell.border=border
            cell.alignment=Alignment(vertical="top",wrap_text=True,
                                     horizontal="center" if c in (1,2,3) else "left")
            if c<=2:
                fg=lv_fill.get(a["level"])
                if fg: cell.fill=PatternFill("solid",fgColor=fg)
                cell.font=Font(bold=True)
        r+=1
    from openpyxl.utils import get_column_letter as gcl3
    for i,w in enumerate([8,10,10,26,40,60],1): ws3.column_dimensions[gcl3(i)].width=w
    ws3.freeze_panes="A2"

    out=r"D:\train\藻种知识库.xlsx"
    wb.save(out); print("saved",out,"rows",len(ROWS))

if __name__=="__main__":
    main()
