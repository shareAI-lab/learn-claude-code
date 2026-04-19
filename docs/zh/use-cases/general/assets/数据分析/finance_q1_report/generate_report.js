const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

function createCell(text, width, options = {}) {
  const { bold = false, fill = null, align = AlignmentType.LEFT, colSpan = 1 } = options;
  const shading = fill ? { fill, type: ShadingType.CLEAR } : undefined;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    columnSpan: colSpan,
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text: String(text), bold, font: "SimSun", size: 21 })]
    })]
  });
}

function createHeaderRow(cells, widths) {
  return new TableRow({
    children: cells.map((text, i) => createCell(text, widths[i], { bold: true, fill: "D9E1F2", align: AlignmentType.CENTER }))
  });
}

function createDataRow(cells, widths, align = AlignmentType.LEFT) {
  return new TableRow({
    children: cells.map((text, i) => createCell(text, widths[i], { align: typeof align === 'string' ? AlignmentType.LEFT : (align[i] || AlignmentType.LEFT) }))
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "SimSun", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "SimHei" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "SimHei" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1800 }
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "XX科技股份有限公司 · 2024年第一季度财务分析报告", font: "SimSun", size: 18, color: "666666" })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "第 ", font: "SimSun", size: 18 }),
          new TextRun({ children: [PageNumber.CURRENT], font: "SimSun", size: 18 }),
          new TextRun({ text: " 页", font: "SimSun", size: 18 })
        ]
      })] })
    },
    children: [
      // 封面
      new Paragraph({ spacing: { before: 2400, after: 400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "2024年第一季度财务分析报告", bold: true, font: "SimHei", size: 52 })] }),
      new Paragraph({ spacing: { before: 400, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "XX科技股份有限公司", font: "SimHei", size: 32 })] }),
      new Paragraph({ spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "报告期间：2024年1月1日 — 2024年3月31日", font: "SimSun", size: 24 })] }),
      new Paragraph({ spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "编制日期：2024年4月15日", font: "SimSun", size: 24 })] }),
      new Paragraph({ spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "编制部门：财务管理部", font: "SimSun", size: 24 })] }),
      new Paragraph({ spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "审计状态：待审计", font: "SimSun", size: 24, color: "C00000" })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // 目录
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("目录")] }),
      new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new PageBreak()] }),

      // 一、财务摘要
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("一、财务摘要")] }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "本季度公司整体财务表现稳健，营业收入同比增长15.9%，净利润同比增长53.7%，毛利率与净利率均实现提升。", font: "SimSun", size: 24 })] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 2180, 2180, 1880],
        rows: [
          createHeaderRow(["指标", "2024Q1(万元)", "2023Q1(万元)", "同比变化"], [3120, 2180, 2180, 1880]),
          createDataRow(["营业收入", "12,580", "10,850", "+15.9%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["营业成本", "8,240", "7,320", "+12.6%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["毛利润", "4,340", "3,530", "+22.9%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["毛利率", "34.5%", "32.5%", "+2.0pp"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["运营费用", "2,680", "2,450", "+9.4%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["营业利润", "1,660", "1,080", "+53.7%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["净利润", "1,245", "810", "+53.7%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["净利率", "9.9%", "7.5%", "+2.4pp"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["经营现金流", "1,890", "1,420", "+33.1%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["自由现金流", "980", "650", "+50.8%"], [3120, 2180, 2180, 1880], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // 二、收入分析
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("二、收入分析")] }),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 按产品线")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          createHeaderRow(["产品线", "2024Q1(万元)", "同比变化", "收入占比"], [2340, 2340, 2340, 2340]),
          createDataRow(["智能硬件", "5,340", "+18.1%", "42.4%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["SaaS订阅", "4,120", "+26.8%", "32.7%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["咨询服务", "1,860", "+10.7%", "14.8%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["技术支持", "1,260", "-10.0%", "10.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "SaaS订阅业务增长最快（+26.8%），成为第二大收入来源；技术支持收入同比下降10.0%，主要因一次性项目减少。", font: "SimSun", size: 24 })] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 按区域")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          createHeaderRow(["区域", "2024Q1(万元)", "同比变化", "收入占比"], [2340, 2340, 2340, 2340]),
          createDataRow(["华东", "4,650", "+16.8%", "37.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["华南", "3,520", "+18.1%", "28.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["华北", "2,140", "+15.1%", "17.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["西南", "1,380", "+10.4%", "11.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["海外", "890", "+14.1%", "7.1%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "华东与华南合计贡献65%收入，海外业务稳步增长，占比提升至7.1%。", font: "SimSun", size: 24 })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // 三、成本结构
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("三、成本结构")] }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "本季度营业成本同比增长12.6%，低于收入增速，规模效应初显。研发投入增长14.0%，持续加大产品创新。", font: "SimSun", size: 24 })] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          createHeaderRow(["成本项目", "2024Q1(万元)", "同比变化", "占总成本比"], [2340, 2340, 2340, 2340]),
          createDataRow(["原材料", "3,120", "+9.9%", "37.9%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["人工成本", "1,860", "+10.7%", "22.6%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["制造费用", "1,240", "+10.7%", "15.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["研发投入", "980", "+14.0%", "11.9%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["市场营销", "720", "+10.8%", "8.7%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["管理费用", "680", "+9.7%", "8.3%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["折旧摊销", "640", "+16.4%", "7.8%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // 四、利润分析
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("四、利润分析")] }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "毛利率连续两个季度提升，从2023Q3的31.8%上升至2024Q1的34.5%；净利率同步改善，盈利能力显著增强。", font: "SimSun", size: 24 })] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          createHeaderRow(["季度", "毛利率", "净利率", "营业利润率"], [2340, 2340, 2340, 2340]),
          createDataRow(["2023Q1", "32.5%", "7.5%", "10.0%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["2023Q2", "33.2%", "8.2%", "10.8%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["2023Q3", "31.8%", "7.1%", "9.5%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["2023Q4", "34.0%", "9.5%", "12.5%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["2024Q1", "34.5%", "9.9%", "13.2%"], [2340, 2340, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // 五、现金流概况
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("五、现金流概况")] }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "经营活动净现金流同比增长33.1%，现金流质量良好；投资与筹资活动现金流出处于可控范围，现金净增加额825万元。", font: "SimSun", size: 24 })] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 2340, 2340],
        rows: [
          createHeaderRow(["项目", "2024Q1(万元)", "2023Q1(万元)"], [4680, 2340, 2340]),
          createDataRow(["经营活动现金流入", "4,520", "3,860"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["经营活动现金流出", "2,630", "2,440"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["经营活动净现金流", "1,890", "1,420"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["投资活动净现金流", "-680", "-520"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["筹资活动净现金流", "-420", "-380"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["汇率变动影响", "35", "20"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
          createDataRow(["现金净增加额", "825", "540"], [4680, 2340, 2340], [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT]),
        ]
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // 六、风险提示与建议
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("六、风险提示与建议")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1560, 1200, 3300, 3300],
        rows: [
          createHeaderRow(["风险类别", "风险等级", "影响描述", "应对建议"], [1560, 1200, 3300, 3300]),
          createDataRow(["市场竞争加剧", "中", "SaaS赛道竞争者增多，获客成本上升", "加大产品差异化投入，提升客户留存率"], [1560, 1200, 3300, 3300]),
          createDataRow(["原材料价格波动", "中", "芯片及电子元器件价格存在上涨压力", "锁定长期供应协议，优化库存管理"], [1560, 1200, 3300, 3300]),
          createDataRow(["汇率波动", "低", "海外收入占比提升，汇率波动影响利润", "开展外汇套期保值，分散结算币种"], [1560, 1200, 3300, 3300]),
          createDataRow(["人才流失", "低", "核心技术人才市场竞争激烈", "完善股权激励计划，优化研发文化"], [1560, 1200, 3300, 3300]),
        ]
      }),
      new Paragraph({ spacing: { before: 400, after: 200 }, children: [new TextRun({ text: "【审计声明】", bold: true, font: "SimSun", size: 24 })] }),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [new TextRun({ text: "本报告所载财务数据由公司财务管理部编制，基于企业会计准则及内部会计政策。所有重大交易均已入账，报表附注完整。本报告待独立审计师审阅后出具审计意见。", font: "SimSun", size: 24 })] }),
      new Paragraph({ spacing: { before: 400, after: 200 }, alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "编制人：___________    审核人：___________    日期：2024年4月15日", font: "SimSun", size: 24 })] }),
    ]
  }]
});

const outPath = "/Users/mashaoguang/Downloads/FireShot/finance_q1_report/2024Q1_财务分析报告.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Word 报告已保存:", outPath);
});
