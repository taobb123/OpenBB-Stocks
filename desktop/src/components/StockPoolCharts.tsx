/** 股票池：解析每行代码、分页网格、K 线蜡烛小图（SVG，红涨绿跌） */

import { useState } from "react";

export type PriceSeriesLine = { dates: string[]; close: number[] };
export type PriceSeriesOhlc = {
	dates: string[];
	open: number[];
	high: number[];
	low: number[];
	close: number[];
	volume: number[];
};

export type StockChartRow = {
	symbol: string;
	name?: string;
	score?: number | null;
	price_series?: PriceSeriesLine | PriceSeriesOhlc;
	error?: string;
};

const POOL_LINE = /^(\d{6})\s*$/;

function isOhlcSeries(
	s: PriceSeriesLine | PriceSeriesOhlc,
): s is PriceSeriesOhlc {
	if (!("open" in s) || !("high" in s) || !("low" in s) || !("volume" in s)) return false;
	const n = s.dates.length;
	if (n < 2) return false;
	return (
		s.open.length === n &&
		s.high.length === n &&
		s.low.length === n &&
		s.close.length === n &&
		s.volume.length === n
	);
}

function normalizePriceSeries(
	raw: unknown,
): PriceSeriesLine | PriceSeriesOhlc | undefined {
	if (!raw || typeof raw !== "object") return undefined;
	const p = raw as Record<string, unknown>;
	const dates = p.dates;
	const close = p.close;
	if (!Array.isArray(dates) || !Array.isArray(close)) return undefined;
	const n = dates.length;
	if (n < 2 || close.length !== n) return undefined;
	const op = p.open;
	const hi = p.high;
	const lo = p.low;
	const vol = p.volume;
	if (
		Array.isArray(op) &&
		Array.isArray(hi) &&
		Array.isArray(lo) &&
		Array.isArray(vol) &&
		op.length === n &&
		hi.length === n &&
		lo.length === n &&
		vol.length === n
	) {
		return {
			dates: dates as string[],
			open: (op as number[]).map(Number),
			high: (hi as number[]).map(Number),
			low: (lo as number[]).map(Number),
			close: (close as number[]).map(Number),
			volume: (vol as number[]).map((x) => Math.max(0, Number(x))),
		};
	}
	return {
		dates: dates as string[],
		close: (close as number[]).map(Number),
	};
}

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
		const ps = normalizePriceSeries(o.price_series);
		const err = typeof o.error === "string" ? o.error : undefined;
		return {
			symbol: sym,
			name,
			score: extractScore(o),
			price_series: ps,
			error: err,
		};
	});
}

/** A 股：红涨绿跌 */
const C_UP = "#ef4444";
const C_UP_DARK = "#b91c1c";
const C_DOWN = "#22c55e";
const C_DOWN_DARK = "#15803d";
const C_FLAT = "#94a3b8";

/** 简单移动平均线：索引 i 处为 close[i-period+1..i] 的均值，前 period-1 根为 null */
function smaSeries(close: number[], period: number): (number | null)[] {
	const n = close.length;
	const out: (number | null)[] = Array.from({ length: n }, () => null);
	for (let i = period - 1; i < n; i++) {
		let sum = 0;
		for (let k = i - period + 1; k <= i; k++) {
			sum += close[k]!;
		}
		out[i] = sum / period;
	}
	return out;
}

function maPolylinePoints(
	ma: (number | null)[],
	pad: number,
	slotW: number,
	yPx: (p: number) => number,
): string {
	const parts: string[] = [];
	for (let i = 0; i < ma.length; i++) {
		const v = ma[i];
		if (v == null) continue;
		const x = pad + (i + 0.5) * slotW;
		parts.push(`${x},${yPx(v)}`);
	}
	return parts.join(" ");
}

const MA10_STROKE = "#ca8a04";
const MA5_STROKE = "#9333ea";

