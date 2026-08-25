DOMAIN = "tellink"


def reauth_issue_id(entry_id: str) -> str:
    """Return the Repairs issue id for one config entry."""
    return f"reauth_required_{entry_id}"
