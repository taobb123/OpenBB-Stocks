import asyncio
from mcp_tool_helper import MCPToolHelper

async def get_sector_performance():
    helper = MCPToolHelper()
    
    try:
        # 尝试多个 provider
        providers = ["finviz", "yfinance", "fmp"]
        
        for provider in providers:
            print(f"\n尝试使用 {provider}...")
            data = await helper.get_sector_performance(
                group="sector",
                metric="performance",
                provider=provider
            )
            
            if data and "error" not in data:
                print(f"✅ {provider} 成功")
                if "results" in data:
                    sectors = data["results"]
                    print(f"获取到 {len(sectors)} 个行业")
                    for sector in sectors[:5]:
                        name = sector.get("name", "N/A")
                        perf = sector.get("performance_1m", 0)
                        print(f"  {name}: {perf:.2f}%")
                break
            else:
                print(f"⚠️ {provider} 失败")
        
    finally:
        await helper.close()

asyncio.run(get_sector_performance())