function MiniCandlestick({ series }: { series: PriceSeriesOhlc }) {
	const [hoverIndex, setHoverIndex] = useState<number | null>(null);
	const w = 300;
	const h = 120;
	const pad = 6;
	const gap = 4;
	const volumeH = 28;
	const priceTop = pad;
	const priceBottom = h - pad - volumeH - gap;
	const priceH = priceBottom - priceTop;
	const volTop = priceBottom + gap;
	const volBottom = h - pad;
	const volH = volBottom - volTop;
	const { dates, open, high, low, close, volume } = series;
	const n = close.length;
	if (n < 2) {
		return <p className="text-xs text-gray-500">数据点不足</p>;
	}
	const ymin = Math.min(...low);
	const ymax = Math.max(...high);
	const range = ymax - ymin || 1;
	const slotW = (w - 2 * pad) / n;
	const barW = Math.max(0.5, Math.min(slotW * 0.7, 10));
	const maxVol = Math.max(...volume, 0);

	const yPx = (p: number) => priceTop + (1 - (p - ymin) / range) * priceH;

	const first = dates[0] ?? "";
	const last = dates[dates.length - 1] ?? "";

	const bars = open.map((o, i) => {
		const hhi = high[i]!;
		const llo = low[i]!;
		const c = close[i]!;
		const v = volume[i] ?? 0;
		const yH = yPx(hhi);
		const yL = yPx(llo);
		const yO = yPx(o);
		const yC = yPx(c);
		const xCenter = pad + (i + 0.5) * slotW;
		const isFlat = Math.abs(c - o) < 1e-6 || Math.abs(yO - yC) < 0.4;
		const isBearish = !isFlat && c < o;
		let fill: string;
		let stroke: string;
		if (isFlat) {
			fill = C_FLAT;
			stroke = C_FLAT;
		} else if (c > o) {
			fill = C_UP;
			stroke = C_UP_DARK;
		} else {
			fill = C_DOWN;
			stroke = C_DOWN_DARK;
		}
		const top = Math.min(yO, yC);
		const bot = Math.max(yO, yC);
		const bodyH = Math.max(bot - top, 0.5);
		const vNorm = maxVol > 0 ? v / maxVol : 0;
		const vBarH = Math.max(0.5, vNorm * volH);
		return {
			i,
			o,
			c,
			llo,
			hhi,
			yH,
			yL,
			xCenter,
			top,
			bodyH,
			barW,
			fill,
			stroke,
			isFlat,
			isBearish,
			v,
			volY: volBottom - vBarH,
			volH: vBarH,
		};
	});

	const displayIndex = hoverIndex ?? n - 1;
	const displayDate = dates[displayIndex] ?? "";
	const displayClose = close[displayIndex]!;
	const displayLow = low[displayIndex]!;
	const displayVol = volume[displayIndex] ?? 0;
	const hoveredBar = bars[displayIndex];
	const isHovering = hoverIndex != null;

	const ma10 = smaSeries(close, 10);
	const ma5 = smaSeries(close, 5);
	const ma10Pts = maPolylinePoints(ma10, pad, slotW, yPx);
	const ma5Pts = maPolylinePoints(ma5, pad, slotW, yPx);

	const footerLabel = (() => {
		if (!hoveredBar) {
			return `收盘 ${displayClose.toFixed(2)} · 量 ${displayVol.toFixed(0)}`;
		}
		if (hoveredBar.isBearish) {
			return `最低 ${displayLow.toFixed(2)} · 收盘 ${displayClose.toFixed(2)} · 量 ${displayVol.toFixed(0)}`;
		}
		if (hoveredBar.isFlat) {
			return `收盘 ${displayClose.toFixed(2)} · 量 ${displayVol.toFixed(0)}`;
		}
		return `收盘 ${displayClose.toFixed(2)} · 量 ${displayVol.toFixed(0)}`;
	})();

	return (
		<div>
			<svg
				width={w}
				height={h}
				className="block cursor-crosshair"
				role="img"
				aria-label="K 线蜡烛图、10 日与 5 日均线及成交量"
				onMouseLeave={() => setHoverIndex(null)}
			>
				{bars.map((b) => (
					<g key={b.i} pointerEvents="none">
						<line
							x1={b.xCenter}
							x2={b.xCenter}
							y1={b.yH}
							y2={b.yL}
							stroke={b.stroke}
							strokeWidth={1}
						/>
						{b.isFlat ? (
							<line
								x1={b.xCenter - b.barW / 2}
								x2={b.xCenter + b.barW / 2}
								y1={b.top}
								y2={b.top}
								stroke={b.stroke}
								strokeWidth={1.25}
							/>
						) : (
							<rect
								x={b.xCenter - b.barW / 2}
								y={b.top}
								width={b.barW}
								height={b.bodyH}
								fill={b.fill}
								stroke={b.stroke}
								strokeWidth={0.5}
							/>
						)}
						<rect
							x={b.xCenter - b.barW / 2}
							y={b.volY}
							width={b.barW}
							height={b.volH}
							fill={b.fill}
							opacity={0.55}
						/>
					</g>
				))}
				{ma5Pts ? (
					<polyline
						fill="none"
						stroke={MA5_STROKE}
						strokeWidth={1.35}
						strokeLinejoin="round"
						strokeLinecap="round"
						points={ma5Pts}
					/>
				) : null}
				{ma10Pts ? (
					<polyline
						fill="none"
						stroke={MA10_STROKE}
						strokeWidth={1.35}
						strokeLinejoin="round"
						strokeLinecap="round"
						points={ma10Pts}
					/>
				) : null}
				{bars.map((b) => (
					<rect
						key={`hit-${b.i}`}
						x={pad + b.i * slotW}
						y={priceTop}
						width={slotW}
						height={volBottom - priceTop}
						fill="transparent"
						onMouseEnter={() => setHoverIndex(b.i)}
					/>
				))}
				{hoverIndex != null && bars[hoverIndex] ? (
					<line
						x1={bars[hoverIndex]!.xCenter}
						x2={bars[hoverIndex]!.xCenter}
						y1={priceTop}
						y2={volBottom}
						stroke="#64748b"
						strokeWidth={1}
						strokeDasharray="3 2"
						opacity={0.65}
						pointerEvents="none"
					/>
				) : null}
			</svg>
			<div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-0.5 text-[10px] text-gray-600 mb-0.5 font-mono">
				<span className="inline-flex items-center gap-1">
					<span
						className="inline-block w-3 h-0.5 rounded"
						style={{ backgroundColor: MA10_STROKE }}
					/>
					MA10
				</span>
				<span className="inline-flex items-center gap-1">
					<span
						className="inline-block w-3 h-0.5 rounded"
						style={{ backgroundColor: MA5_STROKE }}
					/>
					MA5
				</span>
			</div>
			<div className="flex justify-between text-[11px] text-gray-500 mt-1 font-mono">
				<span>{isHovering ? displayDate : first}</span>
				<span
					className={`font-medium ${isHovering && hoveredBar?.isBearish ? "text-green-700" : "text-black"}`}
				>
					{footerLabel}
				</span>
				<span>{isHovering ? "" : last}</span>
			</div>
		</div>
	);
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

function PoolMiniChart({ series }: { series: PriceSeriesLine | PriceSeriesOhlc }) {
	if (isOhlcSeries(series)) {
		return <MiniCandlestick series={series} />;
	}
	return <MiniSparkline series={series} />;
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
						id={`mar-stock-${row.symbol}`}
						className="border border-gray-200 rounded-lg p-3 bg-gray-50/80 scroll-mt-4"
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
							<PoolMiniChart series={row.price_series} />
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
