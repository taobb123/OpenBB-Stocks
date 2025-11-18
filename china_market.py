import asyncio
from market_structure_analysis import MarketStructureAnalyzer

async def main():
    analyzer = MarketStructureAnalyzer(mcp_url="http://127.0.0.1:8002/mcp")
    # 明确指定市场类型为A股
    result = await analyzer.run_full_analysis(index_query="China", market_type="A股")
    await analyzer.close()
    return result

# 运行
result = asyncio.run(main())