import datetime
from app.services.youtube import parse_iso_datetime

def test_parse_iso_datetime_various_formats():
    # 5-digit microseconds (The exact issue from GitHub Actions: .96018Z and .01222Z)
    dt1 = parse_iso_datetime("2026-05-27T05:55:44.96018Z")
    assert dt1 == datetime.datetime(2026, 5, 27, 5, 55, 44, 960180)

    dt2 = parse_iso_datetime("2025-07-22T11:54:46.01222Z")
    assert dt2 == datetime.datetime(2025, 7, 22, 11, 54, 46, 12220)

    # Standard 6-digit microseconds
    dt3 = parse_iso_datetime("2026-05-27T05:55:44.123456Z")
    assert dt3 == datetime.datetime(2026, 5, 27, 5, 55, 44, 123456)

    # 3-digit milliseconds
    dt4 = parse_iso_datetime("2026-05-27T05:55:44.123Z")
    assert dt4 == datetime.datetime(2026, 5, 27, 5, 55, 44, 123000)

    # No subseconds with Z
    dt5 = parse_iso_datetime("2026-05-27T05:55:44Z")
    assert dt5 == datetime.datetime(2026, 5, 27, 5, 55, 44)

    # Timezone offset (+09:00)
    dt6 = parse_iso_datetime("2026-05-27T05:55:44.96018+09:00")
    assert dt6 == datetime.datetime(2026, 5, 27, 5, 55, 44, 960180)

    # Invalid / None cases
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime("invalid-date-string") is None
