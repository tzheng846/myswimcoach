"""Unit tests for phase_metrics.py — registry invariants + compute engine (Phase 75-01)."""
import numpy as np
import pytest

from phase_metrics import (
    MetricSpec,
    PhaseContext,
    PHASES,
    TIERS,
    REGISTRY,
    compute_phases,
)


def _make_ctx(**overrides):
    n = 50
    defaults = dict(
        t=np.arange(n) / 10.0,
        vel=np.full(n, 1.0),
        dist=np.arange(n) * 0.1,
        accel=np.zeros(n),
        fs=10.0,
        stroke_type="freestyle",
        go_signal_s=None,
    )
    defaults.update(overrides)
    return PhaseContext(**defaults)


class TestRegistryInvariants:
    """AC-1: REGISTRY is the single declarative source of truth, fully populated as planned."""

    def test_keys_unique(self):
        keys = [spec.key for spec in REGISTRY]
        assert len(keys) == len(set(keys)), "duplicate metric key in REGISTRY"

    def test_every_spec_has_valid_phase_and_tier(self):
        for spec in REGISTRY:
            assert spec.phase in PHASES, f"{spec.key}: bad phase {spec.phase!r}"
            assert spec.tier in ("low", "medium", "high"), f"{spec.key}: bad tier {spec.tier!r}"
            assert spec.tier in TIERS

    def test_all_specs_planned_with_no_compute_fn(self):
        """This plan implements zero metrics — every spec must be planned/compute=None."""
        for spec in REGISTRY:
            assert spec.status == "planned", f"{spec.key} is not planned"
            assert spec.compute is None, f"{spec.key} has a compute fn but should not yet"

    def test_reaction_time_reserved_under_start(self):
        keys_by_phase = {spec.key: spec.phase for spec in REGISTRY}
        assert "reaction_time" in keys_by_phase
        assert keys_by_phase["reaction_time"] == "start"

    def test_registry_nonempty_and_covers_all_phases(self):
        phases_present = {spec.phase for spec in REGISTRY}
        assert phases_present == set(PHASES)
        assert len(REGISTRY) >= 30  # the full taxonomy, not a token subset


class TestMetricSpecValidation:
    def test_unknown_phase_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "not_a_phase", "X", "s", "low")

    def test_unknown_tier_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "not_a_tier")

    def test_planned_with_compute_fn_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "low", status="planned", compute=lambda ctx: 1.0)

    def test_implemented_without_compute_fn_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "low", status="implemented", compute=None)

    def test_implemented_with_compute_fn_accepted(self):
        spec = MetricSpec("x", "start", "X", "s", "low", status="implemented", compute=lambda ctx: 1.0)
        assert spec.compute(_make_ctx()) == 1.0


class TestComputePhases:
    """AC-1/AC-2 engine behavior: the seam runs cleanly with an all-planned registry."""

    def test_returns_four_phase_buckets_plus_metadata(self):
        result = compute_phases(_make_ctx())
        assert result["schema_version"] == 1
        assert "go_signal_s" in result
        for phase in PHASES:
            assert phase in result
            assert isinstance(result[phase], dict)

    def test_every_registry_key_reflected_with_none_value(self):
        result = compute_phases(_make_ctx())
        for spec in REGISTRY:
            entry = result[spec.phase][spec.key]
            assert entry["value"] is None
            assert entry["status"] == "planned"
            assert entry["unit"] == spec.unit
            assert entry["label"] == spec.label
            assert entry["tier"] == spec.tier

    def test_reaction_time_entry_value_none_status_planned(self):
        result = compute_phases(_make_ctx())
        entry = result["start"]["reaction_time"]
        assert entry["value"] is None
        assert entry["status"] == "planned"

    def test_go_signal_passed_through(self):
        result = compute_phases(_make_ctx(go_signal_s=12.5))
        assert result["go_signal_s"] == 12.5

    def test_never_raises_on_empty_accel(self):
        ctx = _make_ctx(accel=np.array([]))
        result = compute_phases(ctx)  # must not raise
        assert result["schema_version"] == 1


class TestComputeSeamWiring:
    """Prove the engine actually calls compute() for implemented specs, and swallows
    exceptions to None — this is the seam Step 2 will rely on."""

    def _registry_with(self, extra_spec):
        return tuple(REGISTRY) + (extra_spec,)

    def test_implemented_spec_compute_is_called(self, monkeypatch):
        called = {}

        def fake_compute(ctx):
            called["yes"] = True
            return 42.0

        extra = MetricSpec("test_only_metric", "start", "Test", "s", "low",
                            status="implemented", compute=fake_compute)
        monkeypatch.setattr("phase_metrics.REGISTRY", self._registry_with(extra))

        result = compute_phases(_make_ctx())
        assert called.get("yes") is True
        assert result["start"]["test_only_metric"]["value"] == 42.0
        assert result["start"]["test_only_metric"]["status"] == "implemented"

    def test_raising_compute_fn_degrades_to_none(self, monkeypatch):
        def boom(ctx):
            raise RuntimeError("simulated failure")

        extra = MetricSpec("test_boom_metric", "start", "Test", "s", "low",
                            status="implemented", compute=boom)
        monkeypatch.setattr("phase_metrics.REGISTRY", self._registry_with(extra))

        result = compute_phases(_make_ctx())  # must not raise
        assert result["start"]["test_boom_metric"]["value"] is None
