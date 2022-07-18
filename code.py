import math
import ssl
import time

import adafruit_requests as requests
import alarm
import displayio
import socketpool
from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime
from adafruit_display_shapes import circle, roundrect, rect
from adafruit_display_text import label
from adafruit_imageload import load as load_img
from adafruit_magtag.magtag import MagTag
from wifi import radio

try:
    from secrets import secrets
except ImportError:
    print("Secrets file is missing for malformed!")
    raise

magtag = MagTag()


# Sleep Memory Addresses
# ----------------------------------------------------------------
# [0:3] - Last ICS size, currently unused
# [3:4] - WiFi error count
# [10:14] - Epoch time at start of execution


class Color:
    white = 0xFFFFFF
    lgrey = 0xACACAC
    dgrey = 0x535353
    black = 0x0


def setup():
    magtag.peripherals.neopixel_disable = True
    magtag.peripherals.speaker_disable = True
    loading()


def loading():
    if alarm.wake_alarm:
        return

    font_lg = bitmap_font.load_font("assets/ctrld-fixed-16r.pcf")
    sw = 296
    sh = 128

    group = displayio.Group()
    # Loading text
    group.append(label.Label(
        font_lg,
        text="Loading",
        x=int((sw - 7 * 8) / 2),
        y=int(sh / 2) - 5,
        color=Color.black,
        base_alignment=True
    ))
    # Outer loading bar
    group.append(roundrect.RoundRect(
        x=int((sw - 7 * 8) / 2),
        y=int(sh / 2) + 5,
        width=7 * 8,
        height=10,
        r=5,
        outline=Color.black,
        stroke=2
    ))
    # Inner loading bar
    group.append(roundrect.RoundRect(
        x=int((sw - 7 * 8) / 2) + 3,
        y=int(sh / 2) + 5 + 3,
        width=int(7 * 8 / 2) + 5,
        height=4,
        r=2,
        outline=Color.black,
        stroke=2
    ))
    magtag.splash.append(group)
    magtag.refresh()
    magtag.splash.append(rect.Rect(x=0, y=0, width=sw, height=sh, fill=Color.white))  # Clear screen


def error(msg: str, dur=10.0):
    font_sm = bitmap_font.load_font("assets/ctrld-fixed-10r.pcf")
    font_lg = bitmap_font.load_font("assets/ctrld-fixed-16r.pcf")
    tri_bmp, tri_shd = load_img("assets/triangle.bmp")
    sw = 296
    # sh = 128

    group = displayio.Group()
    title = "ERROR"
    title_x = int((sw - len(title) * 8) / 2)
    msg += "\nTrying again in {}{}...".format(f"{int(dur)} minute" if dur >= 1 else f"{int(dur * 60)} second",
                                              's' if dur != 1 or dur <= (1 / 60) else '')

    # Header Box
    group.append(rect.Rect(
        x=0,
        y=0,
        width=sw,
        height=15,
        fill=Color.black
    ))
    # Header Title
    group.append(label.Label(
        font_lg,
        text=title,
        x=title_x,
        y=6,
        color=Color.white
    ))
    # Left Warning Triangle
    group.append(displayio.TileGrid(
        tri_bmp,
        pixel_shader=tri_shd,
        tile_width=11,
        tile_height=9,
        x=title_x - 11 - 5,
        y=3
    ))
    # Right Warning Triangle
    group.append(displayio.TileGrid(
        tri_bmp,
        pixel_shader=tri_shd,
        tile_width=11,
        tile_height=9,
        x=sw - title_x + 5,
        y=3
    ))
    # Error Message
    group.append(label.Label(
        font_sm,
        text=msg,
        x=3,
        y=23,
        color=Color.black
    ))

    magtag.splash.append(group)
    magtag.refresh()
    bedtime(dur)


# def boot_time():
#     size = int.from_bytes(alarm.sleep_memory[10:14], "big") + 1
#     alarm.sleep_memory[10:14] = size.to_bytes(4, 'big')
#     return size


def connect_wifi():
    try:
        radio.connect(secrets["ssid"], secrets["password"])
    except ConnectionError:
        # Increase retry time exponentially
        duration = alarm.sleep_memory[3]
        alarm.sleep_memory[3] *= 2
        error("Could not connect to WiFi!", duration)
    finally:
        # Clear WiFi error count
        alarm.sleep_memory[3] = 1

    # return fetch object
    # noinspection PyArgumentList, PyTypeChecker
    http = requests.Session(socketpool.SocketPool(radio), ssl.create_default_context())

    if not http:
        error("Could not open a socket!", 0.25)

    return http


# Check if length of raw data is the same as last time
def size_check(size):
    print(f"\nSize: {size}\n")
    if size == int.from_bytes(alarm.sleep_memory[0:3], "big"):
        print("Data is probably unchanged. Going to sleep...")
        return True
    alarm.sleep_memory[0:3] = size.to_bytes(3, 'big')
    return False


def get_events(http: requests.Session):
    raw_data = None
    timestamp = None

    try:
        body = {
            "id"           : secrets["ticktick"],
            "voltage"      : magtag.peripherals.battery,
            "upstash_url"  : secrets["upstash_url"],
            "upstash_token": secrets["upstash_token"],
        }
        req = http.post("https://ticktick-events.vercel.app/api/events", json=body)
        raw_data = req.json()

        timestamp = datetime.fromisoformat(raw_data["timestamp"])
    except RuntimeError:
        error("Failed getting events from TickTick!", 0.25)

    # Size check
    if size_check(len(raw_data)):
        bedtime(60)

    return [raw_data["events"], timestamp]


