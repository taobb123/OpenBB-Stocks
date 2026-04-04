"""快速检测 TUSHARE_TOKEN 与 Tushare Pro 接口。用法: python scripts/test_tushare_connection.py"""
import os
import sys

def main() -> int:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        print("TUSHARE_TOKEN: 未设置（请在终端设置环境变量后再运行）")
        return 2
    print(f"TUSHARE_TOKEN: 已设置（长度 {len(token)}）")

    try:
        import tushare as ts
    except ImportError:
        print("未安装 tushare，请执行: pip install tushare")
        return 3

    ts.set_token(token)
    pro = ts.pro_api()

    df = pro.stock_basic(ts_code="600519.SH", fields="ts_code,name,industry,list_date")
    print("\n[stock_basic] 600519.SH:")
    if df is None or df.empty:
        print("  (空或失败)")
        return 4
    print(df.to_string(index=False))

    d = pro.daily(ts_code="600519.SH", start_date="20260201", end_date="20260404")
    print("\n[daily] 20260201~20260404 条数:", 0 if d is None else len(d))
    if d is not None and not d.empty:
        print(d.head(3).to_string(index=False))

    db = pro.daily_basic(ts_code="600519.SH", fields="trade_date,close,pe_ttm,pb")
    print("\n[daily_basic] 最新一条:")
    if db is not None and not db.empty:
        print(db.head(1).to_string(index=False))
    else:
        print("  (空)")

    print("\nOK: Tushare Pro 接口调用成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
