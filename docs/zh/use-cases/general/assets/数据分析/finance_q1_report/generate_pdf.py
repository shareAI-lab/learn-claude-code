from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import os

# 注册中文字体
font_paths = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
]
font_registered = False
for fp in font_paths:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('ChineseFont', fp))
            font_registered = True
            break
        except Exception:
            continue

if not font_registered:
    # fallback 用内置 Helvetica（英文/数字可用，中文会显示方块）
    class FakeFont:
        name = 'Helvetica'
    pdfmetrics.registerFont(FakeFont())
    CHINESE_FONT = 'Helvetica'
else:
    CHINESE_FONT = 'ChineseFont'

def make_style():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ChineseTitle', fontName=CHINESE_FONT, fontSize=20, leading=28, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='ChineseHeading1', fontName=CHINESE_FONT, fontSize=14, leading=20, spaceBefore=16, spaceAfter=10, textColor=colors.HexColor('#1a1a1a')))
    styles.add(ParagraphStyle(name='ChineseHeading2', fontName=CHINESE_FONT, fontSize=12, leading=18, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='ChineseBody', fontName=CHINESE_FONT, fontSize=10, leading=16, spaceAfter=8, alignment=4, firstLineIndent=20))
    styles.add(ParagraphStyle(name='ChineseBodyCenter', fontName=CHINESE_FONT, fontSize=10, leading=16, spaceAfter=8, alignment=1))
    styles.add(ParagraphStyle(name='ChineseBodyRight', fontName=CHINESE_FONT, fontSize=10, leading=16, spaceAfter=8, alignment=2))
    styles.add(ParagraphStyle(name='ChineseSmall', fontName=CHINESE_FONT, fontSize=9, leading=14, alignment=1, textColor=colors.grey))
    return styles

styles = make_style()
pdf_path = "/Users/mashaoguang/Downloads/FireShot/finance_q1_report/2024Q1_财务分析报告.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                        rightMargin=2*cm, leftMargin=2.5*cm,
                        topMargin=2.5*cm, bottomMargin=2*cm)

def build_table(data, col_widths, header_fill=colors.HexColor('#D9E1F2')):
    t = Table(data, colWidths=col_widths)
    style = [
        ('FONTNAME', (0,0), (-1,0), CHINESE_FONT),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,0), (-1,0), header_fill),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (-1,-1), CHINESE_FONT),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]
    t.setStyle(TableStyle(style))
    return t

story = []

# 封面
story.append(Spacer(1, 4*cm))
story.append(Paragraph("2024年第一季度财务分析报告", styles['ChineseTitle']))
story.append(Spacer(1, 1*cm))
story.append(Paragraph("XX科技股份有限公司", styles['ChineseBodyCenter']))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("报告期间：2024年1月1日 — 2024年3月31日", styles['ChineseBodyCenter']))
story.append(Paragraph("编制日期：2024年4月15日", styles['ChineseBodyCenter']))
story.append(Paragraph("编制部门：财务管理部", styles['ChineseBodyCenter']))
story.append(Paragraph("<font color='#C00000'>审计状态：待审计</font>", styles['ChineseBodyCenter']))
story.append(PageBreak())

# 目录
story.append(Paragraph("目录", styles['ChineseHeading1']))
story.append(Spacer(1, 0.3*cm))
toc_items = [
    "一、财务摘要",
    "二、收入分析", "&nbsp;&nbsp;&nbsp;&nbsp;2.1 按产品线", "&nbsp;&nbsp;&nbsp;&nbsp;2.2 按区域",
    "三、成本结构",
    "四、利润分析",
    "五、现金流概况",
    "六、风险提示与建议"
]
for item in toc_items:
    story.append(Paragraph(item, styles['ChineseBody']))
story.append(PageBreak())

# 一、财务摘要
story.append(Paragraph("一、财务摘要", styles['ChineseHeading1']))
story.append(Paragraph("本季度公司整体财务表现稳健，营业收入同比增长15.9%，净利润同比增长53.7%，毛利率与净利率均实现提升。", styles['ChineseBody']))
story.append(build_table(
    [["指标", "2024Q1(万元)", "2023Q1(万元)", "同比变化"]] +
    [["营业收入", "12,580", "10,850", "+15.9%"],
     ["营业成本", "8,240", "7,320", "+12.6%"],
     ["毛利润", "4,340", "3,530", "+22.9%"],
     ["毛利率", "34.5%", "32.5%", "+2.0pp"],
     ["运营费用", "2,680", "2,450", "+9.4%"],
     ["营业利润", "1,660", "1,080", "+53.7%"],
     ["净利润", "1,245", "810", "+53.7%"],
     ["净利率", "9.9%", "7.5%", "+2.4pp"],
     ["经营现金流", "1,890", "1,420", "+33.1%"],
     ["自由现金流", "980", "650", "+50.8%"]],
    [6*cm, 3.5*cm, 3.5*cm, 3*cm]
))
story.append(PageBreak())

