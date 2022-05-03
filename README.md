# TickTick Display Reborn

> A rewrite of my original TickTick MagTag Display in CircuitPython.

## Screenshots

<p float="left">
  <img src="https://user-images.githubusercontent.com/2217505/166505448-14d6d3ce-7fc2-4232-a17b-113f1227265f.jpeg" width="400" />
  &nbsp; &nbsp; &nbsp; &nbsp;
  <img src="https://user-images.githubusercontent.com/2217505/166505454-787da871-3669-4353-a9eb-a04cec19fb12.jpeg" width="400" /> 
</p>

## Setup

### TickTick Events

This project requires the use of a [TickTick Events](https://github.com/ksmarty/ticktick-events) Vercel function. You
can either run a version yourself, or use the one hosted at https://ticktick-events.vercel.app. If you choose to run
your own, modify line 193 of `code.py`.

### Get TickTick UUID

1. Go to https://ticktick.com/signin and login
2. Go to https://www.ticktick.com/webapp/#settings/subscribe
3. Under `Subscribe TickTick in your calendar app`, click `Enable the URL > All Lists`
4. You will be given a link in the following format: `webcal://ticktick.com/pub/calendar/feeds/YOUR_UUID/basic.ics`

### Secrets

Ensure `secrets.py` has the following values:

- `ssid`: Wi-Fi Name / SSID
- `password`: Wi-Fi password
- `ticktick`: TickTick UUID

### Main Code

Copy `cody.py` and `assets/` to the root of my MagTag.

### Libraries

Copy the following [CircuitPython libraries](https://circuitpython.org/libraries) and place them in the `lib` folder on
the MagTag.

- `adafruit_bitmap_font/`
- `adafruit_datetime.mpy`
- `adafruit_display_shapes/`
- `adafruit_display_text/`
- `adafruit_esp32spi/`
- `adafruit_fakerequests.mpy`
- `adafruit_imageload/`
- `adafruit_io/`
- `adafruit_magtag/`
- `adafruit_ntp.mpy`
- `adafruit_portalbase/`
- `adafruit_requests.mpy`
- `neopixel.mpy`
- `simpleio.mpy`

## Additional Notes

- This project is intended to be run on an [Adafruit MagTag](https://www.adafruit.com/product/4800) with a battery. If
  running on connected power, it may not function properly.
- This project has no affiliation with TickTick.
- The font used is [ctrld](https://github.com/bjin/ctrld-font) by [bjin](https://github.com/bjin).
- If there are no events with dates or times in your lists, the display _will_ error out.
