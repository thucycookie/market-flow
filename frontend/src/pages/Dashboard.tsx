import { useDCFResults } from "../hooks/useDCFResults";
import { TickerCard } from "../components/TickerCard";

export function Dashboard() {
  const { results, lastRun, loading, error } = useDCFResults();

  if (loading) {
    return <p className="text-gray-400">Loading...</p>;
  }

  if (error) {
    return <p className="text-red-400">Error: {error}</p>;
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">DCF Dashboard</h1>
        {lastRun && (
          <p className="text-sm text-gray-400 mt-1">
            Last updated: {lastRun.date} &middot; {lastRun.total_success}/
            {lastRun.tickers_processed.length} tickers processed
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {results.map((r) => (
          <TickerCard key={r.ticker} result={r} />
        ))}
      </div>
    </div>
  );
}
