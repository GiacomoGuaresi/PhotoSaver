# PhotoSaver — Stack (proposta)

> Bozza da discutere. Riferimento: lo stack di PrintPicker.

## Da PrintPicker

PrintPicker usa **Python + Qt (PySide6)**, impacchettato con **PyInstaller**
in eseguibili per macOS, Windows e Linux. Per le immagini usa Pillow,
pillow-heif (HEIC) e rawpy (RAW).

## Va bene per PhotoSaver?

Sì, per quasi tutto:

| Esigenza | Come si copre |
|---|---|
| App desktop macOS / Windows / Linux | PySide6 + PyInstaller, come PrintPicker |
| Copia con verifica, checksum | Libreria standard di Python: **SHA-256** (`hashlib`), accelerato in hardware sulle CPU recenti e verificabile senza l'app (`sha256sum`, `certutil`); thread in background |
| Indice e storico sui dischi | SQLite in una cartella nascosta su ogni disco (es. `.photosaver/`) |
| Miniature JPG / HEIC / RAW | Pillow, pillow-heif, rawpy (già provati in PrintPicker) |
| Video (miniature, anteprima) | Qt Multimedia per la riproduzione; un fotogramma per la miniatura |
| Dati GPS e date | EXIF letti con Pillow |
| Design | Tema scuro, token colore, font Inter, icone Lucide, come in PrintPicker |

## Punto da valutare: la mappa

La mappa con i cluster è l'unica parte che PrintPicker non ha. Due strade:

- **Qt WebEngine + Leaflet** (con il plugin markercluster): è la soluzione più
  matura per i cluster, ma aggiunge circa 100 MB agli eseguibili.
- **Qt Location (QML) con le mappe OpenStreetMap**: l'app resta più leggera,
  ma i cluster vanno scritti a mano.

In entrambi i casi servono le tile della mappa da internet, quindi la mappa
funziona solo online.

✅ **Scelta: Qt WebEngine + Leaflet + markercluster.** Accettiamo eseguibili più pesanti in cambio di cluster già pronti e collaudati.

## Alternativa considerata

**Tauri / Electron + web UI** semplificherebbero la mappa, ma il lavoro fatto
su PrintPicker (tema, gestione di HEIC e RAW, packaging) non si potrebbe riusare.
