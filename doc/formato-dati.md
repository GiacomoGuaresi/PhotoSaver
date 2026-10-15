# Formato dei dati sui dischi

Cosa scrive PhotoSaver su ogni disco. Le foto restano file normali nella
cartella dell'archivio, leggibili anche senza l'app.

```
<disco>/
├── .photosaver/
│   └── disk.json        identità del disco
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
