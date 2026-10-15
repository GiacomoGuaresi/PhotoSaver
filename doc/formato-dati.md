# Formato dei dati sui dischi

Cosa scrive PhotoSaver su ogni disco. Le foto restano file normali nella
cartella dell'archivio, leggibili anche senza l'app.

```
<disco>/
├── .photosaver/
│   ├── disk.json        identità del disco
│   ├── index.sqlite     indice dell'archivio
│   └── cestino/         file cancellati o sostituiti dall'app
└── <cartella archivio>/ le foto (es. Foto/)
```

## `disk.json`

```json
{
  "disk_id": "3f2a…",
  "archive_id": "9c41…",
  "label": "A",
  "archive_dir": "Foto",
  "created": "2026-10-15T19:10:00+00:00",
  "format": 1
}
```

| Campo | Significato |
|---|---|
| `disk_id` | identificativo unico del disco (UUID) |
| `archive_id` | identificativo dell'archivio, uguale su tutti i suoi dischi |
| `label` | nome mostrato nell'app ("A", "B") |
| `archive_dir` | nome della cartella con le foto, nella radice del disco |
| `created` | data di inizializzazione (UTC) |
| `format` | versione del formato: un'app più vecchia rifiuta un disco più nuovo |

Il file si scrive in modo atomico (file temporaneo → `fsync` → rinomina), così
un'interruzione lascia il file vecchio o quello nuovo, mai uno a metà.
Inizializzare una cartella che è già un disco viene rifiutato.

## `index.sqlite`

Database SQLite, **uguale su tutti i dischi** dell'archivio. Descrive cosa
l'archivio deve contenere e com'è ogni copia su ogni disco.

| Tabella | Contenuto |
|---|---|
| `meta` | `archive_id`, `hash_algorithm` (`sha256`), `revision`, `created`, `full_check_run` (check completo in corso: inizio e dischi), `last_full_check:<id disco>` |
| `disks` | un record per disco: id, nome, data di aggiunta |
| `files` | un record per file: percorso relativo alla cartella archivio (con `/`), dimensione, data di modifica (ns), hash, data di aggiunta |
| `copies` | stato di ogni file su ogni disco (`ok`, `missing`, `corrupt`, `modified`) e data dell'ultima verifica del contenuto |
| `events` | storico delle operazioni: data, tipo, percorso, disco, dettagli JSON |
| `trash` | file nel cestino di ogni disco: percorso originale, posizione nel cestino, dimensione, data, hash, motivo (`deleted`, `replaced`) |
| `journal` | operazioni in corso: tipo e parametri JSON; una riga rimasta indica un'operazione interrotta |
| `known_issues` | differenze segnate come note: percorso, disco, tipo, hash visto (se il file cambia ancora, torna a essere segnalato) |

- I dischi sono **righe, non colonne**: una terza copia non cambia lo schema.
- **Versione dello schema** in `PRAGMA user_version`; all'apertura l'app applica
  le migrazioni mancanti, e rifiuta un indice scritto da un'app più nuova.
- Ogni scrittura avviene in una **transazione**, che incrementa `revision`.
  Confrontando le revisioni si capisce quale disco ha l'indice più recente dopo
  un'interruzione.
- Niente WAL (`journal_mode = DELETE`, `synchronous = FULL`): il WAL usa memoria
  condivisa, poco affidabile su dischi rimovibili exFAT.
- La copia dell'indice su un altro disco usa l'API di backup di SQLite e una
  rinomina atomica.

## File `.photosaver-partial`

Durante una copia, il file viene scritto come `.<nome>.photosaver-partial` nella
cartella di destinazione. Prende il nome definitivo solo dopo:

1. scrittura forzata sul disco (`fsync`);
2. rilettura dal disco (su Linux scartando la cache) e confronto dell'hash con
   quello della sorgente;
3. impostazione della data di modifica originale.

Un file `.photosaver-partial` rimasto sul disco indica una copia interrotta:
non fa parte dell'archivio e la copia successiva lo sostituisce. La sorgente si
legge una volta sola anche quando le destinazioni sono due (dischi A e B), e un
file esistente non viene mai sovrascritto.

## Cestino

Ogni disco ha il suo cestino, `.photosaver/cestino/`: spostarci un file è una
semplice rinomina sullo stesso disco, quindi è immediato.

```
.photosaver/cestino/20261015T190000-1a2b3c/FOTO 2026/MARE 2026/a.jpg
                    └ data e lotto ──────┘└ percorso originale ───────┘
```

- **Ripristina**: il file torna al suo posto (mai sopra un file esistente); se
  l'archivio non lo elencava più, viene rimesso nell'indice e gli altri dischi
  lo riceveranno al check successivo.
- **Svuota**: a mano, oppure solo i file più vecchi di N giorni (30 di default).
  I file sui dischi non collegati restano finché il disco non viene collegato.

## Operazioni interrotte

Se l'app si chiude o un disco si stacca a metà di un'operazione:

- **Indici**: le operazioni scrivono sull'indice con la revisione più alta e lo
  copiano sugli altri dischi a intervalli e alla fine. All'apertura vince
  l'indice più recente, e gli altri vengono riallineati.
- **Azioni di riparazione** (ripara, copia, cancella, sposta…): prima di toccare
  i file, l'azione viene scritta nella tabella `journal` dell'indice. Se resta
  una riga, l'app la segnala e la completa: ogni azione si può rieseguire senza
  danni, perché riconosce quello che era già stato fatto (file già corretto,
  già spostato, già nel cestino).
- **Caricamento**: rifare il caricamento riprende da dove si era fermato. Un
  file copiato su un disco ma non ancora registrato viene riconosciuto (dal
  caricamento successivo, o dal check come "aggiunto a mano", con l'azione
  "aggiungi" proposta).
- **Copie a metà**: restano come `.photosaver-partial`, ignorati e sostituiti
  dalla copia successiva.
