"""Tests for the pure reference-generation helpers.

Verrouille deux correctifs du repository ``postgres_contract_repo`` :

- ``_next_reference_number`` doit trier les suffixes **numériquement** et non
  lexicographiquement (bug historique du « blocage à 1000 » où ``MAX(reference)``
  sur une chaîne considérait "999" > "1000").
- ``_reference_lock_key`` doit produire une clé d'advisory lock **déterministe**
  et **stable entre processus** (CRC32, contrairement à ``hash()`` randomisé),
  tenant dans un ``bigint`` PostgreSQL.
"""

import zlib

from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    _next_reference_number,
    _reference_lock_key,
)


class TestNextReferenceNumber:
    """Tests for the numeric sequence extraction helper."""

    def test_empty_list_returns_one(self):
        """Given no references, the first sequence number is 1."""
        assert _next_reference_number([]) == 1

    def test_single_reference_increments(self):
        """Given PROV-2026-001, the next number is 2."""
        assert _next_reference_number(["PROV-2026-001"]) == 2

    def test_full_range_up_to_999_returns_1000(self):
        """Given suffixes 001..999, the next number is 1000."""
        references = [f"PROV-2026-{i:03d}" for i in range(1, 1000)]
        assert _next_reference_number(references) == 1000

    def test_numeric_sort_beats_lexicographic_max(self):
        """CRITICAL: given 999 and 1000, next is 1001 (numeric), not 1000.

        A lexicographic MAX on the string ranks "999" above "1000" (because
        '9' > '1'), which would wrongly return 1000 and re-collide with the
        existing 1000. Numeric sorting must yield 1001.
        """
        assert _next_reference_number(["PROV-2026-999", "PROV-2026-1000"]) == 1001

    def test_numeric_sort_two_vs_ten(self):
        """Given suffixes 2 and 10, numeric max is 10 -> next is 11."""
        assert _next_reference_number(["PROV-2026-2", "PROV-2026-10"]) == 11

    def test_malformed_entries_are_ignored(self):
        """Non-numeric suffixes are skipped; valid ones still counted."""
        references = ["PROV-2026-007", "not-a-number", "PROV-2026-xyz"]
        assert _next_reference_number(references) == 8

    def test_all_malformed_returns_one(self):
        """Given only unparseable entries, falls back to 1."""
        assert _next_reference_number(["garbage", "no-number-here", ""]) == 1


class TestReferenceLockKey:
    """Tests for the advisory-lock key derivation helper."""

    def test_same_prefix_same_key(self):
        """The key is deterministic for a given prefix."""
        assert _reference_lock_key("PROV-2026-") == _reference_lock_key("PROV-2026-")

    def test_stable_across_calls(self):
        """Two successive calls return the same value (no randomized hashing)."""
        first = _reference_lock_key("GEM-CC-")
        second = _reference_lock_key("GEM-CC-")
        assert first == second

    def test_matches_crc32_of_prefix(self):
        """The key equals CRC32(prefix) : deterministic and process-stable.

        Anchors the fix to the real implementation: CRC32 does not depend on
        ``PYTHONHASHSEED`` (unlike ``hash()``), so concurrent workers compute
        the same lock key for the same prefix.
        """
        for prefix in ("PROV-2026-", "GEM-CC-", "GEN-PO-"):
            assert _reference_lock_key(prefix) == zlib.crc32(prefix.encode("utf-8"))

    def test_distinct_prefixes_yield_distinct_keys(self):
        """Different prefix families map to different lock keys."""
        prefixes = ["PROV-2026-", "GEM-CC-", "GEN-PO-", "BDC-GEM-CC-0001-"]
        keys = {_reference_lock_key(p) for p in prefixes}
        assert len(keys) == len(prefixes)

    def test_key_fits_in_bigint(self):
        """The key is non-negative and fits in a PostgreSQL bigint (< 2**63)."""
        for prefix in ("PROV-2026-", "GEM-CC-", "GEN-PO-", "BDC-GEM-CC-0001-"):
            key = _reference_lock_key(prefix)
            assert 0 <= key < 2**63
