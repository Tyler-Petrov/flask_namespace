from itsdangerous import BadSignature


class OutsideLocality(BadSignature):
    """Raised if itsdangerous signed data was unsigned outside of specified locality"""
