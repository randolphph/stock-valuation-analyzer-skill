#!/usr/bin/env python3
"""
Stock Valuation Analyzer — Net Cash & Ex-Cash PE Calculator
Accepts JSON input with financial data, outputs structured analysis.
"""

import json
import sys
import argparse


def calculate_net_cash(data: dict) -> dict:
    """
    Calculate net cash using the conservative framework:
    净现金 = (货币资金 + 交易性金融资产) + min(应收, 应付) + 合同负债 - 总负债
    """
    # Step 1: Cash & equivalents
    cash = data.get("货币资金", 0)
    trading_fa = data.get("交易性金融资产", 0)
    other_liquid = data.get("其他低风险流动资产", 0)  # structured deposits etc.
    cash_total = cash + trading_fa + other_liquid

    # Step 2: Working capital adjustment
    receivables = data.get("应收票据", 0) + data.get("应收账款", 0)
    payables = data.get("应付票据", 0) + data.get("应付账款", 0)
    wc_adjustment = min(receivables, payables)

    contract_liabilities = data.get("合同负债", 0)

    # Step 3: Total liabilities
    total_liabilities = data.get("负债合计", 0)

    # Net cash
    net_cash = cash_total + wc_adjustment + contract_liabilities - total_liabilities

    return {
        "现金类资产": round(cash_total, 2),
        "货币资金": round(cash, 2),
        "交易性金融资产": round(trading_fa, 2),
        "其他低风险流动资产": round(other_liquid, 2),
        "应收合计": round(receivables, 2),
        "应付合计": round(payables, 2),
        "经营性负债调整_min应收应付": round(wc_adjustment, 2),
        "合同负债": round(contract_liabilities, 2),
        "负债合计": round(total_liabilities, 2),
        "净现金": round(net_cash, 2),
    }


def calculate_valuation(data: dict, net_cash_result: dict) -> dict:
    """
    Calculate reported PE and ex-cash (real) PE.
    """
    net_profit = data.get("归母净利润", 0)
    total_shares = data.get("总股本", 0)  # in 亿股
    price = data.get("股价", 0)
    market_cap = data.get("总市值", 0)

    # Calculate market cap if not provided directly
    if market_cap == 0 and price > 0 and total_shares > 0:
        market_cap = price * total_shares

    net_cash = net_cash_result["净现金"]

    result = {
        "总市值": round(market_cap, 2),
        "归母净利润": round(net_profit, 2),
        "总股本": round(total_shares, 4),
    }

    if net_profit > 0:
        reported_pe = market_cap / net_profit
        real_pe = (market_cap - net_cash) / net_profit
        result["报表PE"] = round(reported_pe, 2)
        result["真实PE_扣除净现金"] = round(real_pe, 2)
        result["PE差异"] = round(reported_pe - real_pe, 2)
    else:
        result["报表PE"] = "N/A (负利润)"
        result["真实PE_扣除净现金"] = "N/A (负利润)"
        result["PE差异"] = "N/A"

    if market_cap > 0:
        result["现金占市值比"] = round(net_cash / market_cap * 100, 2)
    if total_shares > 0:
        result["每股净现金"] = round(net_cash / total_shares, 2)

    # Cash conversion quality
    op_cashflow = data.get("经营活动现金流净额", None)
    if op_cashflow is not None and net_profit > 0:
        result["现金收益比"] = round(op_cashflow / net_profit * 100, 2)

    # Dividend metrics
    total_dividend = data.get("现金分红总额", None)
    dps = data.get("每股分红", None)
    if total_dividend is None and dps is not None and total_shares > 0:
        total_dividend = dps * total_shares
    if total_dividend is not None:
        result["现金分红总额"] = round(total_dividend, 2)
        if market_cap > 0:
            result["股息率"] = round(total_dividend / market_cap * 100, 2)
        if net_profit > 0:
            result["分红比例"] = round(total_dividend / net_profit * 100, 2)
        if total_shares > 0:
            result["每股分红"] = round(total_dividend / total_shares, 2)

    return result


def analyze(data: dict) -> dict:
    """Full analysis pipeline."""
    net_cash_result = calculate_net_cash(data)
    valuation_result = calculate_valuation(data, net_cash_result)

    # Determine assessment
    net_cash = net_cash_result["净现金"]
    flags = []

    if net_cash < 0:
        flags.append("⚠️ 净负债：真实PE高于报表PE，经营业务实际更贵")

    cash_pct = valuation_result.get("现金占市值比", 0)
    if isinstance(cash_pct, (int, float)) and cash_pct > 20:
        flags.append("💰 现金占市值比超过20%，大量价值在现金而非经营业务")

    cash_conv = valuation_result.get("现金收益比", None)
    if cash_conv is not None:
        if cash_conv < 70:
            flags.append("🔴 现金收益比低于70%，利润质量存疑")
        elif cash_conv > 120:
            flags.append("🟢 现金收益比高于120%，利润质量优异")

    div_yield = valuation_result.get("股息率", None)
    if div_yield is not None and div_yield >= 4:
        flags.append("🟢 股息率≥4%，现金回报可观")
    payout = valuation_result.get("分红比例", None)
    if payout is not None:
        if payout >= 70:
            flags.append("💸 分红比例≥70%，公司倾向高比例分红")
        elif payout < 20:
            flags.append("📉 分红比例<20%，公司留存比例较高")

    return {
        "company": data.get("公司名称", "未知"),
        "period": data.get("报告期", "未知"),
        "net_cash_breakdown": net_cash_result,
        "valuation": valuation_result,
        "flags": flags,
    }


def main():
    parser = argparse.ArgumentParser(description="Stock Net Cash & Ex-Cash PE Analyzer")
    parser.add_argument("--input", "-i", type=str, help="Path to JSON input file")
    parser.add_argument("--json", "-j", type=str, help="JSON string input")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif args.json:
        data = json.loads(args.json)
    else:
        # Read from stdin
        data = json.load(sys.stdin)

    result = analyze(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
