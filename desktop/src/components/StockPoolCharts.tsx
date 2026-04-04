/** 股票池：解析每行代码、分页网格、收盘价走势小图（SVG） */

export type StockChartRow = {
	symbol: string;
	name?: string;
	score?: number | null;
	price_series?: { dates: string[]; close: number[] };
	error?: string;
};

const POOL_LINE = /^(\d{6})\s*$/;

/** 纯文本股票池：每行一个代码，忽略空行与 # 注释；支持行内提取 6 位数字 */
export function parsePoolFileContent(content: string): string[] {
	const out: string[] = [];
	const seen = new Set<string>();
	for (const line of content.split(/\r?\n/)) {
		const t = line.trim();
		if (!t || t.startsWith("#")) continue;
		let code: string | null = null;
		if (POOL_LINE.test(t)) {
			code = t;
		} else {
			const m = t.match(/\b(\d{6})\b/);
			if (m) code = m[1];
		}
		if (code && !seen.has(code)) {
			seen.add(code);
			out.push(code);
		}
	}
	return out;
}

function extractScore(stock: Record<string, unknown>): number | null {
	const timing = stock.timing as Record<string, unknown> | undefined;
	if (!timing) return null;
	const inner = timing.timing as Record<string, unknown> | undefined;
	if (inner && typeof inner.score === "number") return inner.score;
	if (typeof (timing as { score?: number }).score === "number") {
		return (timing as { score: number }).score;
	}
	return null;
}

export function stocksFromAnalysisData(data: unknown): StockChartRow[] {
	if (!data || typeof data !== "object") return [];
	const stocks = (data as { stocks?: unknown[] }).stocks;
	if (!Array.isArray(stocks)) return [];
	return stocks.map((s) => {
		if (!s || typeof s !== "object") {
			return { symbol: "?", error: "无效项" };
		}
		const o = s as Record<string, unknown>;
		const sym = String(o.symbol ?? "?");
		const profile = o.profile as Record<string, unknown> | undefined;
		const name =
			profile && typeof profile.name === "string" ? profile.name : undefined;
		const ps = o.price_series as StockChartRow["price_series"] | undefined;
		const err = typeof o.error === "string" ? o.error : undefined;
		return {
			symbol: sym,
			name,
			score: extractScore(o),
			price_series: ps?.dates?.length && ps?.close?.length ? ps : undefined,
			error: err,
		};
	});
}

function MiniSparkline({
	series,
}: {
	series: { dates: string[]; close: number[] };
}) {
	const w = 300;
	const h = 100;
	const pad = 6;
	const { close, dates } = series;
	if (close.length < 2) {
		return <p className="text-xs text-gray-500">数据点不足</p>;
	}
	const min = Math.min(...close);
	const max = Math.max(...close);
	const range = max - min || 1;
	const n = close.length;
	const points = close
		.map((y, i) => {
			const x = pad + (i / (n - 1)) * (w - 2 * pad);
			const yy = pad + (1 - (y - min) / range) * (h - 2 * pad);
			return `${x},${yy}`;
		})
		.join(" ");

	const first = dates[0] ?? "";
	const last = dates[dates.length - 1] ?? "";
	const lastClose = close[close.length - 1];

	return (
		<div>
			<svg
				width={w}
				height={h}
				className="block text-blue-600"
				role="img"
				aria-label="收盘价走势"
			>
				<polyline
					fill="none"
					stroke="currentColor"
					strokeWidth="1.75"
					strokeLinejoin="round"
					strokeLinecap="round"
					points={points}
				/>
			</svg>
			<div className="flex justify-between text-[11px] text-gray-500 mt-1 font-mono">
				<span>{first}</span>
				<span className="text-black font-medium">
					收盘 {lastClose.toFixed(2)}
				</span>
				<span>{last}</span>
			</div>
		</div>
	);
}

export function StockPoolChartGrid({
	stocks,
	page,
	pageSize,
	onPageChange,
}: {
	stocks: StockChartRow[];
	page: number;
	pageSize: number;
	onPageChange: (p: number) => void;
}) {
	const totalPages = Math.max(1, Math.ceil(stocks.length / pageSize));
	const safePage = Math.min(Math.max(1, page), totalPages);
	const start = (safePage - 1) * pageSize;
	const slice = stocks.slice(start, start + pageSize);

	if (stocks.length === 0) {
		return null;
	}

	return (
		<div className="bg-white rounded-lg shadow border border-gray-100 p-4">
			<div className="flex flex-wrap items-center justify-between gap-3 mb-4">
				<h2 className="text-lg font-semibold text-black">
					股票池走势（共 {stocks.length} 只）
				</h2>
				<div className="flex items-center gap-2 text-sm">
					<span className="text-gray-600">
						第 {safePage} / {totalPages} 页
					</span>
					<button
						type="button"
						disabled={safePage <= 1}
						onClick={() => onPageChange(safePage - 1)}
						className="px-3 py-1 rounded border border-gray-300 text-black disabled:opacity-40 hover:bg-gray-50"
					>
						上一页
					</button>
					<button
						type="button"
						disabled={safePage >= totalPages}
						onClick={() => onPageChange(safePage + 1)}
						className="px-3 py-1 rounded border border-gray-300 text-black disabled:opacity-40 hover:bg-gray-50"
					>
						下一页
					</button>
				</div>
			</div>

			<div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
				{slice.map((row) => (
					<div
						key={row.symbol}
						className="border border-gray-200 rounded-lg p-3 bg-gray-50/80"
					>
						<div className="flex justify-between items-start gap-2 mb-2">
							<div>
								<p className="font-mono font-semibold text-black">
									{row.symbol}
								</p>
								{row.name && (
									<p className="text-xs text-gray-600 truncate max-w-[200px]">
										{row.name}
									</p>
								)}
							</div>
							{row.score != null && (
								<span className="text-xs bg-blue-100 text-blue-900 px-2 py-0.5 rounded">
									时机 {row.score}
								</span>
							)}
						</div>
						{row.error && (
							<p className="text-xs text-red-600 mb-2">{row.error}</p>
						)}
						{row.price_series ? (
							<MiniSparkline series={row.price_series} />
						) : (
							!row.error && (
								<p className="text-xs text-gray-500">暂无 K 线序列</p>
							)
						)}
					</div>
				))}
			</div>
		</div>
	);
}