def curve(x):
    return -1.69766 * 10 ** -15 * x ** 7 + \
           1.28507 * 10 ** -12 * x ** 6 + \
           -3.8474 * 10 ** -10 * x ** 5 + \
           5.77331 * 10 ** -8 * x ** 4 + \
           -4.56812 * 10 ** -6 * x ** 3 + \
           0.000187889 * x ** 2 + \
           -0.00520139 * x + \
           4.09916


def battery_status():
    # Datasheet: https://cdn-shop.adafruit.com/product-files/4236/4236_ds_LP552535+420mAh+3.7V.pdf
    # Graph calculated from recorded data
    volts = magtag.peripherals.battery
    percent = min((curve(volts * -228 + 934.996) * 0.943 - 2.8635) * 100, 100)
    return math.ceil((percent - 10) / 16)


def month_str(x: int, long=False):
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


# def month_num(x: str, long=False):
#     s = None if long else 3
#     return {
#         "January"[:s]  : 1,
#         "February"[:s] : 2,
#         "March"[:s]    : 3,
#         "April"[:s]    : 4,
#         "May"[:s]      : 5,
#         "June"[:s]     : 6,
#         "July"[:s]     : 7,
#         "August"[:s]   : 8,
#         "September"[:s]: 9,
#         "October"[:s]  : 10,
#         "November"[:s] : 11,
#         "December"[:s] : 12,
#     }[x]


def draw(events, today: datetime):
    font_sm = bitmap_font.load_font("assets/ctrld-fixed-10r.pcf")
    font_lg = bitmap_font.load_font("assets/ctrld-fixed-16r.pcf")
    bat_bmp, bat_shd = load_img("assets/battery.bmp")

    # events = filter(lambda x: x[0].isoformat() >= today.date().isoformat(), events)

    title_group = displayio.Group()

    # Title
    title_group.append(label.Label(
        font_sm,
        color=Color.black,
        x=93,
        y=8,
        text="~ TickTick To-Do ~",
    ))
    # Updated
    title_group.append(label.Label(
        font_sm,
        color=Color.black,
        x=170,
        y=119,
        text="Updated: {}".format(str(today).replace('-', '/')[5:-16]),
    ))
    # Unplugged
    # title_group.append(label.Label(
    #     font_sm,
    #     color=Color.black,
    #     x=7,
    #     y=119,
    #     text="Unplugged: {} hours".format(boot_time() - 1),
    # ))

    # Draw battery
    battery_group = displayio.Group(x=274, y=4)
    icon = displayio.TileGrid(
        bat_bmp,
        pixel_shader=bat_shd,
        tile_width=16,
        tile_height=8,
    )
    icon[0] = battery_status()  # First index is the icon to show
    battery_group.append(icon)

    # Add to screen
    magtag.splash.append(title_group)
    magtag.splash.append(battery_group)

    if events is not None:
        # Current Month, Current Day, Current Height
        crm, crd, crh = 0, 0, 8

        for event in events:
            title, content, ts = event["title"], event["description"], datetime.fromisoformat(event["start"])

            # Month header
            if ts.month != crm:
                crm = ts.month
                # Add month
                magtag.splash.append(label.Label(
                    font_sm,
                    text=month_str(crm),
                    color=Color.black,
                    x=7,
                    y=crh
                ))
                crh += 14

            # Event item
            item_group = displayio.Group(x=10, y=crh)

            # Add number for first event of the day
            if crd != ts.toordinal():
                crd = ts.toordinal()

                # Add circle if event is today
                if ts.isoformat()[:10] == today.date().isoformat():
                    item_group.append(circle.Circle(5, 5, 11, fill=Color.lgrey))

                # Event day #
                item_group.append(label.Label(
                    font_lg,
                    text=str(ts.day),
                    color=Color.black,
                    x=-3 if ts.day > 9 else 1,  # 1 for 1 digit, -3 for 2 digits
                    y=4
                ))

            has_time = str(ts.time()) != "00:00:00"

            # Event background
            item_group.append(roundrect.RoundRect(
                x=23,
                y=-6,
                width=217 if has_time else 258,
                height=22,
                r=4,
                fill=Color.lgrey
            ))
            # Event text
            item_group.append(label.Label(
                font_lg,
                text=title[:(26 if has_time else 31)],
                color=Color.black,
                x=27,
                y=4,
            ))
            # Event time
            if has_time:
                item_group.append(roundrect.RoundRect(
                    x=242,
                    y=-6,
                    width=38,
                    height=22,
                    r=4,
                    fill=Color.lgrey
                ))
                item_group.append(label.Label(
                    font_sm,
                    text=f"{ts.hour:>2}:{ts.minute:02}",
                    color=Color.black,
                    x=246,
                    y=5,
                ))

            magtag.splash.append(item_group)

            crh += 24
            # Drawing cutoff
            if crh > 100:
                break

    time.sleep(magtag.display.time_to_refresh + 1)
    magtag.refresh()


def bedtime(duration: int | float):
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + duration * 60)
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


def main():
    setup()
    http = connect_wifi()
    [events, timestamp] = get_events(http)
    draw(events, timestamp)
    bedtime(60)


if __name__ == "__main__":
    main()
