"""Tests for MagicLink.mark_used() single-use invalidation.

Verrouille le comportement du correctif ``mark_used`` : après une action
terminale à usage unique, le lien est définitivement invalidé en réutilisant
le drapeau ``is_revoked``. Ne duplique pas les tests généraux de
``test_magic_link_entity.py`` (nouveau lien valide, revoke, expiration...).
"""

from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose


def _make_link() -> MagicLink:
    """Create a fresh, valid magic link."""
    return MagicLink(
        third_party_id="00000000-0000-0000-0000-000000000001",
        purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
        email_sent_to="test@example.com",
    )


class TestMagicLinkMarkUsed:
    """Tests for the mark_used() terminal invalidation."""

    def test_mark_used_invalidates_link(self):
        """Given a fresh (valid) link, when marked used, it becomes invalid."""
        link = _make_link()
        # Precondition: a brand-new link is valid and not revoked.
        assert link.is_valid()
        assert not link.is_revoked

        link.mark_used()

        assert not link.is_valid()
        assert link.is_revoked

    def test_mark_used_consistent_with_revoke(self):
        """mark_used() invalidates a link exactly like revoke()."""
        used = _make_link()
        revoked = _make_link()

        used.mark_used()
        revoked.revoke()

        assert used.is_revoked is True
        assert revoked.is_revoked is True
        assert used.is_valid() is False
        assert used.is_valid() == revoked.is_valid()

    def test_mark_used_is_idempotent(self):
        """Calling mark_used() twice keeps the link invalid."""
        link = _make_link()

        link.mark_used()
        link.mark_used()

        assert not link.is_valid()
        assert link.is_revoked
