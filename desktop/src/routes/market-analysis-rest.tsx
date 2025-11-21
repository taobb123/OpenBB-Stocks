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
			Boolean(analysisResult.data) ||
			analysisResult.success !== undefined); // 只要有响应就显示

	const handleCopy = async (text: string) => {
		try {
			await navigator.clipboard.writeText(text);
		} catch (copyErr) {
			console.error("复制失败", copyErr);
		}
	};

	// 检查 API 是否可用
	const checkApi = async () => {
		try {
			// 使用健康检查端点（GET 请求，不需要 body）
			const baseUrl = getApiBaseUrlWithoutPath();
			const healthCheckUrl = `${baseUrl}/api/`;
			console.log(`检查 API 连接: ${healthCheckUrl}`);
			
			const response = await fetch(healthCheckUrl, {
				method: "GET",
				headers: { "Content-Type": "application/json" },
			});
			
			console.log(`API 健康检查响应: ${response.status} ${response.statusText}`);
			
			if (response.ok) {
				const data = await response.json();
				console.log(`API 健康检查成功:`, data);
				setApiReady(true);
				setError(null);
				return true;
			} else {
				throw new Error(`API returned ${response.status}`);
			}
		} catch (err: any) {
			console.error("API 连接检查失败:", err);
			const errorMsg = `无法连接到后端 API，请确保 Django 服务器正在运行\n服务器地址: ${getApiBaseUrlWithoutPath()}\n错误: ${err.message || "网络错误"}`;
			setError(errorMsg);
			setApiReady(false);
			return false;
		}
	};

	useEffect(() => {
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
			console.log(`正在调用分析 API: ${API_BASE_URL}/analyze-custom-stocks/`);
			console.log(`请求数据:`, { stock_codes: extractData.stock_codes, market_type: "A股" });
			
			const analyzeResponse = await fetch(`${API_BASE_URL}/analyze-custom-stocks/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					stock_codes: extractData.stock_codes,
					market_type: "A股",
				}),
			});

			console.log(`分析 API 响应状态: ${analyzeResponse.status} ${analyzeResponse.statusText}`);

			if (!analyzeResponse.ok) {
				// 尝试解析错误响应
				let errorMessage = `HTTP ${analyzeResponse.status}`;
				let errorReport = `分析失败: HTTP ${analyzeResponse.status}`;
				
				try {
					const errorData = await analyzeResponse.json();
					errorMessage = errorData.error || errorMessage;
					errorReport = errorData.report || errorReport;
				} catch (parseError) {
					// 如果无法解析 JSON，尝试读取文本
					try {
						const errorText = await analyzeResponse.text();
						errorReport = `分析失败: HTTP ${analyzeResponse.status}\n${errorText}`;
					} catch {
						// 忽略解析错误
					}
				}
				
				setAnalysisResult({
					success: false,
					error: errorMessage,
					report: errorReport
				});
				setError(errorMessage);
			} else {
				const analysisData: AnalysisResponse = await analyzeResponse.json();
				console.log(`分析结果:`, { success: analysisData.success, hasReport: !!analysisData.report, hasError: !!analysisData.error });
				
				// 无论成功与否，都设置结果（这样报告可以显示）
				setAnalysisResult(analysisData);
				
				// 如果有错误，也设置错误状态
				if (!analysisData.success && analysisData.error) {
					setError(analysisData.error || "分析失败");
				} else {
					// 清除之前的错误
					setError(null);
				}
			}
		} catch (err: any) {
			console.error("分析错误:", err);
			const errorMessage = err.message || "分析失败，请检查后端服务器是否运行";
			const errorReport = `分析失败:\n${errorMessage}\n\n请确保:\n1. 后端服务器正在运行 (${getApiBaseUrlWithoutPath()})\n2. API 地址正确 (${API_BASE_URL})\n3. 网络连接正常\n4. 检查浏览器控制台查看详细错误信息`;
			
			// 即使出错，也尝试显示错误信息
			setAnalysisResult({
				success: false,
				error: errorMessage,
				report: errorReport
			});
			setError(errorMessage);
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
						<div className="flex justify-between items-center mb-4 gap-4">
							<h2 className="text-xl font-semibold text-black flex-shrink-0">从文件读取股票代码</h2>
							<div className="flex gap-2 flex-shrink-0">
								<Button 
									onClick={handleFileMode}
									disabled={loading || !fileContent.trim() || !apiReady}
									className="text-white font-medium whitespace-nowrap"
									title={
										!apiReady 
											? "API 未连接，请确保后端服务器正在运行。点击下方'重新检查'按钮重试。" 
											: !fileContent.trim() 
												? "请输入股票代码内容" 
												: ""
									}
									style={{ 
										color: '#ffffff',
										backgroundColor: loading || !fileContent.trim() || !apiReady ? '#9ca3af' : '#3b82f6',
										cursor: loading || !fileContent.trim() || !apiReady ? 'not-allowed' : 'pointer',
										opacity: loading || !fileContent.trim() || !apiReady ? 0.6 : 1,
										minWidth: '100px',
										paddingLeft: '16px',
										paddingRight: '16px'
									}}
								>
									{loading 
										? "分析中..." 
										: !apiReady 
											? "API未连接" 
											: !fileContent.trim()
												? "请输入内容"
												: "开始分析"}
								</Button>
								<Button 
									onClick={() => setMode(null)} 
									variant="outline"
									className="text-black border-gray-300 hover:bg-gray-50 whitespace-nowrap"
									style={{ 
										color: '#000000',
										borderColor: '#d1d5db',
										minWidth: '70px',
										paddingLeft: '16px',
										paddingRight: '16px'
									}}
								>
									返回
								</Button>
							</div>
						</div>

						<div className="space-y-4">
							{/* API 状态提示 */}
							{!apiReady && (
								<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
									<div className="flex justify-between items-start gap-3">
										<div className="flex-1 min-w-0">
											<p className="text-sm text-yellow-800 font-medium mb-2">
												⚠️ API 未连接，文件分析功能暂时不可用
											</p>
											<ul className="text-xs text-yellow-700 ml-4 list-disc space-y-1">
												<li>Django 后端服务器正在运行</li>
												<li>API 地址配置正确（当前: {getApiBaseUrlWithoutPath()}）</li>
												<li>检查浏览器控制台查看详细错误信息</li>
											</ul>
										</div>
										<Button
											onClick={async () => {
												const success = await checkApi();
												if (success) {
													setError(null);
												}
											}}
											variant="outline"
											className="text-xs whitespace-nowrap flex-shrink-0"
											style={{
												color: '#000000',
												borderColor: '#d1d5db',
												padding: '6px 14px',
												minWidth: '80px'
											}}
										>
											重新检查
										</Button>
									</div>
								</div>
							)}
							
							<div>
								<div className="flex justify-between items-center mb-2">
									<label className="block text-sm font-medium text-black leading-relaxed">
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
											style={{
												color: '#000000',
												borderColor: '#d1d5db',
												padding: '4px 12px',
												minWidth: '60px'
											}}
										>
											清空
										</Button>
									)}
								</div>
								<textarea
									value={fileContent}
									onChange={(e) => setFileContent(e.target.value)}
									className="w-full h-32 p-3 border-2 border-gray-300 rounded-lg bg-white text-base font-normal focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm transition-all resize-y"
									style={{ 
										color: '#000000',
										caretColor: '#3b82f6',
										backgroundColor: '#ffffff',
										lineHeight: '1.5',
										minHeight: '80px',
										maxHeight: '200px'
									}}
									placeholder="例如：立讯精密（002475）、歌尔股份（002241）..."
									disabled={!apiReady}
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

						{loading && (
							<div className="text-center text-gray-500 py-12">
								<div className="flex flex-col items-center space-y-2">
									<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
									<p>正在分析中，请稍候...</p>
								</div>
							</div>
						)}
						
						{!loading && !hasFileReport && (
							<div className="text-center text-gray-500 py-12">
								使用左侧"从文件读取股票代码"并点击"开始分析"后，这里会显示结果
							</div>
						)}

						{analysisResult && hasFileReport && (
							<div className="space-y-4 flex flex-col h-full">
								<div className="text-right space-x-2 flex-shrink-0">
									{analysisResult.report && (
										<>
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
										</>
									)}
								</div>
								
								{analysisResult.error && (
									<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4 flex-shrink-0">
										<p className="text-yellow-800 text-sm">
											⚠️ {analysisResult.error}
										</p>
									</div>
								)}

								{analysisResult.report ? (
									<div className="bg-gray-50 rounded-lg p-4 flex-1 overflow-auto border border-gray-200">
										<pre className="whitespace-pre-wrap text-sm font-mono text-black leading-relaxed">
											{analysisResult.report}
										</pre>
									</div>
								) : analysisResult.success === false ? (
									<div className="bg-red-50 rounded-lg p-4 flex-1 flex items-center justify-center border border-red-200">
										<p className="text-red-800 text-sm">
											❌ 分析失败，无法生成报告
											{analysisResult.error && `: ${analysisResult.error}`}
										</p>
									</div>
								) : (
									<div className="bg-gray-50 rounded-lg p-4 flex-1 flex items-center justify-center border border-gray-200">
										<p className="text-gray-500 text-sm">报告生成中...</p>
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

