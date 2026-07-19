"""Role gating for bot commands: key commands accept exec OR committee,
everything else (board-game mutations, complaints admin) stays exec-only."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import discord

from rbga.bot import common


def interaction_with_roles(*names):
    member = MagicMock(spec=discord.Member)
    member.roles = [SimpleNamespace(name=n) for n in names]
    interaction = MagicMock()
    interaction.user = member
    return interaction


def configure(monkeypatch, exec_role, committee_role):
    monkeypatch.setattr(common, "EXEC_ROLE", exec_role)
    monkeypatch.setattr(common, "COMMITTEE_ROLE", committee_role)
    monkeypatch.setattr(
        common, "KEYS_ROLES", [r for r in (exec_role, committee_role) if r]
    )


def test_keys_allows_exec_and_committee(monkeypatch):
    configure(monkeypatch, "Executive", "Committee")
    assert common.require_keys_role(interaction_with_roles("Executive"))
    assert common.require_keys_role(interaction_with_roles("Committee"))
    assert not common.require_keys_role(interaction_with_roles("Members"))
    # Role names are exact and case-sensitive.
    assert not common.require_keys_role(interaction_with_roles("executive"))


def test_exec_check_excludes_committee(monkeypatch):
    configure(monkeypatch, "Executive", "Committee")
    assert common.require_exec_role(interaction_with_roles("Executive"))
    assert not common.require_exec_role(interaction_with_roles("Committee"))


def test_keys_check_without_committee_configured(monkeypatch):
    configure(monkeypatch, "Executive", None)
    assert common.require_keys_role(interaction_with_roles("Executive"))
    assert not common.require_keys_role(interaction_with_roles("Committee"))


def test_fails_closed_when_unconfigured(monkeypatch):
    configure(monkeypatch, None, None)
    assert not common.require_keys_role(interaction_with_roles("Executive"))
    assert not common.require_exec_role(interaction_with_roles("Executive"))


def test_fails_outside_guild(monkeypatch):
    configure(monkeypatch, "Executive", "Committee")
    interaction = MagicMock()
    interaction.user = MagicMock(spec=discord.User)  # a DM: not a Member
    assert not common.require_keys_role(interaction)
    assert not common.require_exec_role(interaction)
