from types import SimpleNamespace

import pytest

from app.ml import model
from app.ml.features import CreditFeatures
from app.scripts import seed_demo


def test_demo_uses_rules_without_loading_ml(monkeypatch) -> None:
    monkeypatch.setattr(model, "get_settings", lambda: SimpleNamespace(credit_ml_enabled=False))

    def unexpected_load():
        raise AssertionError("Demo must not load the synthetic ML artifact")

    monkeypatch.setattr(model, "_load", unexpected_load)
    features = CreditFeatures(
        completed_sales=0, paid_credits=0, paid_late=0,
        pending_overdue=0, pending_current=0, outstanding=0,
        requested_amount=50, max_credit_amount=200, tenure_days=0,
    )
    result = model.predict_default_probability(features)
    assert result.ml is False
    assert result.model_version == "rules-v1"


@pytest.mark.asyncio
async def test_demo_seed_refuses_production(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setattr(seed_demo, "get_settings", lambda: SimpleNamespace(
        database_url="postgresql+asyncpg://user:password@database/production",
        environment="production",
    ))
    with pytest.raises(SystemExit, match="refused"):
        await seed_demo.seed_demo()
