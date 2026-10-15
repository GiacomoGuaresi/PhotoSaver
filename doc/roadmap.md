# Roadmap (bozza)

Sviluppo a **piccoli incrementi**, come in PrintPicker: ogni step è piccolo,
testabile e lascia il progetto funzionante.

## Regole di lavoro

- **Uno step = un commit.** Se uno step è troppo grande, si divide in `3a`, `3b`, …
- **Definition of done**: funziona sui dischi simulati (`dev-disks/`), test
  verdi (`pytest`), lint pulito (`ruff`), documentazione in `doc/` aggiornata,
  commit [Conventional Commits](https://www.conventionalcommits.org/).
- La logica (indice, hash, copia, check) vive in moduli **senza Qt**, testabili
  da soli; la UI si limita a chiamarli.
- **Sicurezza dei dati prima di tutto**: ogni operazione che scrive sui dischi
  ha test sugli scenari di guasto (interruzione, file corrotto, disco mancante).

Legenda: ⬜ da fare · 🔄 in corso · ✅ fatto

---

## M0 — Fondamenta

| # | Step | Commit | Stato |
|---|---|---|---|
| 0.1 | `git init`, `README.md`, `LICENSE`, `.gitignore`, `doc/` | `first commit` | ✅ |
| 0.2 | `pyproject.toml` (uv), `src/photosaver/`, `tests/`, pytest + ruff | `chore: python project skeleton` | ✅ |
| 0.3 | CI: lint + test su **Linux e Windows** | `ci: lint and test` | ✅ |
| 0.4 | `scripts/dev_disks.py`: crea `dev-disks/` con foto finte generate (EXIF, GPS, date, nomi Samsung/WhatsApp, video, file da ignorare) | `chore(dev): simulated disks generator` | ✅ |

## M1 — Motore: disco, indice, copia sicura (senza UI) → `v0.1.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 1.1 | **Disco**: `.photosaver/disk.json` (id disco, id archivio, cartella archivio); creazione e lettura | `feat(core): disk identity` | ✅ |
| 1.2 | **Indice** SQLite con schema versionato, pensato per N dischi: file, hash, stato per disco, storico | `feat(core): versioned index` | ✅ |
| 1.3 | **Scanner**: solo foto e video, conteggio dei file ignorati, file temporanei e `._*` di macOS esclusi | `feat(core): media scanner` | ✅ |
| 1.4 | **Hash** in streaming: SHA-256 (veloce, verificabile anche senza l'app) | `feat(core): file hashing` | ✅ |
| 1.5 | **Copia sicura**: file `.partial` → flush → rilettura e verifica dell'hash → rinomina; data di modifica conservata | `feat(core): verified safe copy` | ✅ |
| 1.6 | **CLI di debug** (`python -m photosaver.cli`): init, scan, status | `feat(cli): debug commands` | ✅ |

## M2 — Operazioni: carica, check, ripara (senza UI) → `v0.2.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 2.1 | **Piano di caricamento**: date (EXIF → nome file → data di modifica), destinazione proposta, doppioni, conflitti di nome | `feat(upload): upload plan` | ✅ |
| 2.2 | **Caricamento** su tutti i dischi, con ripresa dopo un'interruzione | `feat(upload): apply to all disks` | ✅ |
| 2.3 | **Check rapido**: confronto indice ↔ dischi per dimensione e data → differenze tipizzate | `feat(check): quick check` | ✅ |
| 2.4 | **Check completo** con hash, ripresa dopo un'interruzione, riconoscimento della corruzione (hash diverso + stessa data) | `feat(check): full check with bit rot detection` | ✅ |
| 2.5 | Riconoscimento di **spostamenti e rinomine** tramite hash | `feat(check): detect moves` | ✅ |
| 2.6 | **Cestino** (a tempo e manuale) e **problemi noti** | `feat(core): trash and known issues` | ✅ |
| 2.7 | **Azioni**: ripara, copia mancanti, propaga cancellazioni e spostamenti; azione proposta per i casi ovvi | `feat(check): resolution actions` | ✅ |
| 2.8 | **Journal delle operazioni**: un'operazione interrotta si riconosce e si completa o annulla; indici di A e B riallineati | `feat(core): operation journal` | ✅ |
| 2.9 | Script per gli **scenari di guasto** in `dev_disks.py` + test end-to-end | `test: failure scenarios` | ✅ |

## M3 — Interfaccia: il flusso completo → `v0.3.0`

Interfaccia "granny software" (vedi [flussi](flussi.md)): una **home** con pochi
pulsanti grandi, ogni funzione è una procedura a passi; Storico e Cestino nel
menu "Altro".

| # | Step | Commit | Stato |
|---|---|---|---|
| 3.1 | Finestra, tema leggibile (testi grandi, contrasto alto), schermate a passi con "Indietro", home, barra dei dischi, italiano e inglese | `feat(ui): main window and theme` | ✅ |
| 3.2 | **Collega i dischi**: riconoscimento dei dischi (in sviluppo: percorsi configurati), schermata d'attesa, sola lettura con un disco, controllo veloce all'avvio, "Ho finito" | `feat(ui): connect disks` | ✅ |
| 3.3 | **Prepara i dischi**: procedura guidata per creare l'archivio (sui dischi simulati, senza formattazione) | `feat(ui): prepare disks wizard` | ✅ |
| 3.4 | **Aggiungi foto**: scelta cartelle, anteprima, copia con avanzamento, proposta di eliminare gli originali | `feat(ui): add photos flow` | ✅ |
| 3.5 | **Controlla i dischi**: controllo veloce e approfondito, problemi raggruppati con l'azione proposta, operazioni interrotte | `feat(ui): check flow` | ⬜ |
| 3.6 | **Storico** e **Cestino** | `feat(ui): history and trash` | ⬜ |

## M4 — Visualizzatore → `v0.4.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 4.1 | Albero delle cartelle + griglia di miniature | `feat(viewer): folder tree and grid` | ⬜ |
| 4.2 | **Miniature salvate sui dischi** (`.photosaver/`), generate in background | `feat(viewer): on-disk thumbnails` | ⬜ |
| 4.3 | Anteprima grande di foto e **video** | `feat(viewer): fullscreen preview` | ⬜ |
| 4.4 | Indicatori di stato per file e cartelle | `feat(viewer): sync status badges` | ⬜ |
| 4.5 | **Modifiche**: rinomina, sposta, cancella, nuova cartella, su entrambi i dischi | `feat(viewer): edit operations` | ⬜ |

## M5 — Dischi veri → `v0.5.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 5.1 | Riconoscimento automatico dei dischi collegati (volumi montati) + collegamento/scollegamento a caldo | `feat(disks): volume detection` | ⬜ |
| 5.2 | Test su **immagine exFAT** montata in loop: maiuscole/minuscole, precisione delle date | `test: exfat behaviour` | ⬜ |
| 5.3 | **Formattazione exFAT** nella procedura guidata (Linux, Windows) con permessi di amministratore | `feat(disks): exfat formatting` | ⬜ |
| 5.4 | **Sostituisci disco**: nuovo disco + copia completa verificata dal disco sano | `feat(disks): replace disk` | ⬜ |
| 5.5 | **Promemoria** per il check completo + prestazioni su USB (letture in parallelo, stima dei tempi) | `feat(check): reminder and usb performance` | ⬜ |

## M6 — Distribuzione → `v1.0.0` (MVP)

| # | Step | Commit | Stato |
|---|---|---|---|
| 6.1 | Build PyInstaller *onedir* per **Linux e Windows**, con self-test | `build: pyinstaller packages` | ⬜ |
| 6.2 | **App portatile sui dischi**: cartella `PhotoSaver/` sincronizzata tra i dischi | `feat(dist): portable app on disks` | ⬜ |
| 6.3 | Release su GitHub + aggiornamento dell'app sui dischi | `feat(dist): updates` | ⬜ |
| 6.4 | **Ricaricamento dell'archivio vecchio** (~400 GB) sui due dischi nuovi: prova sul campo | — | ⬜ |

## Dopo l'MVP

- **M7 — Mappa e ricerca**: GPS su mappa (WebEngine + Leaflet + cluster), ricerca e filtri.
- **macOS**: build universal2, firma e notarizzazione.
- **Terza copia**: interfaccia per N dischi.
- **Android**.
