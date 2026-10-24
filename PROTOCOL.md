# Vesc world protocol, version 1 (`vw:1`)

How a device (a display, a phone app, a logger) hands its rides to
[@vescworldbot](https://t.me/vescworldbot). There is no server to call and no
account to request: the device writes into the owner's **personal Telegram
bot**, and @vescworldbot reads that chat with the bot token the owner gave it.

```
 device ──sendDocument──▶ personal bot chat ◀──getChat / getFile── @vescworldbot ──▶ Mini App
         (files, index, pinned summary)        (owner's token)
```

## 1. Roles

| Who | Does |
|---|---|
| **Owner** | Creates a bot in [@BotFather](https://t.me/BotFather), presses Start in it, gives the token to the device and to @vescworldbot. |
| **Device** | Sends files as documents to the owner's chat, keeps an index of what it sent, pins a summary line. Uses `sendDocument`, `sendMessage`, `editMessageText`, `pinChatMessage`, `deleteMessage`, `getUpdates` (only to learn the owner's chat id). |
| **@vescworldbot** | With the same token calls only `getMe`, `getChat` (to read the pinned message) and `getFile` (to download). It **never** calls `getUpdates` or `setWebhook`, so the device keeps the bot's update stream to itself. |

One personal bot = one vehicle. Several vehicles - several bots.

## 2. The owner's chat id

The device learns it once: after the owner presses Start, `getUpdates` holds a
message from a `private` chat - that chat id is the owner. Confirm the update
(`getUpdates` with `offset = update_id + 1`) and store the id.

## 3. Files

Send each file with `sendDocument` to the owner's chat. Recommended:

- **file name** `<device id>_<base name>` - files of several devices never clash in the chat;
- **caption** `vw:1;id=<device id>;kind=<kind>;path=<path>;size=<bytes>;mtime=<unix>;fw=<version>` - for humans and debugging, @vescworldbot does not rely on it;
- `disable_notification` - a ride is dozens of files.

From the reply keep `message_id` and `document.file_id`.
Telegram lets a bot download up to **20 MB** per file - keep files below that.

### Paths and kinds

The **path** is what the file is called on the device, card-style, from the root.
@vescworldbot decides what a file is by its path:

| Path | Kind | Parsed into |
|---|---|---|
| `/trips/<stem>.txt` | `trip` | a ride (section 5.1) |
| `/gps/<stem>.csv` | `gps` | the GPS track of the ride with the **same stem** (5.2) |
| `/ride/<stem>.csv` | `ride` | per-second controller telemetry of the ride with the **same stem** (5.6) |
| `/blackbox/<stem>.csv` | `bb` | a black box: charts around an event (5.3) |
| `/drag.csv` | `dragsum` | drag runs: 0-60, 100 m, 201 m (5.4) |
| `/service.csv` | `service` | consumables wear (5.5) |
| `/drag/…`, `/vesc/…`, anything else | `drag`, `vesc`, `file` | stored, not parsed |

**Stems** of rides:

- `YYYYMMDD_HHMM_rNNNN` - local start time and ride number, e.g. `20261024_1432_r0123`;
- `ride_NNNN` (optionally `ride_NNNN_2`) - when the device has no clock.

A dated stem is better: without a clock @vescworldbot can only number rides.
Black boxes may be named `YYYYMMDD_HHMMSS_bb…` for the same reason.

A file that changed on the device is simply sent again: the index then points
at the new `file_id`, and @vescworldbot re-reads it.

## 4. Index and pinned summary

### 4.1 Index

A tab-separated text file listing **everything already in the chat**, one line per file:

```
# vw:1 index id=DEMO-000001 fw=1.0.0 t=1792841525
/trips/20261024_1432_r0123.txt	612	134	BQACAgIAAxkDAAOG…	1792844380
/gps/20261024_1432_r0123.csv	5120	135	BQACAgIAAxkDAAOH…	1792844380
```

Columns: `path`, `size` (bytes), `message_id`, `file_id`, `mtime` (unix seconds,
optional but recommended - it dates rides when the device has no clock).
Lines starting with `#` are a header and are ignored.

After each upload session send the whole index as a document too (name
`<device id>_index.tsv`) and keep its `file_id`. The previous index message
may be deleted.

### 4.2 Pinned summary

One message in the owner's chat, pinned, edited after every session. Any text
for the human, plus **one machine line** (the display puts it into an
expandable quote):

```
vw:1;id=DEMO-000001;fw=1.0.0;odo_m=4812300;t=1792844390;n=5;idx=BQACAgIAAxkDAAOI…
```

| Key | Meaning |
|---|---|
| `id` | device id, **required**, stable for the vehicle (`[A-Za-z0-9_-]`, up to 32) |
| `fw` | firmware / app version |
| `odo_m` | odometer, metres |
| `t` | unix time of this summary (0 if the device has no clock) |
| `n` | number of files in the index |
| `idx` | `file_id` of the current index, **required** |

Pin it with `pinChatMessage` (`disable_notification: true`) **after every
session**, also when you only edited it - the owner may have unpinned it.
Do not delete the pinned summary: in private chats Telegram may then stop
reporting any pin in `getChat` until `unpinAllChatMessages` and a fresh pin. This is the only
place @vescworldbot looks: it reads `getChat(owner).pinned_message`, finds
`vw:1;`, downloads `idx` and fetches files whose `file_id` it has not seen.

## 5. File formats

All text is UTF-8, lines end with `\n`. Unknown keys and columns are ignored -
add your own freely. Missing values may be left out.

### 5.1 Ride - `/trips/<stem>.txt`

`key=value` per line. [Example](examples/card/trips/20261024_1432_r0123.txt).

| Key | Unit | Meaning |
|---|---|---|
| `ride` | | ride number |
| `start`, `end` | ISO 8601 with offset | `2026-10-24T14:32:05+03:00` |
| `distance_km` | km | |
| `riding_min`, `powered_min` | min | moving time, powered-on time |
| `max_speed_kph`, `avg_speed_kph` | km/h | average over moving time |
| `wh_used`, `wh_regen`, `wh_per_km` | Wh | |
| `ah_out`, `ah_in` | Ah | |
| `min_voltage` | V | sag |
| `max_bat_a`, `max_regen_a`, `max_motor_a` | A | regen as a positive number |
| `max_temp_esc`, `max_temp_motor` | °C | |
| `battery_end_pct` | % | |
| `odometer_km` | km | at the end |
| `gear` | | ride mode name |
| `vesc` | | `yes` - real ride, `sim` - simulator (kept apart in stats) |
| `device`, `fw` | | |

Several controllers: the keys above are for the whole vehicle, then per
controller `vescN_id` (`1 (master)` marks the master), `vescN_max_temp_esc`,
`vescN_max_temp_motor`, `vescN_max_motor_a`, `vescN_max_bat_a`,
`vescN_max_regen_a`, `vescN_wh_used`, `vescN_wh_regen`, `vescN_faults`
(N = 1…4) and `vescs=<count>`.

### 5.2 GPS track - `/gps/<stem>.csv`

[Example](examples/card/gps/20261024_1432_r0123.csv). Header comment, column line, then points:

```
# device=DEMO-000001 stem=20261024_1432_r0123 fw=1.0.0 tz_min=180 rate_hz=1
utc,lat,lon,kph,alt_m,course,sats,hdop
1792841525,55.752500,37.623100,0.0,150.0,40,6,2.4
```

`utc` - unix seconds; `lat`/`lon` - degrees; `tz_min` - the device's time zone
offset in minutes (lets @vescworldbot read the stem's local time). Points with
`lat=0,lon=0` are skipped; jumps faster than 60 m/s are not counted in the
distance. The stem must equal the ride's stem to be joined to it; a track
without a ride file becomes a ride by itself.

When a ride is shared by link, the first and last 300 m of the track are cut.

### 5.3 Black box - `/blackbox/<stem>.csv`

[Example](examples/card/blackbox/20261024_150211_bb.csv). Up to 60 s around an
event, about 20 frames a second.

```
# trigger=overheat odo_km=4806.9 frames=1200 time=2026-10-24T15:02:11+03:00
# per controller: vesc1=id 1 (master) vesc2=id 2
t_ms,speed_kph,voltage,bat_a,mot_a,temp_esc,temp_mot,duty,throttle,brake,fault,state,esc1_c,mot1_c,mot1_a,bat1_a,duty1,fault1,…
```

- `trigger` - `manual`, `overheat`, `vesc_fault`, `bms_stop`, `link_lost` (others are shown as is); a fault may add ` vesc2 id=32 fault=<code>`;
- `t_ms` - milliseconds, rising; the **last** frame is the event (time 0 on the charts);
- the listed columns are charted when present; `fault` ≠ 0 marks the frame. Per-controller columns `esc<N>_c`, `mot<N>_c`, `mot<N>_a`, `bat<N>_a`, `duty<N>`, `fault<N>` are optional.

### 5.4 Drag runs - `/drag.csv`

No header, `;`-separated, one run per line, appended:

```
runNo;t_cut0;t_cut1;t_cut2;t_100m;kph_100m;t_201m;kph_201m;max_w;max_a;slip_pct
1;2.10;3.85;0;8.10;62.0;12.40;66.5;9850;182;4.1
```

Times in seconds from the start of the run; 0 = not reached. `t_cut0..2` -
the three speed targets set on the device (MLTRA defaults: 0-30, 0-50,
0-100 km/h; the line does not say which were set, so readers should prefer the
distance marks `t_100m` / `t_201m` for comparing riders). `max_w` - peak
power, W; `slip_pct` - wheel slip estimate.

### 5.5 Consumables - `/service.csv`

```
# service device=DEMO-000001 fw=1.0.0
name,group,enabled,km,moving_h,cal_h,limit_km,limit_h,by_moving,used_pct
BRAKE PADS F,BRAKES,1,1650,40.2,2210.0,1800,0,1,92
```

`enabled=0` lines are ignored. `limit_km` / `limit_h` 0 = no limit of that
kind; `by_moving=1` - the hours limit counts moving hours, otherwise calendar
hours; `used_pct` - wear in percent of the nearest limit, `-1` = no limit.
Send it again whenever it changes.

### 5.6 Ride telemetry - `/ride/<stem>.csv`

[Example](examples/card/ride/20261024_1432_r0123.csv). Optional; gives a ride
its speed/power, temperature and voltage/current charts, GPS or not.
Header comment, column line, then one row a second while the vehicle moves or
draws current:

```
# vw:1 ride device=DEMO-000001 stem=20261024_1432_r0123 fw=1.0.0 rate_hz=1
s,utc,kph,volt,bat_a,mot_a,t_esc,t_mot,duty,thr,brk
13,1792841526,2.0,52.4,17.5,31.9,28,25,0.04,0.66,0.00
```

| Column | Meaning |
|---|---|
| `s` | seconds since the device powered up; a gap = standing still |
| `utc` | unix seconds, `0` while the device has no clock |
| `kph` | speed, average over the second |
| `volt` | battery voltage |
| `bat_a`, `mot_a` | battery and motor current, all controllers summed; negative = regen |
| `t_esc`, `t_mot` | controller and motor temperature, °C, the hottest controller |
| `duty`, `thr`, `brk` | duty cycle, throttle and brake, 0…1 |

Power is `volt × bat_a`. Write the file as the ride goes (append), so a pulled
plug loses at most the last rows; a cut last line is skipped. The stem must
equal the ride's stem; a log without a ride file becomes a ride by itself.

## 6. Owner side

1. [@BotFather](https://t.me/BotFather) → `/newbot` → token.
2. Open the new bot, press **Start**.
3. Give the token to the device (and let it upload once).
4. Send the token to [@vescworldbot](https://t.me/vescworldbot) **from the same
   Telegram account that pressed Start** (it reads the pinned message of *that*
   chat) - it deletes the
   message, checks the pinned summary and adds the vehicle. `/status` there
   shows what it sees.

The token gives @vescworldbot read access to that one chat; `/forget` in
@vescworldbot drops it. Revoking the token in @BotFather cuts everyone off.

## 7. Versioning

`vw:1` is this document. Additions that old readers can ignore (new keys,
columns, kinds) keep `vw:1`; an incompatible change will be `vw:2`, and
@vescworldbot will keep reading `vw:1`.
