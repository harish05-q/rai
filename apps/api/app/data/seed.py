"""Seed the demo merchant with synthetic payments and recovery cases."""

from app.data.generate import generate_synthetic_dataset, parse_args
from app.db.session import SessionLocal


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
    print("Seed complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
