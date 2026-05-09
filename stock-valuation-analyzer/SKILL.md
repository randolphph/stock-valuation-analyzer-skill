---
name: stock-valuation-analyzer
description: "Analyze stock financial data to calculate net cash position and ex-cash (real) PE ratio. Use this skill whenever the user mentions: net cash calculation (净现金), ex-cash PE (扣除净现金PE/真实PE), balance sheet cash analysis, real valuation, cash-adjusted PE, or uploads financial statements (财报/年报/季报) for valuation analysis. Also trigger when the user asks about a company's 'real' or 'true' valuation, cash position analysis, or wants to compare reported PE vs adjusted PE. Covers both A-share and HK-listed companies. Even if the user just says '帮我算一下XX的真实PE' or '看看这个公司账上有多少现金', use this skill."
---

# Stock Valuation Analyzer — Net Cash & Ex-Cash PE

## Purpose

Calculate a company's **net cash position** and **ex-cash (real) PE ratio** from financial statement data. This gives a clearer picture of what you're actually paying for the operating business, stripping out the balance sheet cash hoard.

## Core Methodology

### Net Cash Calculation

The net cash formula reflects a conservative-on-liabilities, nuanced-on-assets approach:

```
净现金 = 现金类资产 + 经营性负债调整 - 总负债
```

Breaking it down:

**Step 1 — Cash & equivalents (现金类资产):**
- 货币资金 (cash and bank deposits)
- 交易性金融资产 (trading financial assets — typically low-risk wealth management products / 理财产品)
- If available: 其他流动资产 中的结构性存款或大额存单 (structured deposits or CDs classified under other current assets)

The goal is to capture all liquid, low-risk financial assets. Exclude equity investments, long-term financial assets, or anything with material credit/market risk.

**Step 2 — Working capital adjustment (经营性负债调整):**
- Add back: `min(应收账款+应收票据, 应付账款+应付票据)`
  - Rationale: for the lesser of receivables vs payables, these net out in the operating cycle. Taking the min is conservative — it counts only the portion that's truly offset.
- Add back: 合同负债 (contract liabilities / advance receipts from dealers)
  - Rationale: for companies with strong pricing power (茅台, 可口可乐 type moats), contract liabilities represent interest-free financing from downstream — a sign of strength, not a real obligation that drains cash. This is appropriate ONLY for companies where advance payments are a structural feature of their channel power.

**Step 3 — Subtract total liabilities (总负债):**
- Use total liabilities (负债合计), not just interest-bearing debt.
- This is deliberately conservative: it assumes all liabilities are "real" claims, then selectively adds back the ones that are actually advantageous (contract liabilities, working capital offsets).

**The formula in full:**
```
净现金 = (货币资金 + 交易性金融资产)
       + min(应收账款+应收票据, 应付账款+应付票据)
       + 合同负债
       - 总负债
```

> **Important nuance:** If 合同负债 is already included in 总负债 (which it always is under Chinese GAAP), adding it back is correct — you're reversing its inclusion in total liabilities because you've judged it's not a real cash drain for this type of company.

### Ex-Cash PE Calculation

```
真实PE = (总市值 - 净现金) / 归母净利润
```

Where:
- 总市值 = current stock price × total shares (总股本)
- 归母净利润 = net profit attributable to parent company shareholders (use TTM or latest annual)
- If 净现金 is negative (net debt), the real PE will be HIGHER than reported PE — the business is worth more than the market cap suggests because you're also taking on debt.

### Supplementary Metrics

Also calculate and present:
- **报表PE** (reported PE): 总市值 / 归母净利润
- **现金占市值比**: 净现金 / 总市值 × 100%
- **每股净现金**: 净现金 / 总股本
- **经营性现金流/净利润**: 经营活动现金流净额 / 归母净利润 (cash conversion quality)
- **净现金变化**: compare vs prior year if data available

## Input Handling

### From uploaded financial reports (PDF/Excel)

1. Read the pdf-reading skill at `/mnt/skills/public/pdf-reading/SKILL.md` for PDF extraction guidance
2. Extract the balance sheet (资产负债表) — look for these line items:
   - 货币资金, 交易性金融资产, 应收票据, 应收账款, 合同负债, 应付票据, 应付账款, 负债合计
   - Also find: 其他流动资产 (check notes for structured deposits)
