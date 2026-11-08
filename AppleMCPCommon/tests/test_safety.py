import pytest

from apple_mcp_common.bundle import drop_unexpanded_user_config
from apple_mcp_common.safety import SAFETY_SETTING_TITLES, safety_block_suggestion, safety_mode_warning

ENV = "APPLE_MAIL_MCP_SAFETY_PROFILE"


def test_block_suggestion_names_env_var_value_desktop_setting_and_restart() -> None:
    text = safety_block_suggestion(ENV, "full_access")
    assert f"{ENV}=full_access" in text
    assert '"env" block' in text
    assert 'Claude Desktop' in text and '"Mail safety mode" to full_access' in text
    assert "restart the MCP client" in text
    assert "Ask the user" in text


def test_block_suggestion_for_manage_mentions_both_sufficient_modes() -> None:
    text = safety_block_suggestion("APPLE_NOTES_MCP_SAFETY_MODE", "safe_manage")
    assert "safe_manage or full_access" in text
    assert "APPLE_NOTES_MCP_SAFETY_MODE=safe_manage" in text


def test_block_suggestion_explains_a_typo_first(monkeypatch) -> None:
    monkeypatch.setenv(ENV, "full-access")
    text = safety_block_suggestion(ENV, "full_access", "safe_readonly")
    assert text.startswith(f"{ENV} is set to 'full-access'")
    assert "fell back to safe_readonly" in text


@pytest.mark.parametrize(
    ("raw", "effective", "expected"),
    [
        (None, "safe_manage", None),
        ("safe_manage", "safe_manage", None),
        ("  full_access ", "full_access", None),
        ("SAFE_MANAGE", "safe_manage", None),  # accepted case-insensitively by Files/System
        ("full_access", "safe_manage", None),  # valid value; injected settings may differ
        ("SAFE_MANAGE", "safe_readonly", "'SAFE_MANAGE'"),  # case-sensitive servers coerce it
        ("safe_mange", "safe_readonly", "'safe_mange'"),
        ("", "safe_readonly", "set but blank"),
        ("   ", "safe_readonly", "set but blank"),
        ("${user_config.mail_safety_mode}", "safe_readonly", "not a valid safety mode"),
    ],
)
def test_safety_mode_warning(raw, effective, expected) -> None:
    environ = {} if raw is None else {ENV: raw}
    warning = safety_mode_warning(ENV, effective, environ)
    if expected is None:
        assert warning is None
    else:
        assert expected in warning
        assert f"fell back to {effective}" in warning
        assert "safe_readonly, safe_manage, full_access" in warning


def test_every_safety_env_var_has_a_desktop_title() -> None:
    assert len(SAFETY_SETTING_TITLES) == 9
    assert all(title.endswith("safety mode") for title in SAFETY_SETTING_TITLES.values())


def test_drop_unexpanded_user_config_removes_only_literal_placeholders() -> None:
    environ = {
        "APPLE_MAIL_MCP_ALLOWED_ATTACHMENT_ROOT": "${user_config.mail_allowed_attachment_root}",
        "APPLE_FILES_MCP_ALLOWED_ROOTS": "~/Desktop",
        "APPLE_CALENDAR_MCP_ALLOWED_CALENDARS": "",
        "OTHER": "${user_config.other}",
    }
    removed = drop_unexpanded_user_config(environ)
    assert removed == ["APPLE_MAIL_MCP_ALLOWED_ATTACHMENT_ROOT"]
    assert environ == {
        "APPLE_FILES_MCP_ALLOWED_ROOTS": "~/Desktop",
        "APPLE_CALENDAR_MCP_ALLOWED_CALENDARS": "",
        "OTHER": "${user_config.other}",
    }


def test_how_to_set_uses_an_explicit_desktop_title() -> None:
    from apple_mcp_common.safety import how_to_set

    text = how_to_set("APPLE_SYSTEM_MCP_GUI_ALLOWED_APPS", "com.apple.TextEdit", "Apps that accept GUI input")
    assert "APPLE_SYSTEM_MCP_GUI_ALLOWED_APPS=com.apple.TextEdit" in text
    assert '"Apps that accept GUI input" to com.apple.TextEdit' in text
    assert "restart the MCP client" in text


def test_safety_env_prefers_domain_variable_then_global_then_default() -> None:
    from apple_mcp_common.safety import safety_env

    domain = "APPLE_NOTES_MCP_SAFETY_MODE"
    assert safety_env(domain, "safe_manage", {}) == "safe_manage"
    assert safety_env(domain, "safe_manage", {"APPLE_MCP_SAFETY_MODE": "full_access"}) == "full_access"
    assert safety_env(domain, "safe_manage", {"APPLE_MCP_SAFETY_MODE": "full_access", domain: "safe_readonly"}) == "safe_readonly"
    assert safety_env(domain, "safe_manage", {domain: ""}) == ""


def test_invalid_global_value_is_reported_under_its_own_name() -> None:
    warning = safety_mode_warning("APPLE_NOTES_MCP_SAFETY_MODE", "safe_readonly", {"APPLE_MCP_SAFETY_MODE": "everything"})

    assert warning is not None
    assert "APPLE_MCP_SAFETY_MODE" in warning
    assert safety_mode_warning("APPLE_NOTES_MCP_SAFETY_MODE", "safe_readonly", {}) is None


def test_global_safety_mode_sets_every_domain_and_domain_variable_wins(monkeypatch) -> None:
    import importlib

    modules = [
        ("apple_calendar_mcp.config", "safe_manage"),
        ("apple_contacts_mcp.config", "safe_manage"),
        ("apple_files_mcp.config", "safe_manage"),
        ("apple_notes_mcp.config", "full_access"),
        ("apple_numbers_mcp.config", "full_access"),
        ("apple_reminders_mcp.config", "safe_manage"),
        ("apple_system_mcp.config", "safe_manage"),
        ("apple_messages_mcp.config", "full_access"),
        ("apple_shortcuts_mcp.config", "full_access"),
    ]
    for var in [name for name in __import__("os").environ if name.endswith(("_SAFETY_MODE", "_SAFETY_PROFILE"))]:
        monkeypatch.delenv(var)
    for module_name, default in modules:
        config = importlib.import_module(module_name)
        config.load_settings.cache_clear()
        assert config.load_settings().safety_mode == default, module_name
    monkeypatch.setenv("APPLE_MCP_SAFETY_MODE", "safe_readonly")
    monkeypatch.setenv("APPLE_NOTES_MCP_SAFETY_MODE", "full_access")
    for module_name, _ in modules:
        config = importlib.import_module(module_name)
        config.load_settings.cache_clear()
        expected = "full_access" if module_name == "apple_notes_mcp.config" else "safe_readonly"
        assert config.load_settings().safety_mode == expected, module_name
        config.load_settings.cache_clear()
