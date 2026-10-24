# Vesc world protocol

Connect your own project - a display, a phone app, a data logger - to
**[Vesc world](https://t.me/vescworldbot)**: rides, GPS tracks, black boxes,
drag runs and consumables in a Telegram Mini App, with a garage, a community
leaderboard and share links.

There is no API key and no server to call. Your device uploads files into the
owner's **personal Telegram bot**; [@vescworldbot](https://t.me/vescworldbot)
reads that chat with the token the owner gives it. The same scheme the
[MLTRA VESC display](https://kamiyama.duckdns.org/esp/) uses.

```
 your device ──sendDocument──▶ owner's personal bot ◀──reads── @vescworldbot ──▶ Mini App
```

- **[PROTOCOL.md](PROTOCOL.md)** - the whole contract: the pinned `vw:1` line, the index, paths and every file format.
- **[examples/card/](examples/card/)** - one ride, its GPS track, a black box, drag runs and consumables, exactly as the display writes them.
- **[tools/vw_upload.py](tools/vw_upload.py)** - a working uploader (Python 3, standard library only). Point it at a folder laid out like the examples and it does the rest.

## Try it in five minutes

1. In [@BotFather](https://t.me/BotFather) create a bot (`/newbot`), copy the token.
2. Open your new bot and press **Start**.
3. Upload the sample ride:
   ```sh
   python3 tools/vw_upload.py --token <TOKEN> --dir examples/card --id DEMO-000001 --fw 1.0.0
   ```
   Your bot's chat now holds the files and a pinned summary.
4. Send the same token to [@vescworldbot](https://t.me/vescworldbot) and open the app.

Then make your device produce the same files (only the ride file is really
needed) and run the same steps - in your firmware, your app, or by calling the
script.

## Minimum

A device that only writes `/trips/<stem>.txt` with `start`, `distance_km`,
`max_speed_kph` and `wh_used`, sends it, sends the index and pins the `vw:1`
line already shows up with its rides, stats and achievements. Everything else
adds screens: the track adds the map, the black box adds charts.

## Where Telegram is blocked

`relay/vercel/` is a ready Bot API relay with a one-click Vercel deploy: the
device sends to the relay's address instead of `api.telegram.org`, the rest of
the protocol is unchanged.

## Questions, new fields

Open an issue. New keys and columns that old readers can ignore stay within
`vw:1`; tell us what you send and we will show it.

[Русский](README.ru.md) · License: MIT
