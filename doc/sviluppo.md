# Sviluppo

## Comandi

Serve [uv](https://docs.astral.sh/uv/).

```sh
uv sync                    # crea .venv e installa le dipendenze
uv run pytest              # test
uv run ruff check .        # lint
uv run ruff format .       # formattazione
```

### Avviare l'app

```sh
uv run python scripts/dev_disks.py setup
uv run python -m photosaver --disks dev-disks/disk-a dev-disks/disk-b
```

`--disks` (o la variabile `PHOTOSAVER_DISKS`, percorsi separati da `:`) dice
dove cercare i dischi: il riconoscimento dei volumi veri arriva con M5. L'app
li ricontrolla ogni 1,5 s, quindi per **scollegare un disco** basta rinominare
la cartella (`mv dev-disks/disk-b dev-disks/disk-b.off`) e per ricollegarlo
rimetterle il nome. Con `--disks` su una cartella vuota si prova il "disco nuovo".

### Traduzioni

I testi dell'interfaccia sono in inglese nel codice e tradotti in
`scripts/translations_it.py`. Dopo aver cambiato dei testi:

```sh
uv run python scripts/update_translations.py   # estrae, traduce, compila; segnala i mancanti
```

### CLI di debug

Per provare il motore senza interfaccia, sui dischi simulati:

```sh
uv run python -m photosaver.cli init dev-disks/disk-a --label A
uv run python -m photosaver.cli init dev-disks/disk-b --label B --join dev-disks/disk-a
uv run python -m photosaver.cli status dev-disks/disk-a
uv run python -m photosaver.cli scan dev-disks/desktop
uv run python -m photosaver.cli upload dev-disks/desktop/"MARE 2026" \
    --disks dev-disks/disk-a dev-disks/disk-b [--apply] [--delete-sources]
```

## Dischi simulati

Nelle prime fasi i "dischi" sono **cartelle locali non committate**. Più avanti
si passerà a chiavette e dischi USB veri.

```
PhotoSaver/
└── dev-disks/              ← in .gitignore
    ├── disk-a/             ← simula il disco 1
    ├── disk-b/             ← simula il disco 2
    └── desktop/            ← simula le cartelle da caricare (sorgente)
```

Conseguenze sul codice:

- Per l'app **un disco è semplicemente una cartella radice**: nessuna logica deve
  dipendere da punti di montaggio, etichette di volume o tipo di filesystem.
  Questi dettagli stanno in un modulo separato, che con le cartelle simulate
  restituisce valori finti.
- **Inizializzazione**: su una cartella simulata si salta la formattazione e si
  crea solo la struttura (`.photosaver/`, cartella archivio). La formattazione
  vera è un passaggio a parte, da attivare solo sui dischi reali.
- **Collegare / scollegare un disco**: si simula rinominando o spostando la
  cartella (o con un'opzione di sviluppo), così si provano i casi "un disco solo"
  e "disco mancante".

Si creano con:

```sh
uv run python scripts/dev_disks.py create   # ricrea dev-disks/ da zero (--seed, --scale)
uv run python scripts/dev_disks.py setup    # + archivio su disk-a e disk-b con il vecchio archivio
uv run python scripts/dev_disks.py break all          # tutti gli scenari di guasto
uv run python scripts/dev_disks.py break corrupt move # solo alcuni
uv run python scripts/dev_disks.py reset    # cancella tutto
```

`desktop/` contiene due eventi nuovi (`MARE 2026`, `LAGO 2026`) e un archivio
vecchio da ricaricare (`vecchio-archivio/FOTO FAMIGLIA/FOTO 2024…2025`), con
foto Samsung, Pixel, WhatsApp (senza EXIF) e reflex, qualche video e file da
ignorare. Le foto sono JPEG veri con data, fotocamera e GPS controllati; i video
sono segnaposto non riproducibili. Il generatore è in
`src/photosaver/devtools/` ed è usato anche dai test.

`reset` cancella solo una cartella che contiene il file `.dev-disks`, creato dal
generatore: non può cancellare un disco vero per errore.

### Scenari da poter riprodurre

Disponibili con `break` (vedi `SCENARIOS` in `src/photosaver/devtools/dev_disks.py`)
e provati end-to-end in `tests/test_scenarios.py`: l'archivio viene rotto in
tutti i modi, controllato e sistemato, e alla fine nessuna foto deve mancare
(nell'archivio o nel cestino).

| Scenario | Cosa fa |
|---|---|
| `corrupt` | cambia un byte di una foto sul disco B, stessa dimensione e data |
| `truncate` | porta a 0 byte una foto sul disco A, stessa data |
| `delete` | cancella una foto dal disco A |
| `move` | rinomina una cartella evento sul disco B |
| `edit` | modifica una foto sul disco A (contenuto e data nuovi) |
| `add` | aggiunge a mano una foto solo sul disco A |
| `partial` | lascia un file `.photosaver-partial` a metà sul disco B |
| `desktop` | mette tra le foto da caricare una foto da 0 byte e 3 collegamenti `.lnk` |

Idee iniziali:

Piccoli script di sviluppo (es. `scripts/dev_disks.py`) per creare e "rompere"
i dischi simulati:

- archivio di partenza con foto di prova **generate dallo script** (immagini
  finte con EXIF, GPS e date controllati, nomi nello stile Samsung/WhatsApp,
  qualche video e file da ignorare). Sono riproducibili e senza dati personali:
  nessuna foto vera nel repository né nei test;
- **corruzione silenziosa**: cambiare un byte di un file mantenendo la sua data di modifica;
- file cancellato, spostato o rinominato su un solo disco;
- file aggiunto "a mano" senza passare dall'app;
- copia interrotta (file `.photosaver-partial` rimasto a metà);
- file da 0 byte, collegamenti `.lnk`.

### Cosa le cartelle locali non simulano

Il disco di sviluppo è ext4, non exFAT. Restano da provare sui dischi veri, o
con un'**immagine exFAT montata in loop** (es. un file da 1 GB) come passaggio
intermedio:

- nomi **senza distinzione tra maiuscole e minuscole** (`Foto.jpg` = `foto.jpg`);
- precisione e fuso orario delle **date dei file**;
- assenza dei permessi Unix (avvio dell'app dal disco);
- velocità reale di un disco USB meccanico (prestazioni del check completo);
- disco staccato durante una copia.
