# Il Giornale di Nicco: setup (10 minuti)

1. **Chiave Gemini (gratis):** vai su aistudio.google.com → "Get API key" → copiala.
2. **Repository:** su github.com crea un repo nuovo (es. `giornale`) e carica tutti questi file,
   mantenendo la cartella `.github/workflows/`.
3. **Segreto:** repo → Settings → Secrets and variables → Actions → New repository secret →
   nome `GEMINI_API_KEY`, valore la chiave.
4. **Primo avvio:** tab Actions → "Giornale quotidiano" → Run workflow. Aspetta ~1 minuto.
5. **Pubblica:** Settings → Pages → Source: "Deploy from a branch" → branch `main`, cartella `/docs` → Save.
6. **iPhone:** apri l'indirizzo `https://TUOUTENTE.github.io/giornale/` in Safari →
   Condividi → "Aggiungi alla schermata Home".

Da quel momento si aggiorna da solo ogni mattina.

Personalizzare: modifica `FEEDS` e `INTERESSI` in cima a `generate.py`.
Se un feed non funziona (log in Actions), sostituiscilo con un altro URL RSS.
