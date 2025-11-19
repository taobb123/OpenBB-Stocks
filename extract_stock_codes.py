"""
从文本中提取股票代码，按照分析脚本需要的格式（每行一个）重新排列
"""

import re
import sys
import json

def extract_stock_codes(content: str) -> list[str]:
    """
    从文本内容中提取股票代码（6位数字）
    
    Args:
        content: 文本内容
    
    Returns:
        股票代码列表（已去重）
    """
    # 使用正则表达式提取所有6位数字（股票代码格式：000000-999999）
    pattern = r'\b\d{6}\b'
    stock_codes = re.findall(pattern, content)
    
    # 去重并保持顺序
    seen = set()
    unique_codes = []
    for code in stock_codes:
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)
    
    return unique_codes

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 从命令行参数读取文件路径
        filename = sys.argv[1]
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # 从标准输入读取
        content = sys.stdin.read()
    
    # 提取股票代码
    stock_codes = extract_stock_codes(content)
    
    # 输出为 JSON 格式（便于前端处理）
    print(json.dumps(stock_codes, ensure_ascii=False))

