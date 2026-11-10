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
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
MODELLI = [MODEL, "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash-lite"]
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
                grezzo = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
                testo = re.sub(r"<[^>]+>", " ", grezzo)
                articoli.append({
                    "id": len(articoli),
                    "sezione": sezione,
                    "fonte": feed.feed.get("title", url)[:40],
                    "titolo": e.get("title", "").strip(),
                    "testo": " ".join(testo.split())[:900],
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
di 3-4 frasi (circa 60-90 parole) in italiano, chiaro e coinvolgente, con i dettagli concreti (numeri, nomi, date).
Ordina le sezioni e gli articoli per importanza: il primo articolo del primo blocco sarà la notizia di apertura. Usa SOLO informazioni presenti negli articoli.
Rispondi SOLO con JSON in questo formato:
{{"editoriale": "2 frasi che riassumono la giornata",
  "sezioni": [{{"nome": "...", "articoli": [{{"id": 0, "titolo": "titolo in italiano", "riassunto": "..."}}]}}]}}

ARTICOLI:
{elenco}"""
    corpo = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    ultimo_errore = None
    for modello in dict.fromkeys(MODELLI):
        for tentativo in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent",
                    headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                    json=corpo,
                    timeout=120,
                )
                if r.status_code in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"{r.status_code} su {modello} (tentativo {tentativo + 1})")
                r.raise_for_status()
                testo = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                print(f"Riassunto fatto con {modello}")
                return json.loads(testo)
            except RuntimeError as ex:  # server occupato: riprova dopo una pausa
                ultimo_errore = ex
                print(ex, file=sys.stderr)
                time.sleep(10 * (tentativo + 1))
            except Exception as ex:  # modello non valido o risposta strana: passa al prossimo
                ultimo_errore = ex
                print(f"{modello}: {ex}", file=sys.stderr)
                break
    raise RuntimeError(f"Tutti i modelli hanno fallito: {ultimo_errore}")


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


CSS = """
:root{--bg:#eaf0f8;--card:#ffffff;--ink:#0c1a2e;--soft:#566882;--line:#d5dfec;--hero1:#0f3d91;--hero2:#1f7ae0;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;--serif:"Iowan Old Style",Georgia,"Times New Roman",serif}
@media(prefers-color-scheme:dark){:root{--bg:#060d19;--card:#0e192b;--ink:#e8eef8;--soft:#8c9fba;--line:#1b2b45;--hero1:#0a2a63;--hero2:#1558b8}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:70px}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:17px/1.6 var(--serif);-webkit-text-size-adjust:100%}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);background:var(--bg);z-index:20}
.top{position:relative;overflow:hidden;color:#fff;padding:calc(env(safe-area-inset-top,0px) + 26px) 20px 30px;
background:linear-gradient(135deg,var(--hero1),var(--hero2))}
.top::after{content:"";position:absolute;inset:0;background:
repeating-linear-gradient(90deg,rgba(255,255,255,.07) 0 1px,transparent 1px 56px),
repeating-linear-gradient(0deg,rgba(255,255,255,.07) 0 1px,transparent 1px 56px);
mask-image:linear-gradient(to bottom,#000,transparent);-webkit-mask-image:linear-gradient(to bottom,#000,transparent);pointer-events:none}
.top>div{position:relative;max-width:1040px;margin:0 auto}
.top h1{margin:0;font:800 clamp(30px,6vw,46px)/1.05 var(--sans);letter-spacing:-.03em}
.top .sub{margin:8px 0 0;font:15px var(--sans);opacity:.85}
.top .ed{margin:18px 0 0;max-width:62ch;font:italic 19px/1.5 var(--serif);opacity:.95}
nav{position:sticky;top:env(safe-area-inset-top,0px);z-index:21;background:var(--bg);border-bottom:1px solid var(--line);
display:flex;gap:8px;overflow-x:auto;padding:10px 16px;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav a{flex:none;font:600 14px var(--sans);color:var(--ink);text-decoration:none;padding:7px 14px;border-radius:999px;
border:1.5px solid var(--c);background:var(--card)}
nav a:active,nav a:focus-visible{background:var(--c);color:#fff;outline:none}
main{max-width:1040px;margin:0 auto;padding:22px 16px calc(env(safe-area-inset-bottom,0px) + 44px)}
.lead{display:block;margin-bottom:34px;padding:24px 22px;border-radius:20px;color:#fff;text-decoration:none;
background:linear-gradient(160deg,#0c1f44,#13448f);box-shadow:0 10px 30px -12px rgba(10,40,100,.6)}
.lead .tag{font:600 14px var(--sans);opacity:.8}
.lead h2{margin:8px 0 12px;font:800 clamp(25px,4.6vw,36px)/1.12 var(--sans);letter-spacing:-.02em}
.lead p{margin:0 0 14px;font-size:18px;max-width:64ch;opacity:.95}
.lead .go{font:700 15px var(--sans)}
.grid{display:grid;gap:34px 28px;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr))}
section h2{display:flex;align-items:center;gap:10px;margin:0 0 14px;font:800 23px var(--sans);letter-spacing:-.02em}
section h2::before{content:"";width:12px;height:12px;border-radius:50%;background:var(--c);box-shadow:0 0 0 4px color-mix(in srgb,var(--c) 25%,transparent)}
section h2 span{margin-left:auto;font:600 13px var(--sans);color:var(--soft)}
article{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--c);border-radius:6px 16px 16px 6px;padding:16px 18px;margin-bottom:14px}
article h3{margin:0 0 8px;font:700 19px/1.3 var(--sans);letter-spacing:-.01em}
article p{margin:0 0 12px}
.meta{display:flex;justify-content:space-between;gap:12px;font:14px var(--sans);color:var(--soft)}
.meta a{color:var(--c);font-weight:700;text-decoration:none}
.meta a:hover,.meta a:focus-visible{text-decoration:underline}
footer{text-align:center;padding:0 16px 30px;font:13px var(--sans);color:var(--soft)}
"""

COLORI = ["#2f7bf5", "#e8960c", "#18a57a", "#e5484d", "#8b5cf6", "#d946a8"]


def render(dati, articoli):
    per_id = {a["id"]: a for a in articoli}
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
            "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    ora = datetime.now(TZ)
    data = f"{giorni[ora.weekday()]} {ora.day} {mesi[ora.month - 1]} {ora.year}"

    sezioni = []
    for s in dati.get("sezioni", []):
        voci = []
        for art in s.get("articoli", []):
            orig = per_id.get(art.get("id"))
            if orig:
                voci.append({"titolo": art.get("titolo") or orig["titolo"],
                             "riass": art.get("riassunto", ""),
                             "fonte": orig["fonte"], "link": orig["link"]})
        if voci:
            sezioni.append({"nome": s.get("nome", ""), "voci": voci})

    hero = ""
    if sezioni:
        v = sezioni[0]["voci"].pop(0)
        hero = (f'<a class="lead" href="{e(v["link"])}"><span class="tag">{e(sezioni[0]["nome"])} · notizia di apertura</span>'
                f'<h2>{e(v["titolo"])}</h2><p>{e(v["riass"])}</p><span class="go">Leggi l’articolo su {e(v["fonte"])} →</span></a>')
        if not sezioni[0]["voci"]:
            sezioni.pop(0)

    nav, blocchi = [], []
    for i, s in enumerate(sezioni):
        c = COLORI[i % len(COLORI)]
        sid = f"s{i}"
        nav.append(f'<a href="#{sid}" style="--c:{c}">{e(s["nome"])}</a>')
        arts = "".join(
            f'<article><h3>{e(v["titolo"])}</h3><p>{e(v["riass"])}</p>'
            f'<div class="meta"><span>{e(v["fonte"])}</span><a href="{e(v["link"])}">Leggi tutto</a></div></article>'
            for v in s["voci"])
        blocchi.append(f'<section id="{sid}" style="--c:{c}"><h2>{e(s["nome"])}<span>{len(s["voci"])}</span></h2>{arts}</section>')

    corpo = f'<div class="grid">{"".join(blocchi)}</div>' if blocchi else "<p>Nessuna notizia nuova oggi.</p>"
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Giornale">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0f3d91">
<title>Il Giornale di Nicco</title>
<style>{CSS}</style></head><body>
<header class="top"><div><h1>Il Giornale di Nicco</h1>
<p class="sub">{data} · aggiornato alle {ora.strftime("%H:%M")}</p>
<p class="ed">{e(dati.get("editoriale", ""))}</p></div></header>
<nav>{"".join(nav)}</nav>
<main>{hero}{corpo}</main>
<footer>Riassunti scritti da un’AI: per i dettagli apri l’articolo originale.</footer>
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
