"""Generate synthetic data and run deterministic recovery analysis.

    python scripts/seed_demo.py

This does not execute payment operations. It only scores failed payments and
upserts recovery cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.data.generate import generate_synthetic_dataset, parse_args  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> None:
    args = parse_args()
    with SessionLocal() as session:
        stats = generate_synthetic_dataset(
            session,
            seed=args.seed,
            customer_count=args.customers,
            payment_count=args.payments,
            reset=args.reset,
            analyze=True,
        )
    print("Demo seed complete (analysis included, no payment execution):")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
