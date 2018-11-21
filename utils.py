from datetime import datetime

from pytz import timezone, utc

TIMEZONE = "Europe/Berlin"


def get_local_time(t):
    return utc.localize(datetime.strptime(t, "%Y-%m-%dT%H:%M:%S")).astimezone(timezone(TIMEZONE)).strftime(
        "%Y-%m-%d %H:%M:%S")


def utc_to_str(t):
    return utc.localize(t).astimezone(timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