3. Extract the income statement (利润表):
   - 归属于母公司所有者的净利润
4. Extract the cash flow statement (现金流量表):
   - 经营活动产生的现金流量净额
5. If the data is in an uploaded Excel, use pandas to read it directly

### From user-provided data in conversation

The user may paste key numbers directly. Parse them and proceed with the calculation. Ask for any missing required fields.

### Required data points (minimum)

| Field | Chinese Label | Required? |
|-------|--------------|-----------|
| Cash | 货币资金 | ✅ |
| Trading financial assets | 交易性金融资产 | ✅ (0 if absent) |
| Notes receivable | 应收票据 | ✅ (0 if absent) |
| Accounts receivable | 应收账款 | ✅ |
| Contract liabilities | 合同负债 | ✅ |
| Notes payable | 应付票据 | ✅ (0 if absent) |
| Accounts payable | 应付账款 | ✅ |
| Total liabilities | 负债合计 | ✅ |
| Net profit to parent | 归母净利润 | ✅ |
| Total shares | 总股本 | ✅ |
| Current price or market cap | 股价/总市值 | ✅ |
| Operating cash flow | 经营活动现金流净额 | Optional |

## Output

Generate a **visualization + text analysis** using the show_widget (Visualizer) tool. The output should include:

### 1. Summary Card (Visualizer)
A clean dashboard-style visual showing:
- Company name and reporting period
- Reported PE vs Real (ex-cash) PE — side by side, with color coding (green if real PE < reported PE)
- Net cash position (absolute and per-share)
- Cash as % of market cap
- Cash conversion ratio (if operating cash flow provided)

### 2. Net Cash Waterfall (Visualizer)
A waterfall-style chart showing how net cash is built up:
```
货币资金 → + 交易性金融资产 → + min(应收,应付) → + 合同负债 → - 总负债 → = 净现金
```

### 3. Text Commentary
After the visuals, provide brief prose commentary:
- Is the net cash positive or negative? What does this mean for valuation?
- How much of the market cap is "cash padding"?
- Cash conversion quality assessment
- Any red flags (e.g., large gap between profit and operating cash flow, unusual receivables)
- If net cash is negative, note that the business is actually more expensive than headline PE suggests

### Formatting notes
- All monetary values in 亿元 (hundred millions RMB) for readability
- Round to 2 decimal places
- Use Chinese labels with English in parentheses for key terms
- Color coding: green for favorable metrics, red/orange for concerns

## Edge Cases & Warnings

- **Net debt companies**: If net cash is negative, clearly flag that real PE > reported PE. The company's operating business is MORE expensive than it looks.
- **合同负债 applicability**: Only add back contract liabilities for companies where this represents genuine channel pricing power. For companies where contract liabilities are actual delivery obligations (e.g., software, construction), do NOT add them back. Ask the user if unsure about the business model.
- **Financial companies**: Banks, insurers, brokerages have fundamentally different balance sheets. This framework does not apply — warn the user and decline to calculate.
- **Negative earnings**: If 归母净利润 is negative, PE is meaningless. Report net cash position only and note that PE analysis requires positive earnings.
- **Multiple reporting periods**: If the user provides multi-year data, calculate for each period and show the trend.

## Example

**Input:** 贵州茅台 2024年年报数据
- 货币资金: 763亿
- 交易性金融资产: 711亿
- 应收票据: 0.3亿, 应收账款: 28亿
- 应付票据: 0, 应付账款: 68亿
- 合同负债: 137亿
- 负债合计: 524亿
- 归母净利润: 862亿
- 总股本: 12.56亿股
- 当前股价: 1500元

**Calculation:**
1. 现金类资产 = 763 + 711 = 1474亿
2. min(应收, 应付) = min(0.3+28, 0+68) = min(28.3, 68) = 28.3亿
3. 净现金 = 1474 + 28.3 + 137 - 524 = 1115.3亿
4. 总市值 = 1500 × 12.56 = 18840亿
5. 报表PE = 18840 / 862 = 21.9x
6. 真实PE = (18840 - 1115.3) / 862 = 20.6x
7. 现金占市值比 = 1115.3 / 18840 = 5.9%
8. 每股净现金 = 1115.3 / 12.56 = 88.8元

(Note: these are illustrative numbers, not actual figures)
