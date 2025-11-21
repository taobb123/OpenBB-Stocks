"""
测试 akshare 概念板块接口
"""

import akshare as ak
import pandas as pd

# 测试获取概念板块列表
print("测试1: 获取概念板块列表")
try:
    concept_list = ak.stock_board_concept_name_em()
    print(f"✅ 成功获取概念板块列表，共 {len(concept_list)} 个概念")
    print(concept_list.head(10))
except Exception as e:
    print(f"❌ 获取概念板块列表失败: {e}")

# 测试获取某只股票的概念板块
print("\n测试2: 获取单只股票的概念板块")
try:
    stock_code = "600519"  # 贵州茅台
    stock_concept = ak.stock_board_concept_cons_em(symbol="国产芯片")  # 先测试获取某个概念的股票
    print(f"✅ 成功获取概念股票列表")
    print(stock_concept.head())
except Exception as e:
    print(f"❌ 获取股票概念失败: {e}")

# 测试反向查询：根据股票代码获取其所属概念
print("\n测试3: 根据股票代码获取所属概念")
try:
    # 尝试使用股票基本信息接口
    stock_info = ak.stock_individual_info_em(symbol="600519")
    print(f"✅ 获取股票信息成功")
    print(stock_info)
except Exception as e:
    print(f"❌ 获取股票信息失败: {e}")

