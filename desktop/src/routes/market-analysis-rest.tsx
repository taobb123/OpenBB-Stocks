import { createFileRoute } from "@tanstack/react-router";
import {
	useState,
	useEffect,
	useLayoutEffect,
	useCallback,
	useRef,
	useMemo,
	type ChangeEventHandler,
} from "react";
import { Button } from "@openbb/ui-pro";
import { API_BASE_URL, getApiBaseUrlWithoutPath } from "../config/api";
import {
	parsePoolFileContent,
	stocksFromAnalysisData,
	StockPoolChartGrid,
	type StockChartRow,
} from "../components/StockPoolCharts";

const LS_STOCK_POOL_PATH = "stocks_pool_file_path";
const DEFAULT_STOCK_POOL_PATH =
	"D:\\RunTest\\pyb124\\py_rotation_trade\\A_stocks\\ma_strategy_project\\pybroker_integration\\stocks_pool.txt";

/** 规范化 API 路径（API_BASE_URL 已含 /api 时拼接子路径） */
function apiSubpath(sub: string): string {
	const s = sub.startsWith("/") ? sub.slice(1) : sub;
	return `${API_BASE_URL.replace(/\/$/, "")}/${s}`
		.replace(/([^:]\/)\/+/g, "$1")
		.replace(":/", "://");
}

function isTauriRuntime(): boolean {
	if (typeof window === "undefined") return false;
	return "__TAURI__" in window || "__TAURI_INTERNALS__" in window;
}

function chunkArray<T>(arr: T[], size: number): T[][] {
	if (size <= 0) return [arr];
	const out: T[][] = [];
	for (let i = 0; i < arr.length; i += size) {
		out.push(arr.slice(i, i + size));
	}
	return out;
}

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

/** 切换路由后恢复「市场分析 REST」页状态（localStorage，约 5MB 上限） */
const LS_MAR_PAGE_STATE = "odp_market_analysis_rest_v1";

type PersistedMARPayload = {
	v: 1;
	mode: "file" | "full" | null;
	fileContent: string;
	extractedCodes: string[];
	analysisResult: AnalysisResponse | null;
	fullAnalysisResult: AnalysisResponse | null;
	poolCodes: string[];
	poolLoadMessage: string | null;
	chartStocks: StockChartRow[];
	chartPage: number;
	chartsPerPage: number;
	batchSize: number;
	poolFilePath: string;
};

function readPersistedMAR(): Partial<PersistedMARPayload> | null {
	if (typeof window === "undefined") return null;
	try {
		const raw = localStorage.getItem(LS_MAR_PAGE_STATE);
		if (!raw) return null;
		const o = JSON.parse(raw) as PersistedMARPayload;
		if (o?.v !== 1) return null;
		return o;
	} catch {
		return null;
	}
}

function stripHeavyForStorage(
	payload: PersistedMARPayload,
): PersistedMARPayload {
	const lightCharts: StockChartRow[] = payload.chartStocks.map((row) => {
		const { price_series: _p, ...rest } = row;
		return { ...rest };
	});
	return {
		...payload,
		analysisResult: payload.analysisResult
			? { ...payload.analysisResult, data: undefined }
			: null,
		fullAnalysisResult: payload.fullAnalysisResult
			? { ...payload.fullAnalysisResult, data: undefined }
			: null,
		chartStocks: lightCharts,
	};
}

function persistMARState(payload: PersistedMARPayload): void {
	try {
		localStorage.setItem(LS_MAR_PAGE_STATE, JSON.stringify(payload));
	} catch {
		try {
			localStorage.setItem(
				LS_MAR_PAGE_STATE,
				JSON.stringify(stripHeavyForStorage(payload)),
			);
		} catch {
			console.warn(
				"[market-analysis-rest] localStorage 空间不足，已跳过持久化（可少存一些股票走势图）",
			);
		}
	}
}

