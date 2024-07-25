from itsdangerous import BadSignature


class OutsideScope(BadSignature):
    """Raised if itsdangerous signed data was unsigned outside of specified scope_str"""
