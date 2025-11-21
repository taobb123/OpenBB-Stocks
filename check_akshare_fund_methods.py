"""
检查 akshare 中基金相关的可用方法
"""

import akshare as ak

print("检查 akshare 中基金相关的函数...")
print("="*60)

# 获取所有 akshare 的函数
all_attrs = dir(ak)
fund_related = [attr for attr in all_attrs if 'fund' in attr.lower()]

print(f"\n找到 {len(fund_related)} 个基金相关的函数:")
for i, func_name in enumerate(fund_related, 1):
    print(f"{i}. {func_name}")
    try:
        func = getattr(ak, func_name)
        if callable(func):
            # 尝试获取函数签名
            import inspect
            try:
                sig = inspect.signature(func)
                print(f"   签名: {sig}")
            except:
                print(f"   (无法获取签名)")
    except:
        pass

# 特别检查基金相关的函数
print(f"\n{'='*60}")
print("测试几个常见的基金函数...")

test_functions = [
    'fund_em_open_fund_info',
    'fund_em_fund_name',
    'fund_em_portfolio_hold',
    'fund_open_fund_info_em',
    'fund_fund_name_em',
    'fund_portfolio_hold_em',
]

for func_name in test_functions:
    if hasattr(ak, func_name):
        print(f"\n✅ {func_name} 存在")
        func = getattr(ak, func_name)
        try:
            import inspect
            sig = inspect.signature(func)
            print(f"   签名: {sig}")
        except:
            pass
    else:
        print(f"❌ {func_name} 不存在")

