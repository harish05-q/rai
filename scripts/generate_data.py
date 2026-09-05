"""Generate synthetic R.AI domain data. Run from the repository root:

    python scripts/generate_data.py
    python scripts/generate_data.py --customers 1000 --payments 10000 --seed 42

Uses DATABASE_URL from the environment or apps/api settings.
Does not run recovery analysis; use scripts/seed_demo.py for generate + analyze.
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
            analyze=args.analyze,
        )
    print("Generation complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
