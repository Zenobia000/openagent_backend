"""
KV-Cache baseline measurement script.

Analyzes API usage logs to compute:
- KV-Cache hit rate (cached_tokens / total_tokens)
- Estimated cost savings from caching
- Per-provider breakdown

Usage:
    python scripts/measure_kv_cache.py [--log-dir data/cost] [--output data/baseline/kv_cache_baseline.json]
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def analyze_api_logs(log_dir: str = "data/cost") -> dict:
    """Analyze API usage logs for cache hit rate."""
    total_tokens = 0
    cached_tokens = 0
    total_cost = 0.0
    request_count = 0
    per_provider: dict[str, dict] = {}

    log_path = Path(log_dir)
    if not log_path.exists():
        return {"error": f"Log directory not found: {log_dir}"}

    for log_file in sorted(log_path.glob("usage_*.jsonl")):
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                request_count += 1
                entry_total = entry.get("total_tokens", 0)
                entry_cached = entry.get("cached_tokens", 0)
                entry_cost = entry.get("cost_usd", 0.0)
                provider = entry.get("provider", "unknown")

                total_tokens += entry_total
                cached_tokens += entry_cached
                total_cost += entry_cost

                if provider not in per_provider:
                    per_provider[provider] = {
                        "total_tokens": 0,
                        "cached_tokens": 0,
                        "request_count": 0,
                    }
                per_provider[provider]["total_tokens"] += entry_total
                per_provider[provider]["cached_tokens"] += entry_cached
                per_provider[provider]["request_count"] += 1

    hit_rate = cached_tokens / total_tokens if total_tokens > 0 else 0
    # Claude pricing: cached $0.30/MTok vs uncached $3/MTok
    potential_savings = cached_tokens * (3.0 - 0.3) / 1_000_000

    # Per-provider hit rates
    for stats in per_provider.values():
        t = stats["total_tokens"]
        stats["hit_rate"] = round(stats["cached_tokens"] / t, 4) if t > 0 else 0

    return {
        "measured_at": datetime.utcnow().isoformat(),
        "log_dir": str(log_dir),
        "request_count": request_count,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "kv_cache_hit_rate": round(hit_rate, 4),
        "total_cost_usd": round(total_cost, 4),
        "potential_savings_usd": round(potential_savings, 4),
        "per_provider": per_provider,
    }


def main():
    parser = argparse.ArgumentParser(description="Measure KV-Cache baseline")
    parser.add_argument("--log-dir", default="data/cost", help="API usage log directory")
    parser.add_argument("--output", default="data/baseline/kv_cache_baseline.json", help="Output file")
    args = parser.parse_args()

    result = analyze_api_logs(args.log_dir)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"KV-Cache Baseline Report")
    print(f"========================")
    print(f"Requests analyzed: {result.get('request_count', 0)}")
    print(f"Total tokens:      {result.get('total_tokens', 0):,}")
    print(f"Cached tokens:     {result.get('cached_tokens', 0):,}")
    print(f"Hit rate:          {result.get('kv_cache_hit_rate', 0):.2%}")
    print(f"Potential savings: ${result.get('potential_savings_usd', 0):.2f}")
    print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()
