"""Tests for MagicLink domain entity."""

from datetime import datetime, timedelta

import pytest

from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose


class TestMagicLink:
    """Tests for MagicLink entity."""

    def test_new_magic_link_is_valid(self):
        """Given a new magic link, it should be valid."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
        )
        assert link.is_valid()
        assert not link.is_expired
        assert not link.is_revoked

    def test_token_is_generated_automatically(self):
        """Given a new magic link, a token should be generated."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
        )
        assert link.token is not None
        assert len(link.token) >= 64

    def test_revoke_makes_link_invalid(self):
        """Given a valid link, when revoked, then it is invalid."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
        )
        link.revoke()
        assert not link.is_valid()
        assert link.is_revoked

    def test_expired_link_is_invalid(self):
        """Given an expired link, it should be invalid."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert not link.is_valid()
        assert link.is_expired

    def test_mark_accessed_sets_timestamp(self):
        """Given a new link, when accessed, then timestamp is set."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
        )
        assert link.accessed_at is None
        link.mark_accessed()
        assert link.accessed_at is not None

    def test_mark_accessed_is_idempotent(self):
        """Given an already accessed link, mark_accessed does not change timestamp."""
        link = MagicLink(
            third_party_id="00000000-0000-0000-0000-000000000001",
            purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
            email_sent_to="test@example.com",
        )
        link.mark_accessed()
        first_access = link.accessed_at
        link.mark_accessed()
        assert link.accessed_at == first_access

    def test_generate_token_produces_unique_tokens(self):
        """Generated tokens should be unique."""
        token1 = MagicLink.generate_token()
        token2 = MagicLink.generate_token()
        assert token1 != token2
