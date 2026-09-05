from app.agents.schemas import BaselineComparison
from app.models.enums import ComparisonStatus, SuggestedAction


def compare_to_baseline(
    recommended_action: SuggestedAction,
    baseline_action: str,
    rationale: str,
) -> BaselineComparison:
    baseline = SuggestedAction(baseline_action)
    if recommended_action == baseline:
        return BaselineComparison(
            status=ComparisonStatus.ALIGNED,
            reason="R.AI recommended the same action as the deterministic baseline.",
        )
    clipped = rationale.strip()
    if len(clipped) > 700:
        clipped = clipped[:699] + "…"
    reason = (
        f"R.AI recommended {recommended_action.value} while the baseline recommended "
        f"{baseline.value}. {clipped}"
    )
    return BaselineComparison(status=ComparisonStatus.DIFFERS, reason=reason[:1024])
