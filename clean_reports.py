"""
清理报告文件脚本
用于删除生成的报告文件（investment_report_*.txt, custom_stock_analysis_*.txt 等）
"""

import os
import glob
from pathlib import Path
from datetime import datetime
import argparse


def clean_reports(
    pattern: str = None,
    days_old: int = None,
    dry_run: bool = False,
    interactive: bool = False
):
    """
    清理报告文件
    
    Args:
        pattern: 文件匹配模式，如 "*.txt" 或 "20251118*.txt"
        days_old: 只删除 N 天前的文件（None 表示删除所有匹配的文件）
        dry_run: 如果为 True，只显示将要删除的文件，不实际删除
        interactive: 如果为 True，删除前询问确认
    """
    # 默认匹配所有报告文件
    if pattern is None:
        patterns = [
            "*.txt",  # 纯数字日期格式的报告
            "investment_report_*.txt",  # 旧格式（如果有）
            "custom_stock_analysis_*.txt",  # 旧格式（如果有）
            "custom_stock_analysis_*.json",  # JSON 数据文件
            "market_analysis_result.json"  # 市场分析结果
        ]
    else:
        patterns = [pattern]
    
    current_dir = Path(".")
    deleted_count = 0
    total_size = 0
    
    print("=" * 60)
    print("🧹 报告文件清理工具")
    print("=" * 60)
    print()
    
    # 收集所有匹配的文件
    files_to_delete = []
    for pattern in patterns:
        matched_files = list(current_dir.glob(pattern))
        files_to_delete.extend(matched_files)
    
    # 去重（可能有重复）
    files_to_delete = list(set(files_to_delete))
    
    # 按时间过滤（如果指定了 days_old）
    if days_old is not None:
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        files_to_delete = [
            f for f in files_to_delete
            if f.stat().st_mtime < cutoff_time
        ]
    
    # 排序（按修改时间，最新的在前）
    files_to_delete.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    if not files_to_delete:
        print("✅ 没有找到需要清理的文件")
        return
    
    # 显示将要删除的文件
    print(f"📋 找到 {len(files_to_delete)} 个文件：")
    print()
    for f in files_to_delete:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        total_size += size
        size_str = f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
        print(f"  • {f.name} ({size_str}, 修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    print()
    print(f"📊 总计: {len(files_to_delete)} 个文件, {total_size / 1024:.2f} KB" if total_size < 1024 * 1024 else f"📊 总计: {len(files_to_delete)} 个文件, {total_size / (1024 * 1024):.2f} MB")
    print()
    
    # 如果是 dry run，只显示不删除
    if dry_run:
        print("🔍 预览模式：不会实际删除文件")
        return
    
    # 交互式确认
    if interactive:
        response = input("❓ 确认删除这些文件？(y/N): ").strip().lower()
        if response != 'y':
            print("❌ 已取消")
            return
    
    # 删除文件
    print("🗑️  正在删除...")
    for f in files_to_delete:
        try:
            f.unlink()
            deleted_count += 1
            print(f"  ✅ 已删除: {f.name}")
        except Exception as e:
            print(f"  ❌ 删除失败 {f.name}: {e}")
    
    print()
    print("=" * 60)
    print(f"✅ 清理完成！已删除 {deleted_count} 个文件")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="清理报告文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览所有报告文件（不实际删除）
  python clean_reports.py --dry-run
  
  # 删除所有报告文件
  python clean_reports.py
  
  # 交互式删除（删除前询问）
  python clean_reports.py --interactive
  
  # 只删除 7 天前的文件
  python clean_reports.py --days 7
  
  # 只删除特定模式的文件
  python clean_reports.py --pattern "20251118*.txt"
        """
    )
    
    parser.add_argument(
        "--pattern", "-p",
        type=str,
        default=None,
        help="文件匹配模式（如 '*.txt' 或 '20251118*.txt'）"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=None,
        help="只删除 N 天前的文件"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只显示将要删除的文件，不实际删除"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互式模式：删除前询问确认"
    )
    
    args = parser.parse_args()
    
    clean_reports(
        pattern=args.pattern,
        days_old=args.days,
        dry_run=args.dry_run,
        interactive=args.interactive
    )


if __name__ == "__main__":
    main()

