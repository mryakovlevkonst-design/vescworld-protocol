#!/usr/bin/env python3
"""Reference Vesc world uploader - the same steps the MLTRA display does.

Sends every new or changed file of a local folder (laid out like the SD card,
see PROTOCOL.md) to the owner's personal Telegram bot, uploads the index and
keeps the pinned vw:1 summary up to date. Python 3.8+, standard library only.

    python3 vw_upload.py --token 123456:ABC... --dir ./card --id MYBIKE-0001 --fw 1.0.0

First run: open your bot in Telegram and press Start (or send it anything),
then run the script - it remembers you as the owner.

State lives next to the folder in <dir>/.vw/ (index.tsv + state.json); delete
it to send everything again.
"""
import argparse, json, mimetypes, os, sys, time, uuid, urllib.request, urllib.error

API = "https://api.telegram.org/bot{token}/{method}"
SKIP_DIRS = {".vw", ".git"}


class Bot:
    def __init__(self, token):
        self.token = token

    def call(self, method, data=None, files=None):
        url = API.format(token=self.token, method=method)
        if files:
            body, ctype = multipart(data or {}, files)
        else:
            body, ctype = json.dumps(data or {}).encode(), "application/json"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": ctype})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)["result"]
            except urllib.error.HTTPError as e:
                err = json.load(e)
                retry = (err.get("parameters") or {}).get("retry_after")
                if e.code == 429 and retry:           # flood control: wait as told
                    time.sleep(retry + 1)
                    continue
                raise RuntimeError(f"{method}: {err.get('description')}") from None
        raise RuntimeError(f"{method}: too many retries")


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (name, data) in files.items():
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        out += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def kind_of(path):
    for prefix, kind in (("/trips/", "trip"), ("/gps/", "gps"), ("/ride/", "ride"), ("/blackbox/", "bb"), ("/drag/", "drag")):
        if path.startswith(prefix):
            return kind
    return {"/drag.csv": "dragsum", "/service.csv": "service"}.get(path, "file")


def scan(root):
    """Card paths ("/trips/x.txt") -> (abs path, size, mtime)."""
    out = {}
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for n in names:
            if n.startswith("."):
                continue
            p = os.path.join(d, n)
            st = os.stat(p)
            out["/" + os.path.relpath(p, root).replace(os.sep, "/")] = (p, st.st_size, int(st.st_mtime))
    # trips before their GPS tracks and logs, like the display does
    order = {"trip": 0, "service": 1, "ride": 2, "gps": 2, "dragsum": 3, "drag": 4, "bb": 5}
    return dict(sorted(out.items(), key=lambda kv: (order.get(kind_of(kv[0]), 9), kv[0])))


def load_index(path):
    idx = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            idx[c[0]] = {"size": int(c[1]), "mid": int(c[2]), "fid": c[3], "mtime": int(c[4]) if len(c) > 4 else 0}
    return idx


def save_index(path, idx, dev, fw):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# vw:1 index id={dev} fw={fw} t={int(time.time())}\n")
        for p, e in idx.items():
            f.write(f"{p}\t{e['size']}\t{e['mid']}\t{e['fid']}\t{e['mtime']}\n")


def find_owner(bot):
    for u in bot.call("getUpdates", {"timeout": 0, "allowed_updates": ["message"]}):
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            bot.call("getUpdates", {"offset": u["update_id"] + 1, "timeout": 0})   # confirm
            return chat["id"]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--token", required=True, help="your personal bot token from @BotFather")
    ap.add_argument("--dir", required=True, help="folder laid out like the card: trips/ gps/ blackbox/ ...")
    ap.add_argument("--id", required=True, help="device id, stable per vehicle, e.g. MYBIKE-0001")
    ap.add_argument("--fw", default="0", help="your firmware/app version")
    ap.add_argument("--odo-km", type=float, default=0, help="odometer for the summary")
    ap.add_argument("--owner", type=int, help="owner chat id, if you already know it (skips waiting for Start)")
    a = ap.parse_args()

    root = os.path.abspath(a.dir)
    vw = os.path.join(root, ".vw")
    os.makedirs(vw, exist_ok=True)
    idx_path, st_path = os.path.join(vw, "index.tsv"), os.path.join(vw, "state.json")
    st = json.load(open(st_path)) if os.path.exists(st_path) else {}
    bot = Bot(a.token)
    me = bot.call("getMe")
    print(f"bot @{me['username']}")

    if a.owner:
        st["owner"] = a.owner
    if not st.get("owner"):
        st["owner"] = find_owner(bot)
        if not st["owner"]:
            sys.exit(f"open @{me['username']} in Telegram, press Start, then run this again")
        print(f"owner chat {st['owner']}")
        json.dump(st, open(st_path, "w"), indent=1)
    owner = st["owner"]

    idx = load_index(idx_path)
    sent = 0
    for path, (abs_p, size, mtime) in scan(root).items():
        old = idx.get(path)
        if old and old["size"] == size and old["mtime"] == mtime:
            continue
        cap = f"vw:1;id={a.id};kind={kind_of(path)};path={path};size={size};mtime={mtime};fw={a.fw}"
        name = f"{a.id}_{os.path.basename(path)}"
        with open(abs_p, "rb") as f:
            m = bot.call("sendDocument", {"chat_id": owner, "caption": cap, "disable_notification": "true"},
                         {"document": (name, f.read())})
        idx[path] = {"size": size, "mid": m["message_id"], "fid": m["document"]["file_id"], "mtime": mtime}
        save_index(idx_path, idx, a.id, a.fw)        # after every file: a crash loses nothing
        sent += 1
        print(f"sent {path}")
    if not sent and st.get("idx_fid"):
        print("nothing new")
        return

    save_index(idx_path, idx, a.id, a.fw)
    with open(idx_path, "rb") as f:
        m = bot.call("sendDocument", {"chat_id": owner, "disable_notification": "true",
                                      "caption": f"vw:1;id={a.id};kind=index;n={len(idx)};t={int(time.time())};fw={a.fw}"},
                     {"document": (f"{a.id}_index.tsv", f.read())})
    if st.get("idx_mid"):                            # the previous index is stale now
        try:
            bot.call("deleteMessage", {"chat_id": owner, "message_id": st["idx_mid"]})
        except RuntimeError:
            pass
    st["idx_mid"], st["idx_fid"] = m["message_id"], m["document"]["file_id"]

    text = (f"📊 <b>Vesc world</b> · {a.id}\nFirmware {a.fw} · odometer {a.odo_km:.0f} km\n"
            f"Files in the cloud: {len(idx)}\n\n"
            f"<blockquote expandable>vw:1;id={a.id};fw={a.fw};odo_m={int(a.odo_km * 1000)};"
            f"t={int(time.time())};n={len(idx)};idx={st['idx_fid']}</blockquote>")
    try:
        if not st.get("pin_mid"):
            raise RuntimeError("no pin yet")
        bot.call("editMessageText", {"chat_id": owner, "message_id": st["pin_mid"], "text": text, "parse_mode": "HTML"})
    except RuntimeError:
        st["pin_mid"] = bot.call("sendMessage", {"chat_id": owner, "text": text, "parse_mode": "HTML"})["message_id"]
    bot.call("pinChatMessage", {"chat_id": owner, "message_id": st["pin_mid"], "disable_notification": True})
    json.dump(st, open(st_path, "w"), indent=1)
    print(f"done: {sent} new, {len(idx)} in the cloud, summary pinned")


if __name__ == "__main__":
    main()
