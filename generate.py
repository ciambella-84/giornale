"""Il mio giornale AI: scarica notizie dai feed RSS, le fa riassumere a Gemini
e scrive docs/index.html. Modifica solo FEEDS qui sotto per personalizzare."""
import html, json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import feedparser
import requests

# ---- PERSONALIZZA QUI --------------------------------------------------
FEEDS = {
    "Aviazione": [
        "https://simpleflying.com/feed/",
        "https://avherald.com/h?subscribe=rss",
    ],
    "Hardware e prezzi": [
        "https://videocardz.com/feed",
        "https://www.tomshardware.com/feeds/all",
    ],
    "X-Plane e simulazione": [
        "https://developer.x-plane.com/feed/",
    ],
    "Roblox": [
        "https://blog.roblox.com/feed/",
    ],
    "Tennis": [
        "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
    ],
}
INTERESSI = (
    "aviazione civile (incidenti, nuovi aerei, compagnie, cargo DHL), "
    "X-Plane e flight simulation, prezzi e novità di RAM/GPU/CPU, "
    "Roblox, Minecraft, tennis"
)
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
MAX_PER_FEED = 8
ORE_RECENTI = 40
# ------------------------------------------------------------------------

TZ = ZoneInfo("Europe/Rome")


def fetch_articles():
    limite = datetime.now(timezone.utc) - timedelta(hours=ORE_RECENTI)
    articoli = []
    for sezione, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url, agent="Mozilla/5.0 giornale-ai")
            except Exception as e:
                print(f"Feed fallito {url}: {e}", file=sys.stderr)
                continue
            for e in feed.entries[:MAX_PER_FEED]:
                t = e.get("published_parsed") or e.get("updated_parsed")
                if t and datetime(*t[:6], tzinfo=timezone.utc) < limite:
                    continue
                testo = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
                articoli.append({
                    "id": len(articoli),
                    "sezione": sezione,
                    "fonte": feed.feed.get("title", url)[:40],
                    "titolo": e.get("title", "").strip(),
                    "testo": " ".join(testo.split())[:300],
                    "link": e.get("link", ""),
                })
    return articoli


def chiedi_a_gemini(articoli):
    elenco = "\n".join(
        f'[{a["id"]}] ({a["sezione"]}) {a["titolo"]} - {a["testo"]}' for a in articoli
    )
    prompt = f"""Sei il direttore di un piccolo giornale personale per un ragazzo italiano appassionato di: {INTERESSI}.
Qui sotto trovi gli articoli di oggi, ognuno con un [id]. Scegli solo i più interessanti
(massimo 4 per sezione, salta doppioni e roba banale) e scrivi per ognuno un riassunto
di 1-2 frasi in italiano, chiaro e diretto. Usa SOLO informazioni presenti negli articoli.
Rispondi SOLO con JSON in questo formato:
{{"editoriale": "2 frasi che riassumono la giornata",
  "sezioni": [{{"nome": "...", "articoli": [{{"id": 0, "titolo": "titolo in italiano", "riassunto": "..."}}]}}]}}

ARTICOLI:
{elenco}"""
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
        },
        timeout=120,
    )
    r.raise_for_status()
    testo = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(testo)


def fallback(articoli):
    """Se l'AI non risponde, mostra comunque i titoli grezzi."""
    sezioni = {}
    for a in articoli:
        sezioni.setdefault(a["sezione"], []).append(
            {"id": a["id"], "titolo": a["titolo"], "riassunto": ""})
    return {
        "editoriale": "Il riassunto AI non è disponibile oggi: ecco i titoli grezzi.",
        "sezioni": [{"nome": n, "articoli": v[:4]} for n, v in sezioni.items()],
    }


def e(s):
    return html.escape(str(s), quote=True)


def render(dati, articoli):
    per_id = {a["id"]: a for a in articoli}
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
            "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    ora = datetime.now(TZ)
    data = f"{giorni[ora.weekday()]} {ora.day} {mesi[ora.month - 1]} {ora.year}"

    blocchi = []
    for s in dati.get("sezioni", []):
        voci = []
        for art in s.get("articoli", []):
            orig = per_id.get(art.get("id"))
            if not orig:
                continue
            riass = f'<p>{e(art.get("riassunto", ""))}</p>' if art.get("riassunto") else ""
            voci.append(
                f'<article><h3><a href="{e(orig["link"])}">{e(art.get("titolo") or orig["titolo"])}</a></h3>'
                f'{riass}<small>{e(orig["fonte"])}</small></article>'
            )
        if voci:
            blocchi.append(f'<section><h2>{e(s.get("nome", ""))}</h2>{"".join(voci)}</section>')

    corpo = "".join(blocchi) or "<p>Nessuna notizia nuova oggi.</p>"
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Giornale">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Il Giornale di Nicco</title>
<style>
:root{{--bg:#eef2f7;--card:#fff;--ink:#0e1a2b;--soft:#52627a;--line:#d3dbe6;--accent:#1f5fe0;--head:#0e1a2b;--headink:#eef2f7;
box-sizing:border-box;padding-bottom:env(safe-area-inset-bottom,0px)}}
@media(prefers-color-scheme:dark){{:root{{--bg:#08101c;--card:#101c2e;--ink:#e6edf7;--soft:#8fa1ba;--line:#1d2c44;--accent:#6ea0ff;--head:#050a12;--headink:#e6edf7}}}}
*{{box-sizing:border-box}}
html,body{{margin:0}}
body{{background:var(--bg);color:var(--ink);font:17px/1.55 Georgia,"Times New Roman",serif}}
header{{background:var(--head);color:var(--headink);padding:calc(env(safe-area-inset-top,0px) + 22px) 20px 20px}}
header h1{{margin:0;font:800 30px/1.1 "Helvetica Neue",Arial,sans-serif;letter-spacing:-.02em}}
header .data{{margin:4px 0 0;font:14px "Helvetica Neue",Arial,sans-serif;opacity:.7}}
main{{max-width:680px;margin:0 auto;padding:18px 16px 40px}}
.edit{{border-left:4px solid var(--accent);padding:2px 0 2px 14px;margin:6px 0 26px;font-style:italic}}
section{{margin-bottom:28px}}
h2{{font:700 20px "Helvetica Neue",Arial,sans-serif;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid var(--accent)}}
article{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:10px}}
h3{{margin:0 0 4px;font:700 18px/1.3 "Helvetica Neue",Arial,sans-serif}}
h3 a{{color:inherit;text-decoration:none}} h3 a:focus-visible,h3 a:hover{{color:var(--accent);text-decoration:underline}}
article p{{margin:4px 0 8px}} small{{color:var(--soft);font:13px "Helvetica Neue",Arial,sans-serif}}
</style></head><body>
<header><h1>Il Giornale di Nicco</h1><p class="data">{data}</p></header>
<main><p class="edit">{e(dati.get("editoriale", ""))}</p>{corpo}</main>
</body></html>"""


def main():
    articoli = fetch_articles()
    print(f"{len(articoli)} articoli scaricati")
    try:
        dati = chiedi_a_gemini(articoli) if articoli else fallback(articoli)
    except Exception as ex:
        print(f"Gemini fallito: {ex}", file=sys.stderr)
        dati = fallback(articoli)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(render(dati, articoli))
    print("docs/index.html scritto")


if __name__ == "__main__":
    main()