function MarketAnalysisRest() {
	const restored = useMemo(() => readPersistedMAR(), []);

	const [mode, setMode] = useState<"file" | "full" | null>(
		restored?.mode ?? null,
	);
	const [fileContent, setFileContent] = useState(restored?.fileContent ?? "");
	const [extractedCodes, setExtractedCodes] = useState<string[]>(
		restored?.extractedCodes ?? [],
	);
	const [loading, setLoading] = useState(false);
	const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(
		restored?.analysisResult ?? null,
	);
	// 独立的状态：完整市场分析结果（固定在右侧宽区域）
	const [fullAnalysisResult, setFullAnalysisResult] =
		useState<AnalysisResponse | null>(restored?.fullAnalysisResult ?? null);
	const [fullAnalysisLoading, setFullAnalysisLoading] = useState(false);
	const [isFullReportModalOpen, setFullReportModalOpen] = useState(false);
	const [isFileReportModalOpen, setFileReportModalOpen] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [apiReady, setApiReady] = useState(false);

	const [poolFilePath, setPoolFilePath] = useState(() => {
		try {
			if (restored?.poolFilePath) return restored.poolFilePath;
			return (
				localStorage.getItem(LS_STOCK_POOL_PATH) || DEFAULT_STOCK_POOL_PATH
			);
		} catch {
			return DEFAULT_STOCK_POOL_PATH;
		}
	});
	const [poolCodes, setPoolCodes] = useState<string[]>(
		restored?.poolCodes ?? [],
	);
	const [poolLoadMessage, setPoolLoadMessage] = useState<string | null>(
		restored?.poolLoadMessage ?? null,
	);
	const [chartStocks, setChartStocks] = useState<StockChartRow[]>(
		restored?.chartStocks ?? [],
	);
	const [chartPage, setChartPage] = useState(restored?.chartPage ?? 1);
	const [chartsPerPage, setChartsPerPage] = useState(
		restored?.chartsPerPage ?? 6,
	);
	const [batchSize, setBatchSize] = useState(restored?.batchSize ?? 8);
	const [batchLoading, setBatchLoading] = useState(false);
	const [batchProgress, setBatchProgress] = useState<{
		current: number;
		total: number;
	} | null>(null);
	const [stockChartJumpInput, setStockChartJumpInput] = useState("");
	const [stockChartJumpError, setStockChartJumpError] = useState<string | null>(
		null,
	);
	const [pendingStockChartJump, setPendingStockChartJump] = useState<
		string | null
	>(null);
	const poolFileInputRef = useRef<HTMLInputElement>(null);
	const analysisAbortRef = useRef<AbortController | null>(null);

	const stopAllAnalysis = useCallback(() => {
		analysisAbortRef.current?.abort();
		analysisAbortRef.current = null;
		setLoading(false);
		setBatchLoading(false);
		setFullAnalysisLoading(false);
		setBatchProgress(null);
		setError("已停止分析（已取消前端请求；若后端已开始运算，该次请求仍可能跑完）。");
	}, []);

	const analysisRunning = loading || batchLoading || fullAnalysisLoading;

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

	useEffect(() => {
		if (chartStocks.length === 0) return;
		const totalPages = Math.max(
			1,
			Math.ceil(chartStocks.length / Math.max(1, chartsPerPage)),
		);
		if (chartPage > totalPages) {
			setChartPage(totalPages);
		}
	}, [chartStocks.length, chartsPerPage, chartPage]);

	const jumpToStockChart = useCallback(() => {
		setStockChartJumpError(null);
		const digits = stockChartJumpInput.replace(/\D/g, "");
		if (digits.length < 6) {
			setStockChartJumpError("请输入 6 位股票代码（可粘贴含数字的文本，自动取前 6 位）");
			return;
		}
		const code = digits.slice(0, 6);
		const idx = chartStocks.findIndex((s) => s.symbol === code);
		if (idx < 0) {
			setStockChartJumpError(`股票池中未找到 ${code}`);
			return;
		}
		const totalPages = Math.max(
			1,
			Math.ceil(chartStocks.length / Math.max(1, chartsPerPage)),
		);
		const page = Math.min(
			totalPages,
			Math.floor(idx / Math.max(1, chartsPerPage)) + 1,
		);
		setChartPage(page);
		setPendingStockChartJump(code);
	}, [stockChartJumpInput, chartStocks, chartsPerPage]);

	useLayoutEffect(() => {
		if (!pendingStockChartJump) return;
		const code = pendingStockChartJump;
		setPendingStockChartJump(null);
		const el = document.getElementById(`mar-stock-${code}`);
		if (!el) return;
		el.scrollIntoView({ behavior: "smooth", block: "center" });
		el.classList.add("ring-2", "ring-blue-500", "ring-offset-2", "rounded-lg");
		window.setTimeout(() => {
			el.classList.remove(
				"ring-2",
				"ring-blue-500",
				"ring-offset-2",
				"rounded-lg",
			);
		}, 2000);
	}, [pendingStockChartJump, chartPage]);

	const persistTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	useEffect(() => {
		const payload: PersistedMARPayload = {
			v: 1,
			mode,
			fileContent,
			extractedCodes,
			analysisResult,
			fullAnalysisResult,
			poolCodes,
			poolLoadMessage,
			chartStocks,
			chartPage,
			chartsPerPage,
			batchSize,
			poolFilePath,
		};
		if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
		persistTimerRef.current = setTimeout(() => {
			persistTimerRef.current = null;
			persistMARState(payload);
		}, 400);
		return () => {
			if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
		};
	}, [
		mode,
		fileContent,
		extractedCodes,
		analysisResult,
		fullAnalysisResult,
		poolCodes,
		poolLoadMessage,
		chartStocks,
		chartPage,
		chartsPerPage,
		batchSize,
		poolFilePath,
	]);

	const persistPoolPath = useCallback((path: string) => {
		setPoolFilePath(path);
		try {
			localStorage.setItem(LS_STOCK_POOL_PATH, path);
		} catch {
			/* ignore */
		}
	}, []);

	const loadPoolFromText = useCallback((text: string, sourceLabel?: string) => {
		const codes = parsePoolFileContent(text);
		setPoolCodes(codes);
		const base =
			codes.length > 0
				? `已解析 ${codes.length} 只股票代码（去重后）`
				: "未解析到有效 6 位股票代码";
		setPoolLoadMessage(sourceLabel ? `${sourceLabel} — ${base}` : base);
		setChartStocks([]);
		setChartPage(1);
	}, []);

	const readPoolFromDiskPath = async () => {
		const p = poolFilePath.trim();
		if (!p) {
			setPoolLoadMessage("请先填写股票池文件路径");
			return;
		}
		if (!isTauriRuntime()) {
			setPoolLoadMessage(
				"当前在浏览器中打开：无法直接读本地路径。请使用 Tauri 桌面窗口，或点击下方「选择 .txt 文件」。",
			);
			return;
		}
		try {
			const { invoke } = await import("@tauri-apps/api/core");
			const text = await invoke<string>("read_utf8_text_file", { path: p });
			loadPoolFromText(text, `磁盘路径 ${p}`);
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : String(e);
			setPoolLoadMessage(`读取失败: ${msg}`);
		}
	};

	const onPickPoolFile: ChangeEventHandler<HTMLInputElement> = (ev) => {
		const file = ev.target.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			const text = typeof reader.result === "string" ? reader.result : "";
			loadPoolFromText(text, `文件「${file.name}」`);
		};
		reader.onerror = () =>
			setPoolLoadMessage(`读取文件失败: ${reader.error?.message ?? "未知错误"}`);
		reader.readAsText(file, "UTF-8");
		ev.target.value = "";
	};

	/** 股票池：仅走势图（后端 scope=charts，不跑时机/基本面/MCP） */
	const runBatchedPoolCharts = async () => {
		if (!apiReady) {
			setError("API 未就绪，请确保后端服务器正在运行");
			return;
		}
		if (poolCodes.length === 0) {
			setError("请先从股票池文件加载代码列表");
			return;
		}
		const size = Math.min(40, Math.max(1, batchSize));
		const chunks = chunkArray(poolCodes, size);
		analysisAbortRef.current?.abort();
		const ac = new AbortController();
		analysisAbortRef.current = ac;
		const { signal } = ac;

		setBatchLoading(true);
		setError(null);
		setBatchProgress({ current: 0, total: chunks.length });
		const merged: StockChartRow[] = [];
		try {
			for (let i = 0; i < chunks.length; i++) {
				if (signal.aborted) break;
				setBatchProgress({ current: i + 1, total: chunks.length });
				const analyzeResponse = await fetch(
					apiSubpath("analyze-custom-stocks/charts/"),
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							stock_codes: chunks[i],
							market_type: "A股",
						}),
						signal,
					},
				);
				if (signal.aborted) break;
				const analysisData: AnalysisResponse = await analyzeResponse.json();
				if (!analyzeResponse.ok || !analysisData.success) {
					const errText =
						analysisData.error ||
						`走势图批次 ${i + 1}/${chunks.length} HTTP ${analyzeResponse.status}`;
					setError(errText);
					break;
				}
				if (analysisData.data) {
					merged.push(...stocksFromAnalysisData(analysisData.data));
				}
			}
			if (merged.length > 0) {
				setChartStocks(merged);
				setChartPage(1);
			} else if (!signal.aborted && chunks.length > 0) {
				setChartStocks([]);
			}
		} catch (err: unknown) {
			if (err instanceof Error && err.name === "AbortError") {
				if (merged.length > 0) {
					setChartStocks(merged);
					setChartPage(1);
				}
				return;
			}
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setBatchLoading(false);
			setBatchProgress(null);
			if (analysisAbortRef.current === ac) {
				analysisAbortRef.current = null;
			}
		}
	};

	/** 股票池：买入/时机分析报告（后端 scope=report，无 price_series，写 Buy.txt） */
	const runBatchedPoolReport = async () => {
		if (!apiReady) {
			setError("API 未就绪，请确保后端服务器正在运行");
			return;
		}
		if (poolCodes.length === 0) {
			setError("请先从股票池文件加载代码列表");
			return;
		}
		const size = Math.min(40, Math.max(1, batchSize));
		const chunks = chunkArray(poolCodes, size);
		analysisAbortRef.current?.abort();
		const ac = new AbortController();
		analysisAbortRef.current = ac;
		const { signal } = ac;

		setBatchLoading(true);
		setError(null);
		setBatchProgress({ current: 0, total: chunks.length });
		const mergedStocks: unknown[] = [];
		const reportParts: string[] = [];
		try {
			for (let i = 0; i < chunks.length; i++) {
				if (signal.aborted) break;
				setBatchProgress({ current: i + 1, total: chunks.length });
				const analyzeResponse = await fetch(
					apiSubpath("analyze-custom-stocks/report/"),
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							stock_codes: chunks[i],
							market_type: "A股",
						}),
						signal,
					},
				);
				if (signal.aborted) break;
				const analysisData: AnalysisResponse = await analyzeResponse.json();
				if (!analyzeResponse.ok || !analysisData.success) {
					const errText =
						analysisData.error ||
						`报告批次 ${i + 1}/${chunks.length} HTTP ${analyzeResponse.status}`;
					setError(errText);
					setAnalysisResult({
						success: false,
						error: errText,
						report: analysisData.report || errText,
						data: { stocks: mergedStocks },
					});
					break;
				}
				const stocks = (analysisData.data as { stocks?: unknown[] } | undefined)
					?.stocks;
				if (stocks?.length) {
					mergedStocks.push(...stocks);
				}
				if (analysisData.report) {
					reportParts.push(analysisData.report);
				}
			}
			if (!signal.aborted && reportParts.length > 0) {
				setAnalysisResult({
					success: true,
					data: { stocks: mergedStocks },
					report: reportParts.join(
						"\n\n──────── 批次分隔 ────────\n\n",
					),
				});
				setError(null);
			}
		} catch (err: unknown) {
			if (err instanceof Error && err.name === "AbortError") {
				if (reportParts.length > 0) {
					setAnalysisResult({
						success: true,
						data: { stocks: mergedStocks },
						report: reportParts.join(
							"\n\n──────── 批次分隔 ────────\n\n",
						),
					});
				}
				return;
			}
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setBatchLoading(false);
			setBatchProgress(null);
			if (analysisAbortRef.current === ac) {
				analysisAbortRef.current = null;
			}
		}
	};

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

		analysisAbortRef.current?.abort();
		const ac = new AbortController();
		analysisAbortRef.current = ac;
		const { signal } = ac;

		setLoading(true);
		setError(null);
		setAnalysisResult(null);

		try {
			// 步骤1：提取股票代码
			// 确保 URL 格式正确
			const extractUrl = `${API_BASE_URL}/extract-stock-codes/`.replace(/\/+/g, '/').replace(':/', '://');
			console.log(`提取股票代码 URL: ${extractUrl}`);
			
			const extractResponse = await fetch(extractUrl, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content: fileContent }),
				signal,
			});

			const extractData: ExtractStockCodesResponse = await extractResponse.json();

			if (!extractData.success || !extractData.stock_codes || extractData.count === 0) {
				setError(extractData.error || "未能从内容中提取到股票代码");
				setLoading(false);
				if (analysisAbortRef.current === ac) analysisAbortRef.current = null;
				return;
			}

			setExtractedCodes(extractData.stock_codes);

			if (signal.aborted) {
				setLoading(false);
				if (analysisAbortRef.current === ac) analysisAbortRef.current = null;
				return;
			}

			// 步骤2：买入/时机分析报告（专用接口，不含走势图 price_series）
			console.log(
				`正在调用分析 API: ${apiSubpath("analyze-custom-stocks/report/")}`,
			);
			console.log(`请求数据:`, { stock_codes: extractData.stock_codes, market_type: "A股" });
			
			const analyzeResponse = await fetch(
				apiSubpath("analyze-custom-stocks/report/"),
				{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					stock_codes: extractData.stock_codes,
					market_type: "A股",
				}),
				signal,
			},
			);

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
			if (err?.name === "AbortError") {
				return;
			}
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
			if (analysisAbortRef.current === ac) {
				analysisAbortRef.current = null;
			}
		}
	};

	// 选项4：运行完整市场分析（结果固定在左侧栏）
	const handleFullAnalysis = async () => {
		if (!apiReady) {
			setError("API 未就绪，请确保后端服务器正在运行");
			return;
		}

		analysisAbortRef.current?.abort();
		const ac = new AbortController();
		analysisAbortRef.current = ac;
		const { signal } = ac;

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
				signal,
			});

			if (!response.ok) {
				throw new Error(`API 错误: ${response.status}`);
			}

			const data: AnalysisResponse = await response.json();
			// 将结果保存到独立的状态中，不会因为切换功能而消失
			setFullAnalysisResult(data);
		} catch (err: any) {
			if (err?.name === "AbortError") {
				return;
			}
			setError(err.message || "分析失败，请检查后端服务器是否运行");
		} finally {
			setFullAnalysisLoading(false);
			if (analysisAbortRef.current === ac) {
				analysisAbortRef.current = null;
			}
		}
	};

	return (
		<div className="flex flex-col min-h-0 w-full max-w-[1600px] mx-auto p-6 pb-12 box-border">
			<h1 className="text-3xl font-bold mb-6 text-black shrink-0">
				市场分析系统 (REST API)
			</h1>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
				<div className="space-y-6 lg:pr-2">
			{analysisRunning && (
				<div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-sm">
					<p className="text-sm text-amber-950 font-medium">
						分析进行中，可随时停止（将取消后续请求；当前批次若已发出则可能仍在后端执行）。
					</p>
					<Button
						type="button"
						onClick={stopAllAnalysis}
						variant="outline"
						className="shrink-0 border-red-300 text-red-800 hover:bg-red-50 font-medium"
						style={{
							color: "#991b1b",
							borderColor: "#fca5a5",
						}}
					>
						停止分析
					</Button>
				</div>
			)}

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

							<div className="border-t border-gray-200 pt-4 mt-4 space-y-3">
								<h3 className="text-sm font-semibold text-black">
									股票池批量监控（纯文本每行一个代码）
								</h3>
								<p className="text-xs text-gray-600 leading-relaxed">
									在 Tauri 桌面窗口中可使用下方路径直接读取本机文件；若用浏览器打开本页，请使用「选择
									.txt」。股票池与右侧「买入分析」已拆成两个后端接口：「仅走势图」只拉 K
									线（更快）；「分批报告」跑时机/基本面并写入 Buy.txt。二者可分开执行。
								</p>
								<div>
									<label className="block text-xs font-medium text-gray-700 mb-1">
										股票池文件路径（可修改，会记住到本机）
									</label>
									<input
										type="text"
										value={poolFilePath}
										onChange={(e) => persistPoolPath(e.target.value)}
										className="w-full border-2 border-gray-300 rounded-lg px-3 py-2 text-sm font-mono text-black bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
										placeholder={DEFAULT_STOCK_POOL_PATH}
									/>
								</div>
								<div className="flex flex-wrap gap-2 items-center">
									<input
										ref={poolFileInputRef}
										type="file"
										accept=".txt,text/plain"
										className="hidden"
										onChange={onPickPoolFile}
									/>
									<Button
										type="button"
										onClick={readPoolFromDiskPath}
										variant="outline"
										className="text-black border-gray-300"
										style={{
											color: "#000000",
											borderColor: "#d1d5db",
										}}
									>
										从路径读取
									</Button>
									<Button
										type="button"
										onClick={() => poolFileInputRef.current?.click()}
										variant="outline"
										className="text-black border-gray-300"
										style={{
											color: "#000000",
											borderColor: "#d1d5db",
										}}
									>
										选择 .txt 文件
									</Button>
									{poolCodes.length > 0 && (
										<span className="text-sm text-gray-700">
											已加载 {poolCodes.length} 只
										</span>
									)}
								</div>
								{poolLoadMessage && (
									<p className="text-xs text-blue-900 bg-blue-50 border border-blue-100 rounded px-2 py-2">
										{poolLoadMessage}
									</p>
								)}
								<div className="grid grid-cols-2 sm:grid-cols-2 gap-4 max-w-lg">
									<div>
										<label className="block text-xs text-gray-600 mb-1">
											每批分析数量（1–40）
										</label>
										<input
											type="number"
											min={1}
											max={40}
											value={batchSize}
											onChange={(e) =>
												setBatchSize(
													Math.min(
														40,
														Math.max(1, Number(e.target.value) || 8),
													),
												)
											}
											className="w-full border border-gray-300 rounded px-2 py-1 text-sm text-black"
										/>
									</div>
									<div>
										<label className="block text-xs text-gray-600 mb-1">
											每页走势图数量
										</label>
										<input
											type="number"
											min={1}
											max={24}
											value={chartsPerPage}
											onChange={(e) =>
												setChartsPerPage(
													Math.min(
														24,
														Math.max(1, Number(e.target.value) || 6),
													),
												)
											}
											className="w-full border border-gray-300 rounded px-2 py-1 text-sm text-black"
										/>
									</div>
								</div>
								<div className="flex flex-col gap-2 max-w-md">
									<Button
										type="button"
										onClick={runBatchedPoolCharts}
										disabled={
											batchLoading ||
											poolCodes.length === 0 ||
											!apiReady
										}
										className="text-white font-medium w-full"
										style={{
											color: "#ffffff",
											backgroundColor:
												batchLoading ||
												poolCodes.length === 0 ||
												!apiReady
													? "#9ca3af"
													: "#059669",
										}}
									>
										{batchLoading && batchProgress
											? `走势批次 ${batchProgress.current}/${batchProgress.total}…`
											: "分批获取走势图（仅 K 线）"}
									</Button>
									<Button
										type="button"
										onClick={runBatchedPoolReport}
										disabled={
											batchLoading ||
											poolCodes.length === 0 ||
											!apiReady
										}
										className="text-white font-medium w-full"
										style={{
											color: "#ffffff",
											backgroundColor:
												batchLoading ||
												poolCodes.length === 0 ||
												!apiReady
													? "#9ca3af"
													: "#2563eb",
										}}
									>
										{batchLoading && batchProgress
											? `报告批次 ${batchProgress.current}/${batchProgress.total}…`
											: "分批生成买入分析报告（右侧）"}
									</Button>
								</div>
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
				<div className="lg:col-span-2 grid gap-6 min-h-0">
					<div className="bg-white rounded-lg shadow p-6 flex flex-col min-h-[280px] max-h-[min(55vh,32rem)]">
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

					<div className="bg-white rounded-lg shadow p-6 flex flex-col min-h-[280px] max-h-[min(55vh,32rem)]">
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

			{chartStocks.length > 0 && (
				<div className="mt-8 w-full space-y-3">
					<div className="flex flex-wrap items-end gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
						<div className="min-w-[200px] flex-1 text-gray-900">
							<label
								htmlFor="mar-stock-chart-jump"
								className="mb-1 block text-xs font-medium text-gray-600"
							>
								跳转到股票小图（代码）
							</label>
							<input
								id="mar-stock-chart-jump"
								type="text"
								inputMode="numeric"
								autoComplete="off"
								placeholder="例如 600519"
								value={stockChartJumpInput}
								onChange={(e) => {
									setStockChartJumpInput(e.target.value);
									setStockChartJumpError(null);
								}}
								onKeyDown={(e) => {
									if (e.key === "Enter") {
										e.preventDefault();
										jumpToStockChart();
									}
								}}
								className="w-full rounded border border-gray-300 px-3 py-2 text-sm font-mono text-inherit caret-gray-900 placeholder:text-gray-500 !bg-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
								style={{ color: "inherit" }}
							/>
						</div>
						<Button
							type="button"
							variant="default"
							onClick={jumpToStockChart}
							className="text-black"
						>
							跳转
						</Button>
						{stockChartJumpError && (
							<p className="w-full text-sm text-red-600">{stockChartJumpError}</p>
						)}
					</div>
					<StockPoolChartGrid
						stocks={chartStocks}
						page={chartPage}
						pageSize={chartsPerPage}
						onPageChange={setChartPage}
					/>
				</div>
			)}

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

