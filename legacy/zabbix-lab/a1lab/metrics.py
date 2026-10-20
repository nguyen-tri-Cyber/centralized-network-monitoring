"""Metrics calculated only from observed timestamps/case counts."""


def calculate_timings(fault_at, event_at, mail_at):
    return {
        "T_det_seconds": None if event_at is None or fault_at is None else round(event_at - fault_at, 2),
        "T_notify_seconds": None if mail_at is None or event_at is None else round(mail_at - event_at, 2),
    }


def detection_rate(detected: int, valid: int):
    return None if valid == 0 else round(100 * detected / valid, 2)
