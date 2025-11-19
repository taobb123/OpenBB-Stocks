use crate::tauri_handlers::helpers::{RealEnvSystem, RealFileSystem, get_working_directory};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use std::fs;

#[derive(Debug, Serialize, Deserialize)]
pub struct ExtractStockCodesResponse {
    pub stock_codes: Vec<String>,
    pub count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AnalysisResponse {
    pub success: bool,
    pub data: Option<serde_json::Value>,
    pub report: Option<String>,
    pub error: Option<String>,
}

/// 提取股票代码
#[tauri::command]
pub async fn extract_stock_codes(
    content: String,
) -> Result<ExtractStockCodesResponse, String> {
    // 创建临时文件
    let temp_dir = std::env::temp_dir();
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let temp_file = temp_dir.join(format!("stock_codes_{}.txt", timestamp));
    
    // 写入内容到临时文件
    fs::write(&temp_file, &content)
        .map_err(|e| format!("Failed to write temp file: {}", e))?;
    
    // 获取工作目录
    let working_dir = get_working_directory(".")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    
    // 查找 extract_stock_codes.py 脚本
    let script_path = working_dir.join("extract_stock_codes.py");
    if !script_path.exists() {
        // 如果不在工作目录，尝试在项目根目录
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            let project_root = PathBuf::from(&home).join(".openbb_platform");
            let alt_script = project_root.join("extract_stock_codes.py");
            if alt_script.exists() {
                return extract_with_python(&alt_script, &temp_file).await;
            }
        }
        return Err(format!("extract_stock_codes.py not found at {}", script_path.display()));
    }
    
    extract_with_python(&script_path, &temp_file).await
}

async fn extract_with_python(
    script_path: &PathBuf,
    temp_file: &PathBuf,
) -> Result<ExtractStockCodesResponse, String> {
    // 运行 Python 脚本
    let output = Command::new("python")
        .arg(script_path)
        .arg(temp_file)
        .output()
        .map_err(|e| format!("Failed to execute Python script: {}", e))?;
    
    // 清理临时文件
    let _ = fs::remove_file(temp_file);
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python script failed: {}", stderr));
    }
    
    // 解析 JSON 输出
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stock_codes: Vec<String> = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Failed to parse JSON output: {}", e))?;
    
    Ok(ExtractStockCodesResponse {
        count: stock_codes.len(),
        stock_codes,
    })
}

/// 分析自定义股票列表（选项2）
#[tauri::command]
pub async fn analyze_custom_stocks(
    stock_codes: Vec<String>,
    market_type: Option<String>,
    app_handle: tauri::AppHandle,
) -> Result<AnalysisResponse, String> {
    let working_dir = get_working_directory(".")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    
    // 创建临时文件存储股票代码
    let temp_dir = std::env::temp_dir();
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let temp_file = temp_dir.join(format!("stocks_{}.txt", timestamp));
    
    // 写入股票代码（每行一个）
    let content = stock_codes.join("\n");
    fs::write(&temp_file, content)
        .map_err(|e| format!("Failed to write stock codes file: {}", e))?;
    
    // 查找 interactive_analysis.py
    let script_path = working_dir.join("interactive_analysis.py");
    if !script_path.exists() {
        return Err(format!("interactive_analysis.py not found at {}", script_path.display()));
    }
    
    // 创建 Python 脚本来运行分析
    let timestamp2 = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let analysis_script = temp_dir.join(format!("run_analysis_{}.py", timestamp2));
    let python_code = format!(
        r#"
import asyncio
import json
import sys
from pathlib import Path

# 添加工作目录到路径
sys.path.insert(0, r"{}")

from interactive_analysis import InteractiveMarketAnalyzer

async def main():
    # 读取股票代码
    with open(r"{}", "r", encoding="utf-8") as f:
        stock_symbols = [line.strip() for line in f if line.strip()]
    
    if not stock_symbols:
        print(json.dumps({{"error": "No stock codes found"}}))
        return
    
    # 创建分析器
    analyzer = InteractiveMarketAnalyzer(use_akshare=True)
    
    try:
        # 分析股票
        market_type = "{}"
        analysis = await analyzer.analyze_custom_stocks(stock_symbols, market_type=market_type)
        
        # 生成报告
        report = analyzer.format_custom_analysis_report(analysis)
        
        # 输出结果
        result = {{
            "analysis": analysis,
            "report": report
        }}
        print(json.dumps(result, ensure_ascii=False))
    finally:
        await analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())
"#,
        working_dir.display(),
        temp_file.display(),
        market_type.unwrap_or_else(|| "A股".to_string())
    );
    
    fs::write(&analysis_script, python_code)
        .map_err(|e| format!("Failed to write analysis script: {}", e))?;
    
    // 运行分析脚本
    let output = Command::new("python")
        .arg(&analysis_script)
        .output()
        .map_err(|e| format!("Failed to execute analysis script: {}", e))?;
    
    // 清理临时文件
    let _ = fs::remove_file(&temp_file);
    let _ = fs::remove_file(&analysis_script);
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Ok(AnalysisResponse {
            success: false,
            data: None,
            report: None,
            error: Some(format!("Analysis failed: {}", stderr)),
        });
    }
    
    // 解析输出
    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Failed to parse analysis result: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Ok(AnalysisResponse {
            success: false,
            data: None,
            report: None,
            error: Some(error.as_str().unwrap_or("Unknown error").to_string()),
        });
    }
    
    Ok(AnalysisResponse {
        success: true,
        data: result.get("analysis").cloned(),
        report: result.get("report").and_then(|r| r.as_str().map(|s| s.to_string())),
        error: None,
    })
}

