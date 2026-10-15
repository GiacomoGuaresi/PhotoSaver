# Sviluppo

## Comandi

Serve [uv](https://docs.astral.sh/uv/).

```sh
uv sync                    # crea .venv e installa le dipendenze
uv run pytest              # test
uv run ruff check .        # lint
uv run ruff format .       # formattazione
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

### Scenari da poter riprodurre

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
