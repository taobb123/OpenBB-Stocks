import { createFileRoute } from "@tanstack/react-router";
import { invoke } from "@tauri-apps/api/core";
import { useState, useEffect } from "react";
import { Button } from "@openbb/ui-pro";

// 检查 Tauri 环境是否可用
const isTauriAvailable = (): boolean => {
	if (typeof window === "undefined") return false;
	// Tauri v2 使用 window.__TAURI_INTERNALS__ 或 window.__TAURI__
	return "__TAURI__" in window || "__TAURI_INTERNALS__" in window;
};

interface ExtractStockCodesRequest {
	content: string;
}

interface ExtractStockCodesResponse {
	stock_codes: string[];
	count: number;
}

interface AnalyzeStocksRequest {
	stock_codes: string[];
	market_type?: string;
}

interface RunFullAnalysisRequest {
	index_query?: string;
	market_type?: string;
}

interface AnalysisResponse {
	success: boolean;
	data?: any;
	report?: string;
	error?: string;
}

function MarketAnalysis() {
	const [mode, setMode] = useState<"file" | "full" | null>(null);
	const [fileContent, setFileContent] = useState("");
	const [extractedCodes, setExtractedCodes] = useState<string[]>([]);
	const [loading, setLoading] = useState(false);
	const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [tauriReady, setTauriReady] = useState(false);

	// 检查 Tauri 环境是否就绪
	useEffect(() => {
		if (isTauriAvailable()) {
			setTauriReady(true);
		} else {
			setError("Tauri 环境未就绪，请确保在 Tauri 应用中运行");
		}
	}, []);

	// 选项2：从文件读取股票代码
	const handleFileMode = async () => {
		if (!tauriReady) {
			setError("Tauri 环境未就绪，请稍候再试");
			return;
		}

		if (!fileContent.trim()) {
			setError("请输入或粘贴股票代码内容");
			return;
		}

		setLoading(true);
		setError(null);
		setAnalysisResult(null);

		try {
			// 步骤1：提取股票代码
			const extractResponse = await invoke<ExtractStockCodesResponse>(
				"extract_stock_codes",
				{ content: fileContent }
			);

			if (extractResponse.count === 0) {
				setError("未能从内容中提取到股票代码");
				setLoading(false);
				return;
			}

			setExtractedCodes(extractResponse.stock_codes);

			// 步骤2：运行分析
			const analysisResponse = await invoke<AnalysisResponse>(
				"analyze_custom_stocks",
				{
					stock_codes: extractResponse.stock_codes,
					market_type: "A股",
				}
			);

			setAnalysisResult(analysisResponse);
		} catch (err: any) {
			setError(err.message || "分析失败");
		} finally {
			setLoading(false);
		}
	};

	// 选项4：运行完整市场分析
	const handleFullAnalysis = async () => {
		if (!tauriReady) {
			setError("Tauri 环境未就绪，请稍候再试");
			return;
		}

		setLoading(true);
		setError(null);
		setAnalysisResult(null);

		try {
			const response = await invoke<AnalysisResponse>("run_full_market_analysis", {
				index_query: "China",
				market_type: "A股",
			});

			setAnalysisResult(response);
		} catch (err: any) {
			setError(err.message || "分析失败");
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="p-6 max-w-6xl mx-auto">
			<h1 className="text-3xl font-bold mb-6">市场分析系统</h1>

			{/* 模式选择 */}
			{!mode && (
				<div className="space-y-4">
					<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<h2 className="text-xl font-semibold mb-4">请选择分析模式：</h2>
						<div className="space-y-3">
							<Button
								onClick={() => setMode("file")}
								className="w-full"
								variant="default"
							>
								2. 从文件读取股票代码
							</Button>
							<Button
								onClick={() => setMode("full")}
								className="w-full"
								variant="default"
							>
								4. 运行完整市场分析（自动筛选）
							</Button>
						</div>
					</div>
				</div>
			)}

			{/* 选项2：文件模式 */}
			{mode === "file" && (
				<div className="space-y-4">
					<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<div className="flex justify-between items-center mb-4">
							<h2 className="text-xl font-semibold">从文件读取股票代码</h2>
							<div className="flex gap-2">
								<Button
									onClick={handleFileMode}
									disabled={loading || !fileContent.trim()}
									className=""
								>
									{loading ? "分析中..." : "开始分析"}
								</Button>
								<Button onClick={() => setMode(null)} variant="outline">
									返回
								</Button>
							</div>
						</div>

						<div className="space-y-4">
							<div>
								<div className="flex justify-between items-center mb-2">
									<label className="block text-sm font-medium">
										粘贴股票代码内容（支持任意格式，系统会自动提取6位数字代码）：
									</label>
									{fileContent.trim() && (
										<Button
											onClick={() => {
												setFileContent("");
												setExtractedCodes([]);
											}}
											variant="outline"
											className="text-xs whitespace-nowrap flex-shrink-0"
										>
											清空
										</Button>
									)}
								</div>
								<textarea
									value={fileContent}
									onChange={(e) => setFileContent(e.target.value)}
									className="w-full h-32 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 resize-y"
									style={{
										minHeight: '80px',
										maxHeight: '200px'
									}}
									placeholder="例如：立讯精密（002475）、歌尔股份（002241）..."
								/>
							</div>

							{extractedCodes.length > 0 && (
								<div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
									<p className="text-sm font-medium mb-2">
										已提取 {extractedCodes.length} 个股票代码：
									</p>
									<div className="flex flex-wrap gap-2">
										{extractedCodes.map((code, idx) => (
											<span
												key={idx}
												className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded text-sm"
											>
												{code}
											</span>
										))}
									</div>
								</div>
							)}
						</div>
					</div>
				</div>
			)}

			{/* 选项4：完整分析模式 */}
			{mode === "full" && (
				<div className="space-y-4">
					<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
						<div className="flex justify-between items-center mb-4">
							<h2 className="text-xl font-semibold">运行完整市场分析</h2>
							<Button onClick={() => setMode(null)} variant="outline">
								返回
							</Button>
						</div>

						<div className="space-y-4">
							<p className="text-gray-600 dark:text-gray-400">
								将自动分析市场结构，识别强势行业（仅分析到强势行业，不筛选个股）
							</p>

							<Button
								onClick={handleFullAnalysis}
								disabled={loading}
								className="w-full"
							>
								{loading ? "分析中..." : "开始完整分析"}
							</Button>
						</div>
					</div>
				</div>
			)}

			{/* 错误提示 */}
			{error && (
				<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
					<p className="text-red-800 dark:text-red-200">{error}</p>
				</div>
			)}

			{/* 分析结果 */}
			{analysisResult && (
				<div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h2 className="text-xl font-semibold mb-4">分析结果</h2>

					{analysisResult.error && (
						<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
							<p className="text-red-800 dark:text-red-200">
								{analysisResult.error}
							</p>
						</div>
					)}

					{analysisResult.success && analysisResult.report && (
						<div className="space-y-4">
							<div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
								<pre className="whitespace-pre-wrap text-sm font-mono overflow-auto max-h-96">
									{analysisResult.report}
								</pre>
							</div>

							{analysisResult.data && (
								<details className="mt-4">
									<summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
										查看详细数据（JSON）
									</summary>
									<div className="mt-2 bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
										<pre className="whitespace-pre-wrap text-xs font-mono overflow-auto max-h-96">
											{JSON.stringify(analysisResult.data, null, 2)}
										</pre>
									</div>
								</details>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
}

export const Route = createFileRoute("/market-analysis")({
	component: MarketAnalysis,
});

