from apple_mcp_common.safety import safety_block_suggestion
from apple_numbers_mcp.config import load_settings

SAFETY_ENV_VAR = "APPLE_NUMBERS_MCP_SAFETY_MODE"

READ_ACTIONS = frozenset(
    {
        "numbers_health",
        "numbers_list_documents",
        "numbers_list_sheets",
        "numbers_list_tables",
        "numbers_read_range",
    }
)
MANAGE_ACTIONS = frozenset(
    {
        "numbers_open_document",
        "numbers_create_document",
        "numbers_save_document",
        "numbers_close_document",
        "numbers_create_table",
        "numbers_add_rows",
        "numbers_delete_rows",
        "numbers_add_columns",
        "numbers_delete_columns",
        "numbers_set_format",
        "numbers_write_range",
        "numbers_export_document",
    }
)


class SafetyError(Exception):
    def __init__(self, error_code: str, message: str, suggestion: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.suggestion = suggestion


def ensure_action_allowed(action: str) -> None:
    settings = load_settings()

    if action in READ_ACTIONS:
        return

    if action in MANAGE_ACTIONS:
        if settings.safety_mode == "safe_readonly":
            raise SafetyError(
                "WRITE_BLOCKED",
                f"Action '{action}' is blocked because {SAFETY_ENV_VAR} is '{settings.safety_mode}'.",
                safety_block_suggestion(SAFETY_ENV_VAR, "safe_manage", settings.safety_mode),
            )
        return

    raise SafetyError(
        "UNKNOWN_ACTION",
        f"Action '{action}' is not recognized by the safety policy.",
        "Update the permissions layer before exposing new tools.",
    )