/// 运行完整市场分析（选项4）
#[tauri::command]
pub async fn run_full_market_analysis(
    index_query: Option<String>,
    market_type: Option<String>,
    app_handle: tauri::AppHandle,
) -> Result<AnalysisResponse, String> {
    let working_dir = get_working_directory(".")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    
    // 查找 interactive_analysis.py
    let script_path = working_dir.join("interactive_analysis.py");
    if !script_path.exists() {
        return Err(format!("interactive_analysis.py not found at {}", script_path.display()));
    }
    
    // 创建 Python 脚本来运行完整分析
    let temp_dir = std::env::temp_dir();
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let analysis_script = temp_dir.join(format!("run_full_analysis_{}.py", timestamp));
    let python_code = format!(
        r#"
import asyncio
import json
import sys
from pathlib import Path

# 添加工作目录到路径
sys.path.insert(0, r"{}")

from interactive_analysis import InteractiveMarketAnalyzer

async def main():
    # 创建分析器
    analyzer = InteractiveMarketAnalyzer(use_akshare=True)
    
    try:
        # 运行完整分析
        index_query = r"{}"
        market_type = r"{}"
        result = await analyzer.analyzer.run_full_analysis(
            index_query=index_query,
            market_type=market_type,
            skip_stock_screening=True  # 跳过个股筛选和报告生成
        )
        
        # 生成报告
        from market_structure_analysis import MarketStructureAnalyzer
        report_analyzer = MarketStructureAnalyzer()
        report = report_analyzer.generate_investment_report(result)
        
        # 输出结果
        output = {{
            "analysis": result,
            "report": report
        }}
        print(json.dumps(output, ensure_ascii=False, default=str))
    finally:
        await analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())
"#,
        working_dir.display(),
        index_query.unwrap_or_else(|| "China".to_string()),
        market_type.unwrap_or_else(|| "A股".to_string())
    );
    
    fs::write(&analysis_script, python_code)
        .map_err(|e| format!("Failed to write analysis script: {}", e))?;
    
    // 运行分析脚本
    let output = Command::new("python")
        .arg(&analysis_script)
        .output()
        .map_err(|e| format!("Failed to execute analysis script: {}", e))?;
    
    // 清理临时文件
    let _ = fs::remove_file(&analysis_script);
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Ok(AnalysisResponse {
            success: false,
            data: None,
            report: None,
            error: Some(format!("Analysis failed: {}", stderr)),
        });
    }
    
    // 解析输出
    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: serde_json::Value = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Failed to parse analysis result: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Ok(AnalysisResponse {
            success: false,
            data: None,
            report: None,
            error: Some(error.as_str().unwrap_or("Unknown error").to_string()),
        });
    }
    
    Ok(AnalysisResponse {
        success: true,
        data: result.get("analysis").cloned(),
        report: result.get("report").and_then(|r| r.as_str().map(|s| s.to_string())),
        error: None,
    })
}

