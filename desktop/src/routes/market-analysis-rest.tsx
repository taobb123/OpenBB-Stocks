import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Button } from "@openbb/ui-pro";
import { API_BASE_URL, getApiBaseUrlWithoutPath } from "../config/api";

interface ExtractStockCodesResponse {
	success: boolean;
	stock_codes?: string[];
	count?: number;
	error?: string;
}

interface AnalysisResponse {
	success: boolean;
	data?: any;
	report?: string;
	error?: string;
}

function MarketAnalysisRest() {
	const [mode, setMode] = useState<"file" | "full" | null>(null);
	const [fileContent, setFileContent] = useState("");
	const [extractedCodes, setExtractedCodes] = useState<string[]>([]);
	const [loading, setLoading] = useState(false);
	const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
	// 独立的状态：完整市场分析结果（固定在右侧宽区域）
	const [fullAnalysisResult, setFullAnalysisResult] = useState<AnalysisResponse | null>(null);
	const [fullAnalysisLoading, setFullAnalysisLoading] = useState(false);
	const [isFullReportModalOpen, setFullReportModalOpen] = useState(false);
	const [isFileReportModalOpen, setFileReportModalOpen] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [apiReady, setApiReady] = useState(false);
	const hasFullReport =
		!!fullAnalysisResult &&
		(Boolean(fullAnalysisResult.report) ||
			Boolean(fullAnalysisResult.error) ||
			Boolean(fullAnalysisResult.data));
	const hasFileReport =
		!!analysisResult &&
		(Boolean(analysisResult.report) ||
			Boolean(analysisResult.error) ||
			Boolean(analysisResult.data));

	const handleCopy = async (text: string) => {
		try {
			await navigator.clipboard.writeText(text);
		} catch (copyErr) {
			console.error("复制失败", copyErr);
		}
	};

	// 检查 API 是否可用
	useEffect(() => {
		const checkApi = async () => {
			try {
				// 使用健康检查端点（GET 请求，不需要 body）
				const baseUrl = getApiBaseUrlWithoutPath();
				const response = await fetch(`${baseUrl}/api/`, {
					method: "GET",
					headers: { "Content-Type": "application/json" },
				});
				
				if (response.ok) {
					setApiReady(true);
					setError(null);
				} else {
					throw new Error(`API returned ${response.status}`);
				}
			} catch (err) {
				setError(`无法连接到后端 API，请确保 Django 服务器正在运行 (${getApiBaseUrlWithoutPath()})`);
				setApiReady(false);
			}
		};
		checkApi();
	}, []);

	// 选项2：从文件读取股票代码
	const handleFileMode = async () => {
		if (!apiReady) {
			setError("API 未就绪，请确保后端服务器正在运行");
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
			const extractResponse = await fetch(`${API_BASE_URL}/extract-stock-codes/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content: fileContent }),
			});

			const extractData: ExtractStockCodesResponse = await extractResponse.json();

			if (!extractData.success || !extractData.stock_codes || extractData.count === 0) {
				setError(extractData.error || "未能从内容中提取到股票代码");
				setLoading(false);
				return;
			}

			setExtractedCodes(extractData.stock_codes);

			// 步骤2：运行分析
			const analyzeResponse = await fetch(`${API_BASE_URL}/analyze-custom-stocks/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					stock_codes: extractData.stock_codes,
					market_type: "A股",
				}),
			});

			const analysisData: AnalysisResponse = await analyzeResponse.json();
			setAnalysisResult(analysisData);
		} catch (err: any) {
			setError(err.message || "分析失败，请检查后端服务器是否运行");
		} finally {
			setLoading(false);
		}
	};

	// 选项4：运行完整市场分析（结果固定在左侧栏）
	const handleFullAnalysis = async () => {
		if (!apiReady) {
			setError("API 未就绪，请确保后端服务器正在运行");
			return;
		}

		setFullAnalysisLoading(true);
		setError(null);
		// 不清除之前的完整分析结果，保持显示

		try {
			const response = await fetch(`${API_BASE_URL}/run-full-analysis/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					index_query: "China",
					market_type: "A股",
				}),
			});

			if (!response.ok) {
				throw new Error(`API 错误: ${response.status}`);
			}

			const data: AnalysisResponse = await response.json();
			// 将结果保存到独立的状态中，不会因为切换功能而消失
			setFullAnalysisResult(data);
		} catch (err: any) {
			setError(err.message || "分析失败，请检查后端服务器是否运行");
		} finally {
			setFullAnalysisLoading(false);
		}
	};

	return (
		<div className="p-6 max-w-[1600px] mx-auto">
			<h1 className="text-3xl font-bold mb-6 text-black">市场分析系统 (REST API)</h1>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div className="space-y-6 lg:h-[calc(100vh-5rem)] lg:overflow-y-auto lg:pr-2">

			{/* API 状态提示 */}
			{!apiReady && (
				<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
					<p className="text-yellow-900">
						⚠️ 无法连接到后端 API。请确保：
						<br />
						1. Django 服务器正在运行：<code className="bg-yellow-100 text-yellow-900 px-2 py-1 rounded font-mono">python manage.py runserver</code>
						<br />
						2. 服务器地址：<code className="bg-yellow-100 text-yellow-900 px-2 py-1 rounded font-mono">{getApiBaseUrlWithoutPath()}</code>
						<br />
						3. 如需修改端口，请设置环境变量 <code className="bg-yellow-100 text-yellow-900 px-2 py-1 rounded font-mono">VITE_API_BASE_URL</code>
					</p>
				</div>
			)}

			{/* 模式选择 */}
			{!mode && (
				<div className="space-y-4">
					<div className="bg-white rounded-lg shadow p-6">
						<h2 className="text-xl font-semibold mb-4 text-black">请选择分析模式：</h2>
						<div className="space-y-3">
							<Button
								onClick={() => setMode("file")}
								className="w-full text-black font-medium"
								variant="default"
								disabled={!apiReady}
								style={{ 
									color: apiReady ? '#000000' : '#9ca3af',
									backgroundColor: apiReady ? '#ffffff' : '#f3f4f6',
									border: '2px solid #d1d5db'
								}}
							>
								2. 从文件读取股票代码
							</Button>
							<Button
								onClick={() => setMode("full")}
								className="w-full text-black font-medium"
								variant="default"
								disabled={!apiReady}
								style={{ 
									color: apiReady ? '#000000' : '#9ca3af',
									backgroundColor: apiReady ? '#ffffff' : '#f3f4f6',
									border: '2px solid #d1d5db'
								}}
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
					<div className="bg-white rounded-lg shadow p-6">
						<div className="flex justify-between items-center mb-4">
							<h2 className="text-xl font-semibold text-black">从文件读取股票代码</h2>
							<Button 
								onClick={() => setMode(null)} 
								variant="outline"
								className="text-black border-gray-300 hover:bg-gray-50"
								style={{ 
									color: '#000000',
									borderColor: '#d1d5db'
								}}
							>
								返回
							</Button>
						</div>

						<div className="space-y-4">
							<div>
								<label className="block text-sm font-medium mb-2 text-black">
									粘贴股票代码内容（支持任意格式，系统会自动提取6位数字代码）：
								</label>
								<textarea
									value={fileContent}
									onChange={(e) => setFileContent(e.target.value)}
									className="w-full h-48 p-3 border-2 border-gray-300 rounded-lg bg-white text-base font-normal focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm transition-all"
									style={{ 
										color: '#000000',
										caretColor: '#3b82f6',
										backgroundColor: '#ffffff',
										lineHeight: '1.5'
									}}
									placeholder="例如：立讯精密（002475）、歌尔股份（002241）..."
								/>
							</div>

							{extractedCodes.length > 0 && (
								<div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
									<p className="text-sm font-medium mb-2 text-blue-900">
										已提取 {extractedCodes.length} 个股票代码：
									</p>
									<div className="flex flex-wrap gap-2">
										{extractedCodes.map((code, idx) => (
											<span
												key={idx}
												className="px-2 py-1 bg-blue-100 rounded text-sm text-blue-900 font-mono"
											>
												{code}
											</span>
										))}
									</div>
								</div>
							)}

							<Button
								onClick={handleFileMode}
								disabled={loading || !fileContent.trim() || !apiReady}
								className="w-full text-white font-medium"
								style={{ 
									color: '#ffffff',
									backgroundColor: loading || !fileContent.trim() || !apiReady ? '#9ca3af' : '#3b82f6'
								}}
							>
								{loading ? "分析中..." : "开始分析"}
							</Button>
						</div>
					</div>
				</div>
			)}

					{/* 选项4：完整分析模式 */}
					{mode === "full" && (
						<div className="space-y-4">
							<div className="bg-white rounded-lg shadow p-6">
								<div className="flex justify-between items-center mb-4">
									<h2 className="text-xl font-semibold text-black">运行完整市场分析</h2>
									<Button 
										onClick={() => setMode(null)} 
										variant="outline"
										className="text-black border-gray-300 hover:bg-gray-50"
										style={{ 
											color: '#000000',
											borderColor: '#d1d5db'
										}}
									>
										返回
									</Button>
								</div>

								<div className="space-y-4">
									<p className="text-gray-700">
										将自动分析市场结构，识别强势行业（仅分析到强势行业，不筛选个股）
									</p>
									<p className="text-sm text-gray-600">
										分析结果将展示在右侧宽区域，切换功能时不会消失
									</p>

									<Button
										onClick={handleFullAnalysis}
										disabled={fullAnalysisLoading || !apiReady}
										className="w-full text-white font-medium"
										style={{ 
											color: '#ffffff',
											backgroundColor: fullAnalysisLoading || !apiReady ? '#9ca3af' : '#3b82f6'
										}}
									>
										{fullAnalysisLoading ? "分析中..." : "开始完整分析"}
									</Button>
								</div>
							</div>
						</div>
					)}

			{/* 错误提示 */}
			{error && (
				<div className="bg-red-50 border border-red-200 rounded-lg p-4">
					<p className="text-red-900 font-medium">{error}</p>
				</div>
			)}

				</div>

				{/* 右侧栏：报告展示区 */}
				<div className="lg:col-span-2 grid gap-6">
					<div className="bg-white rounded-lg shadow p-6 flex flex-col min-h-[280px] max-h-[55vh]">
						<div className="flex items-center justify-between mb-4">
							<h2 className="text-xl font-semibold text-black">文件分析结果</h2>
							{hasFileReport && (
								<Button
									variant="outline"
									onClick={() => setFileReportModalOpen(true)}
									className="text-black border-gray-300 hover:bg-gray-50"
								>
									查看完整报告
								</Button>
							)}
						</div>

						{!hasFileReport && (
							<div className="text-center text-gray-500 py-12">
								使用左侧“从文件读取股票代码”并点击“开始分析”后，这里会显示结果
							</div>
						)}

						{analysisResult && hasFileReport && (
							<div className="space-y-4">
								<div className="text-right space-x-2">
									<Button
										variant="outline"
										onClick={() => analysisResult.report && handleCopy(analysisResult.report)}
										className="text-black border-gray-300 hover:bg-gray-50"
									>
										复制内容
									</Button>
									<Button
										variant="outline"
										onClick={() => setFileReportModalOpen(true)}
										className="text-black border-gray-300 hover:bg-gray-50"
									>
										弹出查看
									</Button>
								</div>
								{analysisResult.error && (
									<div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
										<p className="text-red-800">{analysisResult.error}</p>
									</div>
								)}

								{analysisResult.report && (
									<div className="bg-gray-50 rounded-lg p-4">
										<pre className="whitespace-pre-wrap text-sm font-mono overflow-auto max-h-96 text-black">
											{analysisResult.report}
										</pre>
									</div>
								)}

								{analysisResult.data && (
									<details className="mt-4">
										<summary className="cursor-pointer text-sm font-medium text-black">
											查看详细数据（JSON）
										</summary>
										<div className="mt-2 bg-gray-50 rounded-lg p-4">
											<pre className="whitespace-pre-wrap text-xs font-mono overflow-auto max-h-96 text-black">
												{JSON.stringify(analysisResult.data, null, 2)}
											</pre>
										</div>
									</details>
								)}
							</div>
						)}
					</div>

					<div className="bg-white rounded-lg shadow p-6 flex flex-col min-h-[280px] max-h-[55vh]">
						<div className="flex items-center justify-between mb-4">
							<h2 className="text-xl font-semibold text-black">完整市场分析结果</h2>
							{fullAnalysisResult?.report && (
								<div className="space-x-2">
									<Button
										variant="outline"
										onClick={() => fullAnalysisResult.report && handleCopy(fullAnalysisResult.report)}
										className="text-black border-gray-300 hover:bg-gray-50"
									>
										复制内容
									</Button>
									<Button
										variant="outline"
										onClick={() => setFullReportModalOpen(true)}
										className="text-black border-gray-300 hover:bg-gray-50"
									>
										弹出查看
									</Button>
								</div>
							)}
						</div>

						{fullAnalysisLoading && (
							<div className="text-center text-gray-600 py-12">分析中...</div>
						)}

						{!fullAnalysisLoading && !fullAnalysisResult && (
							<div className="text-center text-gray-500 py-12">
								点击左侧“运行完整市场分析”按钮查看结果
							</div>
						)}

						{fullAnalysisResult && hasFullReport && (
							<div className="space-y-4 overflow-auto pr-2" style={{ scrollbarWidth: "thin" }}>
								{fullAnalysisResult.error && (
									<div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
										<p className="text-red-900 font-medium text-sm">
											{fullAnalysisResult.error}
										</p>
									</div>
								)}

								{fullAnalysisResult.success && fullAnalysisResult.report && (
									<div className="space-y-4 h-full">
										<div className="bg-gray-50 rounded-lg p-4">
											<pre className="whitespace-pre-wrap text-sm font-mono text-black">
												{fullAnalysisResult.report}
											</pre>
										</div>

										{fullAnalysisResult.data && (
											<details className="mt-4">
												<summary className="cursor-pointer text-sm font-medium text-black">
													查看详细数据（JSON）
												</summary>
												<div className="mt-2 bg-gray-50 rounded-lg p-4 max-h-[400px] overflow-y-auto">
													<pre className="whitespace-pre-wrap text-xs font-mono text-black">
														{JSON.stringify(fullAnalysisResult.data, null, 2)}
													</pre>
												</div>
											</details>
										)}
									</div>
								)}
							</div>
						)}
					</div>
				</div>
			</div>

			{/* 文件分析弹窗 */}
			{isFileReportModalOpen && analysisResult?.report && (
				<div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
					<div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full h-[70vh] flex flex-col">
						<div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
							<h3 className="text-lg font-semibold text-black">文件分析完整报告</h3>
							<div className="space-x-2">
								<Button
									variant="outline"
									onClick={() => handleCopy(analysisResult.report!)}
									className="text-black border-gray-300 hover:bg-gray-50"
								>
									复制内容
								</Button>
								<Button
									variant="outline"
									onClick={() => setFileReportModalOpen(false)}
									className="text-black border-gray-300 hover:bg-gray-50"
								>
									关闭
								</Button>
							</div>
						</div>
						<div className="flex-1 overflow-auto p-4 bg-gray-50 space-y-4">
							<pre className="whitespace-pre-wrap text-sm font-mono text-black">
								{analysisResult.report}
							</pre>
							{analysisResult.data && (
								<div>
									<h4 className="text-sm font-medium text-black mb-2">JSON 数据</h4>
									<pre className="whitespace-pre-wrap text-xs font-mono text-black bg-white rounded-lg p-3">
										{JSON.stringify(analysisResult.data, null, 2)}
									</pre>
								</div>
							)}
						</div>
					</div>
				</div>
			)}

			{/* 完整市场分析弹窗 */}
			{isFullReportModalOpen && fullAnalysisResult?.report && (
				<div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
					<div className="bg-white rounded-lg shadow-2xl max-w-5xl w-full h-[80vh] flex flex-col">
						<div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
							<h3 className="text-lg font-semibold text-black">完整分析报告</h3>
							<div className="space-x-2">
								<Button
									variant="outline"
									onClick={() => handleCopy(fullAnalysisResult.report!)}
									className="text-black border-gray-300 hover:bg-gray-50"
								>
									复制内容
								</Button>
								<Button
									variant="outline"
									onClick={() => setFullReportModalOpen(false)}
									className="text-black border-gray-300 hover:bg-gray-50"
								>
									关闭
								</Button>
							</div>
						</div>
						<div className="flex-1 overflow-auto p-4 bg-gray-50">
							<pre className="whitespace-pre-wrap text-sm font-mono text-black">
								{fullAnalysisResult.report}
							</pre>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

export const Route = createFileRoute("/market-analysis-rest")({
	component: MarketAnalysisRest,
});

