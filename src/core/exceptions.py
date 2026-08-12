class UserNotFoundError(LookupError):
    """No active user for this id — distinct from 'user exists but has no
    department yet', which is a legitimate post-SSO-login state."""
