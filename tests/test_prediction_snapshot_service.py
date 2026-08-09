import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.services.prediction_snapshot_service import (
    MarketData,
    PredictionData,
    PredictionIdentity,
    PredictionRunLifecycleError,
    PredictionSnapshot,
    PredictionSnapshotLifecycle,
    PredictionSnapshotValidationError,
    SnapshotModelIdentity,
    SupportingEvidence,
    canonical_artifact_fingerprint,
)


RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
LOGICAL_BUILD_ID = "20260727T120000Z"
ARTIFACT_FINGERPRINT = "registry-sha256-fixture"


def build_context_and_snapshot(
    *,
    market: str = "moneyline",
    selection: str = "Washington Nationals",
    model_run_id: UUID = RUN_ID,
    logical_build_id: str = LOGICAL_BUILD_ID,
):
    lifecycle = PredictionSnapshotLifecycle()
    context = lifecycle.begin_run(
        model=SnapshotModelIdentity("mlb_sharpstack", "1.0.0", "abc123"),
        logical_build_id=logical_build_id,
        artifact_fingerprint=ARTIFACT_FINGERPRINT,
        started_at=NOW,
        build_timestamp=NOW,
        artifact_pointer="output/cards/recommendation_registry.json",
        model_run_id=model_run_id,
    )
    snapshot = PredictionSnapshot(
        identity=PredictionIdentity(
            provider_game_id="824414",
            sport="baseball",
            league="mlb",
            market=market,
            selection=selection,
            scheduled_start_at_prediction=NOW + timedelta(hours=2),
        ),
        run=context,
        prediction=PredictionData(
            model_probability=0.599,
            confidence_score=79.5,
            confidence_label="HIGH",
            recommendation="STRONG PLAY",
            model_recommendation="STRONG PLAY",
            conviction_tier="STRONG PLAY",
            hammer_score=66.8,
            market_value_label="POSITIVE VALUE",
            market_value_tone="positive_value",
        ),
        market=MarketData(),
        supporting_evidence=SupportingEvidence(),
    )
    return lifecycle, context, snapshot


def test_registry_row_converts_to_immutable_snapshot_without_full_ledger():
    lifecycle = PredictionSnapshotLifecycle()
    context = lifecycle.begin_run(
        model=SnapshotModelIdentity("mlb_sharpstack", "1.0.0", "abc123"),
        logical_build_id=LOGICAL_BUILD_ID,
        artifact_fingerprint=ARTIFACT_FINGERPRINT,
        started_at=NOW,
        build_timestamp=NOW,
        model_run_id=RUN_ID,
    )
    row = {
        "event_id": "824414",
        "sport": "BASEBALL",
        "league": "MLB",
        "market": "moneyline",
        "selection": " Washington   Nationals ",
        "matchup": "Arizona Diamondbacks @ Washington Nationals",
        "event_time": "2026-07-27T14:00:00Z",
        "scheduled_start_at": "2026-07-27T14:00:00Z",
        "model_probability": 0.599,
        "confidence": "HIGH",
        "recommendation": "STRONG PLAY",
        "model_recommendation": "STRONG PLAY",
        "hammer_score": 66.8,
        "market_value_label": "POSITIVE VALUE",
        "market_value_tone": "positive_value",
        "real_market_loaded": False,
        "market_quote": {},
        "components": {
            "model_confidence": 79.5,
            "bullpen": {
                "source_quality": "PARTIAL",
                "evidence_ledger": [
                    {
                        "source_quality": "COMPLETE",
                        "limited_history": False,
                        "workload_assessment": {"overall_workload": "LIGHT"},
                        "availability_evidence": {"status": "NO_OBSERVED_CONCERN"},
                        "role_evidence": {"candidate_roles": [{"role": "CLOSER"}]},
                    }
                ],
            },
        },
        "reasons": ["Model supports Washington."],
    }
    snapshot = PredictionSnapshot.from_registry_row(row, run=context)
    payload = snapshot.to_dict()

    assert snapshot.identity.selection == "WASHINGTON NATIONALS"
    assert snapshot.identity.selection_side == "HOME"
    assert snapshot.identity.scheduled_start_at_prediction == datetime(
        2026, 7, 27, 14, tzinfo=UTC
    )
    assert payload["identity"]["selection_side"] == "HOME"
    assert snapshot.market.offered_odds is None
    assert snapshot.market.reference_price is None
    assert payload["components"]["bullpen"].get("evidence_ledger") is None
    assert payload["supporting_evidence"]["bullpen"]["evidence_summary"] == {
        "evaluated_pitcher_count": 1,
        "limited_history_count": 0,
        "source_quality_counts": {"COMPLETE": 1},
        "overall_workload_counts": {"LIGHT": 1},
        "availability_status_counts": {"NO_OBSERVED_CONCERN": 1},
        "role_candidate_counts": {"CLOSER": 1},
    }


def test_missing_optional_market_and_schedule_fields_remain_null():
    lifecycle = PredictionSnapshotLifecycle()
    context = lifecycle.begin_run(
        model=SnapshotModelIdentity("mlb_sharpstack", "1.0.0", "abc123"),
        logical_build_id=LOGICAL_BUILD_ID,
        artifact_fingerprint=ARTIFACT_FINGERPRINT,
        started_at=NOW,
        build_timestamp=NOW,
        model_run_id=RUN_ID,
    )
    snapshot = PredictionSnapshot.from_registry_row(
        {
            "event_id": "824414",
            "sport": "BASEBALL",
            "league": "MLB",
            "market": "moneyline",
            "selection": "Washington Nationals",
        },
        run=context,
    )

    assert snapshot.identity.scheduled_start_at_prediction is None
    assert snapshot.market.offered_odds is None
    assert snapshot.market.reference_price is None


