# Analisi dell'archivio esistente

> Disco di esempio: un disco esterno USB da 1,8 TB, analizzato il 2026-10-15
> **in sola lettura** (elenco file e dimensioni, più la lettura dei metadati EXIF
> di circa 120 foto prese a campione). Sul disco non è stato scritto nulla.
>
> Per privacy, nomi di persone, luoghi e cartelle sono stati sostituiti con
> esempi generici; numeri e schemi sono quelli reali.

## Numeri

| | |
|---|---|
| Filesystem | **NTFS** |
| Spazio usato | 400 GB su 1,8 TB (22%) |
| File nell'archivio foto | **60.078** in circa 280 cartelle |
| Dimensione tipica di un file | ~4,4 MB (mediana); il più grande pesa 775 MB |

| Tipo | File | Spazio |
|---|---|---|
| JPG / JPEG | 55.983 | 314,5 GB |
| MP4 | 2.935 | 66,2 GB |
| MP3 / M4A (musica) | 877 | 1,8 GB |
| Collegamenti `.lnk` di Windows | 239 | — |
| PNG, WEBP, 3GP, AVI | 44 | 0,1 GB |

Nell'archivio **non ci sono HEIC né RAW**: il telefono Samsung salva in JPG.
Ci sono però foto di una reflex, quindi i RAW potrebbero arrivare in futuro.

## Struttura

```
DISCO ESTERNO/
├── Auto/                         ← documenti PDF, non foto
├── FOTO FAMIGLIA/                ← l'archivio foto vero e proprio
│   ├── FOTO 2010 … FOTO 2026/    ← una cartella per anno
│   │   ├── <file sciolti>        ← foto senza evento (~9.000 in tutto)
│   │   └── <EVENTO> <ANNO>/      ← es. "LAGO 2021", "MARE 2022"
│   │       └── <sotto-luogo>/    ← a volte (es. viaggi di più giorni)
│   ├── FOTO <TEMA>/, …           ← cartelle a tema, fuori dagli anni
│   ├── MUSICA/                   ← musica, non foto
│   └── VIDEO 2020/, VIDEO <TEMA>/
└── manuali PDF del disco
```

Lo schema di fondo, cioè **Anno → Evento → (luogo)**, è chiaro e coerente.
Le eccezioni:

- **Manca `FOTO 2019`**: le foto del 2019 sono dentro `FOTO 2020/FOTO 2019/` (1.117 file).
- Cartelle a tema **fuori dagli anni** (cerimonie, scuola, famiglia).
- **I nomi non seguono una regola unica**: quasi tutti in MAIUSCOLO, alcuni no
  (`Spiaggia`, `Modificate`); ci sono doppi spazi (`MARE  2011`) e due
  cartelle quasi uguali (`GITA AL LAGO 2022` e `GITA LAGO 2022`).
- **Cartelle vuote**: 2, entrambe in `FOTO 2022`.

## Nomi dei file

| Schema | File | Da dove arriva | Data di scatto |
|---|---|---|---|
| `YYYYMMDD_HHMMSS` | 45.576 | fotocamera Samsung | nome + EXIF |
| `IMG-YYYYMMDD-WAnnnn` | 6.989 | WhatsApp | **solo dal nome** (WhatsApp cancella gli EXIF) |
| `IMG_YYYYMMDD_HHMMSS` | 3.159 | altri telefoni | nome + EXIF |
| `DSC…`, `HPIM…`, `P…`, ecc. | ~3.600 | fotocamere digitali vecchie | EXIF (quasi sempre) |

**GPS** (dal campione): presente nel 60% circa delle foto da telefono, assente
in quelle di WhatsApp, raro in quelle delle fotocamere. Per la mappa ci sarà
quindi una parte importante di foto senza posizione.

## Problemi trovati

### 🔴 1. Foto mai copiate: 239 collegamenti invece delle foto

Tre cartelle del 2024 contengono **collegamenti Windows (`.lnk`) invece delle foto**:

| Cartella | Collegamenti | Foto vere |
|---|---|---|
| LUOGO A 2024 | 206 | **0** |
| LUOGO B 2024 | 30 | **0** |
| LUOGO C 2024 | 3 | 125 |

Ogni collegamento punta alla **scheda SD del telefono**
(collegato via MTP). Probabilmente, trascinando i file dal telefono, Windows ha
creato collegamenti invece di copie. **Su questo disco quelle foto non ci sono**
e nell'archivio non compare nessun file con lo stesso nome.
→ Da controllare subito: sono sull'altro disco? Sono ancora sul telefono?

### 🟠 2. Un file vuoto

`FOTO 2021/MARE 2021/Spiaggia/2021MMDD_HHMMSS.jpg` pesa **0 byte**: la foto
è persa o la copia si è interrotta. Va controllato se sull'altro disco è integra.

### 🟡 3. Doppioni

- **250 file "- Copia"** (anche `- Copia - Copia`), copie fatte da Windows.
- **518 file con lo stesso nome e la stessa dimensione** in cartelle diverse
  (es. `FOTO 2020/` e `VIDEO 2020/`, oppure `MARE 2020/` e `FAMIGLIA/`).
- Spazio sprecato stimato: **1,7–3 GB**. È poco: probabilmente i doppioni
  sono voluti, una stessa foto messa in due "album".

### 🟡 4. Anno della cartella diverso dall'anno della foto

In 1.709 file l'anno nel nome è diverso da quello della cartella. Quasi tutti
sono casi normali: le foto 2019 dentro `FOTO 2020`, quelle di Capodanno, gli eventi
a cavallo tra due anni. Solo pochi sembrano errori veri, es. 116 foto del 2021
dentro `FOTO 2018`.

### ⚪ 5. Varie

- Un nome di file rovinato: `FOTO 2015/IM䁇-20150503-Wࡁ0014.jpg`, probabilmente
  da una vecchia copia con la codifica sbagliata.
- Sullo stesso disco ci sono anche file che non sono foto (PDF dell'auto, musica):
  l'app deve sapere **quale cartella è l'archivio** e lasciare stare il resto.