# 二、收入分析
story.append(Paragraph("二、收入分析", styles['ChineseHeading1']))
story.append(Paragraph("2.1 按产品线", styles['ChineseHeading2']))
story.append(build_table(
    [["产品线", "2024Q1(万元)", "同比变化", "收入占比"]] +
    [["智能硬件", "5,340", "+18.1%", "42.4%"],
     ["SaaS订阅", "4,120", "+26.8%", "32.7%"],
     ["咨询服务", "1,860", "+10.7%", "14.8%"],
     ["技术支持", "1,260", "-10.0%", "10.0%"]],
    [6*cm, 3.5*cm, 3.5*cm, 3*cm]
))
story.append(Paragraph("SaaS订阅业务增长最快（+26.8%），成为第二大收入来源；技术支持收入同比下降10.0%，主要因一次性项目减少。", styles['ChineseBody']))
story.append(Paragraph("2.2 按区域", styles['ChineseHeading2']))
story.append(build_table(
    [["区域", "2024Q1(万元)", "同比变化", "收入占比"]] +
    [["华东", "4,650", "+16.8%", "37.0%"],
     ["华南", "3,520", "+18.1%", "28.0%"],
     ["华北", "2,140", "+15.1%", "17.0%"],
     ["西南", "1,380", "+10.4%", "11.0%"],
     ["海外", "890", "+14.1%", "7.1%"]],
    [6*cm, 3.5*cm, 3.5*cm, 3*cm]
))
story.append(Paragraph("华东与华南合计贡献65%收入，海外业务稳步增长，占比提升至7.1%。", styles['ChineseBody']))
story.append(PageBreak())

# 三、成本结构
story.append(Paragraph("三、成本结构", styles['ChineseHeading1']))
story.append(Paragraph("本季度营业成本同比增长12.6%，低于收入增速，规模效应初显。研发投入增长14.0%，持续加大产品创新。", styles['ChineseBody']))
story.append(build_table(
    [["成本项目", "2024Q1(万元)", "同比变化", "占总成本比"]] +
    [["原材料", "3,120", "+9.9%", "37.9%"],
     ["人工成本", "1,860", "+10.7%", "22.6%"],
     ["制造费用", "1,240", "+10.7%", "15.0%"],
     ["研发投入", "980", "+14.0%", "11.9%"],
     ["市场营销", "720", "+10.8%", "8.7%"],
     ["管理费用", "680", "+9.7%", "8.3%"],
     ["折旧摊销", "640", "+16.4%", "7.8%"]],
    [6*cm, 3.5*cm, 3.5*cm, 3*cm]
))
story.append(PageBreak())

# 四、利润分析
story.append(Paragraph("四、利润分析", styles['ChineseHeading1']))
story.append(Paragraph("毛利率连续两个季度提升，从2023Q3的31.8%上升至2024Q1的34.5%；净利率同步改善，盈利能力显著增强。", styles['ChineseBody']))
story.append(build_table(
    [["季度", "毛利率", "净利率", "营业利润率"]] +
    [["2023Q1", "32.5%", "7.5%", "10.0%"],
     ["2023Q2", "33.2%", "8.2%", "10.8%"],
     ["2023Q3", "31.8%", "7.1%", "9.5%"],
     ["2023Q4", "34.0%", "9.5%", "12.5%"],
     ["2024Q1", "34.5%", "9.9%", "13.2%"]],
    [6*cm, 3.5*cm, 3.5*cm, 3*cm]
))
story.append(PageBreak())

# 五、现金流概况
story.append(Paragraph("五、现金流概况", styles['ChineseHeading1']))
story.append(Paragraph("经营活动净现金流同比增长33.1%，现金流质量良好；投资与筹资活动现金流出处于可控范围，现金净增加额825万元。", styles['ChineseBody']))
story.append(build_table(
    [["项目", "2024Q1(万元)", "2023Q1(万元)"]] +
    [["经营活动现金流入", "4,520", "3,860"],
     ["经营活动现金流出", "2,630", "2,440"],
     ["经营活动净现金流", "1,890", "1,420"],
     ["投资活动净现金流", "-680", "-520"],
     ["筹资活动净现金流", "-420", "-380"],
     ["汇率变动影响", "35", "20"],
     ["现金净增加额", "825", "540"]],
    [8*cm, 4*cm, 4*cm]
))
story.append(PageBreak())

# 六、风险提示与建议
story.append(Paragraph("六、风险提示与建议", styles['ChineseHeading1']))
story.append(build_table(
    [["风险类别", "风险等级", "影响描述", "应对建议"]] +
    [["市场竞争加剧", "中", "SaaS赛道竞争者增多，获客成本上升", "加大产品差异化投入，提升客户留存率"],
     ["原材料价格波动", "中", "芯片及电子元器件价格存在上涨压力", "锁定长期供应协议，优化库存管理"],
     ["汇率波动", "低", "海外收入占比提升，汇率波动影响利润", "开展外汇套期保值，分散结算币种"],
     ["人才流失", "低", "核心技术人才市场竞争激烈", "完善股权激励计划，优化研发文化"]],
    [3*cm, 2*cm, 5.5*cm, 5.5*cm]
))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>【审计声明】</b>", styles['ChineseBody']))
story.append(Paragraph("本报告所载财务数据由公司财务管理部编制，基于企业会计准则及内部会计政策。所有重大交易均已入账，报表附注完整。本报告待独立审计师审阅后出具审计意见。", styles['ChineseBody']))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("编制人：___________&nbsp;&nbsp;&nbsp;&nbsp;审核人：___________&nbsp;&nbsp;&nbsp;&nbsp;日期：2024年4月15日", styles['ChineseBodyRight']))

doc.build(story)
print(f"PDF 报告已保存: {pdf_path}")