def test_display_event_time_is_never_used_as_a_prediction_schedule_timestamp():
    lifecycle = PredictionSnapshotLifecycle()
    context = lifecycle.begin_run(
        model=SnapshotModelIdentity("mlb_sharpstack", "1.0.0", "abc123"),
        logical_build_id=LOGICAL_BUILD_ID,
        artifact_fingerprint=ARTIFACT_FINGERPRINT,
        started_at=NOW,
        build_timestamp=NOW,
        model_run_id=RUN_ID,
    )
    snapshot = PredictionSnapshot.from_registry_row(
        {
            "event_id": "824414",
            "sport": "BASEBALL",
            "league": "KBO",
            "market": "moneyline",
            "selection": "KIA Tigers",
            "event_time": "6:30pm",
        },
        run=context,
    )

    assert snapshot.identity.scheduled_start_at_prediction is None


def test_snapshot_rejects_mutable_resolution_data():
    _, _, snapshot = build_context_and_snapshot()
    try:
        PredictionSnapshot(
            identity=snapshot.identity,
            run=snapshot.run,
            prediction=snapshot.prediction,
            market=snapshot.market,
            supporting_evidence=snapshot.supporting_evidence,
            components={"nested": {"final_score": 5}},
        )
    except PredictionSnapshotValidationError:
        return
    raise AssertionError("Mutable resolution data was accepted.")


def test_snapshot_components_are_deeply_immutable():
    _, _, snapshot = build_context_and_snapshot()
    frozen = PredictionSnapshot(
        identity=snapshot.identity,
        run=snapshot.run,
        prediction=snapshot.prediction,
        market=snapshot.market,
        supporting_evidence=snapshot.supporting_evidence,
        components={
            "score": {"starter": 81.0},
            "reasons": ["starter advantage"],
        },
    )

    try:
        frozen.components["score"]["starter"] = 0.0
    except TypeError:
        pass
    else:
        raise AssertionError("Snapshot mappings remained mutable.")

    try:
        frozen.components["reasons"].append("market edge")
    except AttributeError:
        return
    raise AssertionError("Snapshot sequences remained mutable.")


def test_snapshot_serializes_as_plain_json_and_freezes_schedule_at_prediction():
    _, _, snapshot = build_context_and_snapshot()
    serialized = snapshot.to_dict()
    assert json.loads(json.dumps(serialized))["identity"][
        "scheduled_start_at_prediction"
    ] == "2026-07-27T14:00:00Z"
    assert snapshot.identity.scheduled_start_at_prediction == NOW + timedelta(hours=2)


def test_idempotency_key_is_stable_and_distinguishes_market_and_selection():
    _, _, first = build_context_and_snapshot()
    _, _, identical = build_context_and_snapshot()
    _, _, different_market = build_context_and_snapshot(market="total")
    _, _, different_selection = build_context_and_snapshot(selection="Arizona Diamondbacks")

    assert first.idempotency_key == identical.idempotency_key
    assert first.idempotency_key != different_market.idempotency_key
    assert first.idempotency_key != different_selection.idempotency_key


def test_retry_uses_logical_identity_not_database_model_run_uuid():
    _, first_context, first = build_context_and_snapshot(
        model_run_id=UUID("11111111-1111-1111-1111-111111111111")
    )
    _, retry_context, retry = build_context_and_snapshot(
        model_run_id=UUID("22222222-2222-2222-2222-222222222222")
    )
    _, _, later_build = build_context_and_snapshot(
        model_run_id=UUID("33333333-3333-3333-3333-333333333333"),
        logical_build_id="20260727T150000Z",
    )

    assert first_context.model_run_id != retry_context.model_run_id
    assert first_context.logical_run_key == retry_context.logical_run_key
    assert first.idempotency_key == retry.idempotency_key
    assert first.idempotency_key != later_build.idempotency_key


def test_artifact_fingerprint_ignores_registry_rebuild_generated_ids_and_timestamps():
    first = {
        "generated_at": "2026-07-27T12:00:00Z",
        "recommendations": [{"recommendation_id": "random-one", "selection": "WSH"}],
    }
    retry = {
        "generated_at": "2026-07-27T12:01:00Z",
        "recommendations": [{"recommendation_id": "random-two", "selection": "WSH"}],
    }
    assert canonical_artifact_fingerprint(first) == canonical_artifact_fingerprint(retry)


def test_one_run_accepts_many_games_and_failed_runs_cannot_complete():
    lifecycle, context, first = build_context_and_snapshot()
    second = PredictionSnapshot(
        identity=PredictionIdentity(
            provider_game_id="824415",
            sport="BASEBALL",
            league="MLB",
            market="moneyline",
            selection="Los Angeles Dodgers",
            scheduled_start_at_prediction=NOW + timedelta(hours=3),
        ),
        run=context,
        prediction=PredictionData(recommendation="PLAYABLE"),
        market=MarketData(),
        supporting_evidence=first.supporting_evidence,
    )

    saved = lifecycle.persist_snapshots(context, [first, second])
    assert len(saved.snapshots) == 2

    failed = lifecycle.fail_run(context, reason="Registry conversion failed.")
    assert failed.status == "failed"
    assert failed.completed_at is None

    try:
        lifecycle.complete_run(context)
    except PredictionRunLifecycleError:
        return
    raise AssertionError("Failed run was marked completed.")
