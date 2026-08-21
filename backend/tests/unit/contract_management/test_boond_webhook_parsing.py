"""Tests for the BoondManager webhook payload parsing."""

from app.contract_management.application.boond_webhook_parsing import (
    iter_events,
    parse_positioning_event,
)


def _webhook_event(entity_type="positioning", entity_id="41", new_state=7):
    """Payload au format réel de Boond : l'état est dans le log inclus."""
    included = []
    if new_state is not None:
        included = [
            {
                "id": "117497",
                "type": "log",
                "attributes": {
                    "content": {
                        "context": {"id": entity_id},
                        "diff": {"state": {"old": 0, "new": new_state}},
                    }
                },
            }
        ]
    return {
        "id": "3_abc123",
        "type": "webhookevent",
        "attributes": {"type": "update"},
        "relationships": {"dependsOn": {"id": entity_id, "type": entity_type}},
        "included": included,
    }


class TestIterEvents:
    """Normalisation du corps du webhook."""

    def test_unwraps_a_list_of_events(self):
        payload = [{"data": _webhook_event()}, {"data": _webhook_event(entity_id="42")}]
        assert [e["relationships"]["dependsOn"]["id"] for e in iter_events(payload)] == ["41", "42"]

    def test_accepts_a_single_object(self):
        assert len(iter_events({"data": _webhook_event()})) == 1

    def test_accepts_data_without_wrapper(self):
        assert iter_events(_webhook_event())[0]["type"] == "webhookevent"


class TestParsePositioningEvent:
    """Extraction du positionnement et de son nouvel état."""

    def test_reads_the_positioning_and_its_new_state(self):
        assert parse_positioning_event(_webhook_event()) == (41, 7)

    def test_ignores_other_entities(self):
        """Un événement candidat ou ressource ne concerne plus Bobby."""
        assert parse_positioning_event(_webhook_event(entity_type="candidate")) == (None, None)

    def test_returns_the_positioning_without_state_when_no_log(self):
        """Sans log de changement d'état, l'état reste inconnu."""
        assert parse_positioning_event(_webhook_event(new_state=None)) == (41, None)

    def test_ignores_a_non_numeric_id(self):
        assert parse_positioning_event(_webhook_event(entity_id="abc")) == (None, None)

    def test_supports_direct_positioning_data(self):
        """Rejeu manuel : le positionnement est transmis tel quel."""
        payload = {"id": "41", "type": "positioning", "attributes": {"state": 7}}
        assert parse_positioning_event(payload) == (41, 7)

    def test_returns_nothing_for_an_empty_payload(self):
        assert parse_positioning_event({}) == (None, None)
