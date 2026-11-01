"""Evaluation harness errors."""


class HarnessError(RuntimeError):
    """A run cannot continue or its result would be misleading."""


class PricesMissingError(HarnessError):
    """prices.json lacks a price needed to compute cost."""


class BudgetExceededError(HarnessError):
    """Cumulative cost passed the per-run abort limit."""


class ModelMismatchError(HarnessError):
    """A call used a model other than the one pinned for the run."""


class VariantCapError(HarnessError):
    """Registering a round would pass the pre-registered cap on tried variants."""
