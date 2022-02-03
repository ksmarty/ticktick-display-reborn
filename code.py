import re
import ssl
import time

import adafruit_requests as requests
import alarm
import socketpool
from adafruit_datetime import datetime, date
from wifi import radio

try:
    from secrets import secrets
except ImportError:
    print("Secrets file is missing for malformed!")
    raise


# noinspection PyTypeChecker
def connect_wifi():
    radio.connect(secrets["ssid"], secrets["password"])
    return requests.Session(socketpool.SocketPool(radio), ssl.create_default_context())


def month_str(x, long=False):
    return {
               1 : "January",
               2 : "February",
               3 : "March",
               4 : "April",
               5 : "May",
               6 : "June",
               7 : "July",
               8 : "August",
               9 : "September",
               10: "October",
               11: "November",
               12: "December",
           }[x][:None if long else 3]


def week_str(x, long=False):
    return {
               0: "Monday",
               1: "Tuesday",
               2: "Wednesday",
               3: "Thursday",
               4: "Friday",
               5: "Saturday",
               6: "Sunday",
           }[x][:None if long else 3]


def date_str(dstr):
    _, year, month, day, _, hour, minute, second = (map(lambda z: int(z) if (z or "").isdigit() else -1, dstr))
    d = datetime(year, month, day, hour, minute, second) \
        if hour != -1 else \
        date(year, month, day)

    data = f"{month_str(month, True)} {d.day}, {d.year}"
    if hour != -1:
        min_str = f"{d.minute:02}"
        hour_str = f"{d.hour or 12}:{min_str} AM" \
            if d.hour < 12 else \
            f"{d.hour % 12}:{min_str} PM"
        data += f" @ {hour_str}"

    return d.toordinal(), data


def parse_event(raw):
    content, ts = "", 0.0
    for line in re.compile('\n').split(raw):
        dt = re.match("DTSTART;(VALUE=DATE:|TZID=.*?)(\d+)(\d\d)(\d\d)(T(\d\d)(\d\d)(\d\d))?", line)
        if dt:
            ts, content = date_str(dt.groups())
            continue
        desc = re.match("SUMMARY:(.*)", line)
        if desc:
            content += f" ~ {desc.group(1)}"
            continue
    return {"ts": ts, "content": content}


def size_check(size):
    print(f"\nSize: {size}\n")
    if size == int.from_bytes(alarm.sleep_memory[0:3], "big"):
        print("Data is probably unchanged. Going to sleep...")
        return True
    alarm.sleep_memory[0:3] = size.to_bytes(3, 'big')
    return False


def get_events(raw_data):
    if size_check(len(raw_data)):
        return

    raw_events = re.compile('END:VEVENT\nBEGIN:VEVENT').split(raw_data)
    events = list(map(parse_event, raw_events))
    events.sort(key=lambda x: x["ts"])

    for event in events:
        print(event["content"])


def bedtime():
    al = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 15)
    alarm.exit_and_deep_sleep_until_alarms(al)


def main():
    http = connect_wifi()
    raw_data = http.get(secrets["ticktick"]).text.replace('\r\n', '\n')
    get_events(raw_data)
    # bedtime()


if __name__ == "__main__":
    main()
