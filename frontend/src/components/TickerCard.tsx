import type { DCFResult } from "../hooks/useDCFResults";

const badgeColors: Record<string, string> = {
  "STRONG BUY": "bg-green-600 text-white",
  BUY: "bg-green-500 text-white",
  HOLD: "bg-yellow-500 text-black",
  SELL: "bg-red-500 text-white",
  AVOID: "bg-red-700 text-white",
};

export function TickerCard({ result }: { result: DCFResult }) {
  const color = badgeColors[result.recommendation] ?? "bg-gray-500 text-white";
  const upsideColor = result.upside >= 0 ? "text-green-400" : "text-red-400";

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-bold text-white">{result.ticker}</h2>
        <span className={`px-2 py-1 rounded text-xs font-semibold ${color}`}>
          {result.recommendation}
        </span>
      </div>

      <div className="space-y-2 text-sm text-gray-300">
        <div className="flex justify-between">
          <span>Price</span>
          <span className="text-white font-medium">
            ${result.price.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Intrinsic Value</span>
          <span className="text-white font-medium">
            ${result.intrinsic.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Upside</span>
          <span className={`font-medium ${upsideColor}`}>
            {result.upside >= 0 ? "+" : ""}
            {result.upside.toFixed(1)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span>WACC</span>
          <span className="text-white font-medium">
            {(result.wacc * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
