import { useEffect, useState } from "react";
import { collection, getDocs, doc, getDoc } from "firebase/firestore";
import { db } from "../lib/firebase";

export interface DCFResult {
  ticker: string;
  price: number;
  intrinsic: number;
  upside: number;
  recommendation: string;
  wacc: number;
  rev_growth: number;
  parameters_used: Record<string, number | string>;
  updated_at: string;
}

export interface LastRun {
  timestamp: string;
  date: string;
  tickers_processed: string[];
  total_success: number;
  total_errors: number;
}

export function useDCFResults() {
  const [results, setResults] = useState<DCFResult[]>([]);
  const [lastRun, setLastRun] = useState<LastRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [snapshot, metaSnap] = await Promise.all([
          getDocs(collection(db, "dcf_results")),
          getDoc(doc(db, "meta", "last_run")),
        ]);

        const data = snapshot.docs.map((d) => d.data() as DCFResult);
        data.sort((a, b) => b.upside - a.upside);
        setResults(data);

        if (metaSnap.exists()) {
          setLastRun(metaSnap.data() as LastRun);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  return { results, lastRun, loading, error };
}
