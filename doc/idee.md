# Idee e proposte (da discutere)

> Spunti emersi dall'analisi del disco ([analisi-disco.md](analisi-disco.md))
> e da qualche ricerca. Niente di deciso: ogni punto chiude con una domanda aperta.

## 1. Cosa esiste già

| Strumento | Cosa fa | Cosa manca rispetto a PhotoSaver |
|---|---|---|
| FreeFileSync | Mirror tra cartelle, confronto per contenuto | Nessuno storico, nessun controllo della corruzione nel tempo, niente visualizzatore |
| [bitrot](https://github.com/ambv/bitrot), [rotrep](https://pkg.go.dev/github.com/ripienaar/rotrep) | Checksum in SQLite, scoprono i file corrotti | Solo da riga di comando, un disco alla volta, non riparano |
| SnapRAID | Parità e controllo periodico dei dati | Pensato per server e NAS, complesso |
| digiKam | Visualizzatore, mappa, database | Non gestisce il mirror tra due dischi |
| Immich / PhotoPrism | Galleria completa con mappa | Richiedono un server sempre acceso |

**Lo spazio libero**: nessuno di questi unisce *mirror + verifica + riparazione +
visualizzatore* in un'app desktop semplice. È proprio quello che fa PhotoSaver.

## 2. Come capire se un file è corrotto

L'idea, presa da bitrot, è confrontare il checksum con la data di modifica:

| Contenuto (hash) | Data di modifica | Significato |
|---|---|---|
| uguale | uguale | tutto OK |
| diverso | **uguale** | **corruzione silenziosa** (bit rot) |
| diverso | diversa | modifica voluta (es. foto ritoccata) |

Con due dischi la riparazione è semplice: si confronta con l'hash salvato,
la copia che corrisponde è quella buona e si ricopia sull'altro disco.
È il caso "ovvio" con l'azione precompilata.

## 3. Due tipi di check

- **Check rapido** (pochi secondi): confronta solo elenco file, dimensioni e date.
  Parte ogni volta che si collegano i dischi. Trova file mancanti, nuovi,
  spostati, collegamenti `.lnk` e file vuoti.
- **Check completo** (rilegge tutto e calcola gli hash): su un disco USB
  da ~100–150 MB/s, 400 GB richiedono **circa 45–70 minuti per disco**. Se i
  dischi sono su porte USB separate si leggono in parallelo. Deve poter
  riprendere se interrotto.
- **Controllo a rotazione** (opzionale): a ogni collegamento ricontrolla solo
  una parte dell'archivio (es. 10%), così in poche settimane tutto viene
  verificato senza mai aspettare un'ora.

## 4. Dati dell'app sui dischi

Ogni disco ha una cartella nascosta, es. `.photosaver/`, che contiene:

- `disk.json`: identificativo del disco, nome ("Disco A"), identificativo
  dell'archivio comune ai due dischi e percorso della cartella archivio
  (es. `FOTO FAMIGLIA/`);
- `index.sqlite`: per ogni file percorso, dimensione, data, hash, data
  dell'ultimo check, più lo **storico degli eventi** (aggiunto, spostato,
  cancellato, riparato…);
- le miniature, se le teniamo sul disco (vedi punto 9).

I due database sono uguali. Un numero di versione indica quale dei due è
più recente, utile se un'operazione si interrompe a metà.

## 5. Copiare in sicurezza

Per ogni file:

1. Copia con un nome temporaneo (`.nomefile.photosaver-partial`).
2. Scrittura forzata su disco (flush).
3. **Rilettura e confronto dell'hash** con quello del file originale.
4. Rinomina al nome definitivo, conservando la data di modifica originale.

Così un'interruzione non lascia mai un file "a metà" con il nome buono:
il file da 0 byte trovato nell'analisi è esattamente il caso da evitare.

## 6. Spostamenti e rinomine

Siccome l'app conosce l'hash di ogni file, quando trova "file sparito qui,
file nuovo là con lo stesso hash" capisce che si tratta di uno **spostamento**
e propone di ripeterlo sull'altro disco, senza ricopiare GB di dati.
È importante perché la struttura delle cartelle potrebbe cambiare (punto 8).

## 7. 🔴 Il problema del filesystem: NTFS e macOS

Il disco è **NTFS**. Linux e Windows lo leggono e scrivono senza problemi;
**macOS lo legge ma non ci scrive** senza driver di terze parti (Paragon,
Tuxera, ntfs-3g). Opzioni:

| Opzione | Pro | Contro |
|---|---|---|
| **A. Tenere NTFS**, su macOS solo visualizzatore + check | Nessuna migrazione, filesystem robusto (con journal) | Su Mac non si possono caricare foto |
| B. Passare a **exFAT** | Lettura e scrittura ovunque | Senza journal: più fragile se si stacca il disco durante una scrittura. Richiede di riformattare (migrazione da un disco all'altro) |
| C. NTFS + driver su Mac | Tutto funziona ovunque | Dipende da software esterno, spesso a pagamento |

✅ **Scelta: exFAT** (opzione B), così i dischi sono leggibili e scrivibili
da tutti i sistemi senza driver. Vedi "Inizializzazione del disco" in
[obiettivo.md](obiettivo.md).

Conseguenze da gestire:

- **Assenza di journal**: la copia sicura (punto 5) e il controllo all'avvio
  ("l'ultima operazione si era interrotta?") diventano ancora più importanti.
  Va ricordato di espellere il disco correttamente.
- **Date dei file**: exFAT le salva con precisione e fuso orario diversi da
  NTFS, quindi il confronto delle date deve avere una tolleranza di qualche secondo.
- **Formattare richiede permessi di amministratore** su tutti i sistemi
  (`mkfs.exfat` su Linux, `diskutil` su macOS, `Format-Volume` su Windows).
- ✅ **Nessuna migrazione**: si usano due dischi nuovi; l'archivio vecchio
  viene ricaricato dall'app e i dischi NTFS restano come copia di riserva.

## 8. Struttura delle cartelle

> ✅ **Deciso: la pulizia e la normalizzazione dei vecchi dati sono fuori scope.**
> L'archivio vecchio viene ricaricato così com'è. Le proposte qui sotto restano
> solo come riferimento.

La struttura attuale **Anno → Evento → (luogo)** funziona e la terrei. Proposte:

- **Archivio = una cartella precisa** sul disco (oggi `FOTO FAMIGLIA/`).
  L'app ignora tutto il resto (`Auto/`, manuali PDF).
- **Normalizzazione proposta, mai imposta**: l'app segnala
  - `FOTO 2019` dentro `FOTO 2020` → spostarla al primo livello?
  - doppi spazi e cartelle quasi uguali (`GITA AL LAGO` / `GITA LAGO`);
  - foto con un anno diverso da quello della cartella (escludendo Capodanno);
  - cartelle vuote, `.lnk`, file da 0 byte, copie "- Copia".
- **Formato del nome dell'evento**: oggi `NOME EVENTO ANNO`. Per l'ordine
  cronologico dentro l'anno si potrebbe usare `MM - NOME EVENTO` o `YYYY-MM NOME`,
  ma è un cambiamento grosso: **domanda aperta**.
- **Cartelle a tema** (cerimonie, scuola, musica): lasciarle così, oppure un
  livello `ALTRO/`?
- **Cosa fa parte dell'archivio**: la musica (`MUSICA`) va protetta anche lei,
  ma solo foto e video vanno mostrati nel visualizzatore? (proposta: sì)

## 9. Visualizzatore

- **Data dello scatto**, in ordine: EXIF → data nel nome del file (serve per
  le ~7.000 foto di WhatsApp, che non hanno EXIF) → data di modifica del file.
- **Mappa**: solo il ~60% delle foto da telefono ha il GPS. Idea per dopo:
  assegnare una posizione a un'intera cartella evento ("LAGO 2021" → il lago),
  così compaiono sulla mappa anche le foto senza GPS.
- **Miniature**: 60.000 miniature da ~30 KB fanno circa 2 GB. Salvarle sul
  disco (in `.photosaver/`) fa sì che siano già pronte su ogni computer; la
  prima generazione richiede tempo, poi è immediata.

## 10. Sicurezza in più

- **Le cancellazioni si propagano**: con il mirror, un errore su un disco
  finisce anche sull'altro. Anche dopo la conferma, consiglio di spostare i file
  in un **cestino dell'app** (`.photosaver/cestino/`, svuotato dopo N giorni)
  invece di cancellarli subito. Costa poco e salva da un clic sbagliato.
- **Regola 3-2-1**: due dischi nella stessa casa proteggono dalla rottura di
  un disco, ma non da furto, incendio o un picco di corrente con entrambi
  collegati. Per il futuro: tenere un disco altrove, o aggiungere una terza
  copia (cloud o NAS).
- **Segnalare l'età dei dischi**: leggere lo stato di salute (SMART) è difficile
  da fare su tutte le piattaforme, ma l'app può almeno tenere traccia degli
  errori di lettura e avvisare se aumentano.

## 11. Nome dell'app ✅

"PhotoGuard" era già usato da altri prodotti. ✅ **Scelto: PhotoSaver.**

## 12. App portatile, salvata sui dischi

L'idea è che ogni disco contenga l'app e si possa avviare da lì su qualsiasi computer.

```
DISCO/
├── PhotoSaver/
│   ├── PhotoSaver-Windows/     (PyInstaller, cartella con .exe)
│   ├── PhotoSaver-Linux/       (PyInstaller, cartella o AppImage)
│   └── PhotoSaver.app          (macOS, universal2: Intel + Apple Silicon)
├── .photosaver/
└── <archivio>/
```

**Fattibilità: media.** Il lavoro è soprattutto di impacchettamento, non di
architettura: le build PyInstaller per i 3 sistemi esistono già in PrintPicker.
Spazio occupato: circa 1 GB per le tre versioni con WebEngine, poco su un disco da 2 TB.

| Sistema | Difficoltà | Note |
|---|---|---|
| Windows | 🟢 bassa | Parte con doppio clic. L'autorun dai dischi USB è disattivato da Windows 7, quindi niente avvio automatico. SmartScreen avvisa se l'eseguibile non è firmato |
| Linux | 🟢/🟡 | exFAT non ha i permessi Unix, ma di solito viene montato con i file eseguibili (senza `noexec`) e quindi funziona. Va compilato su una distribuzione vecchia per compatibilità con glibc |
| macOS | 🔴 alta | Gatekeeper blocca le app non firmate: serve firma + notarizzazione (Apple Developer, 99 $/anno), altrimenti si apre col tasto destro → Apri, o con `xattr`. Su exFAT macOS salva i metadati nei file `._*` (da ignorare nel check) |

Vantaggi:

- **La versione dell'app viaggia con i dati**: niente rischio che un PC con
  un'app vecchia apra un indice aggiornato da una versione più nuova.
- **L'app si copia da sola**: la cartella `PhotoSaver/` è sincronizzata tra i
  due dischi come il resto, quindi se un disco si rompe l'altro ha sia i dati
  sia il programma.
- Nessuna installazione sui computer.

Attenzioni:

- **Aggiornamenti**: l'app non può sostituire sé stessa mentre è in esecuzione.
  Serve un piccolo passaggio "scarica la nuova versione → riavvia → sostituisci",
  da ripetere su entrambi i dischi.
- **Avvio più lento** da un disco USB meccanico (qualche secondo): meglio la
  modalità *onedir* di PyInstaller rispetto a *onefile*, che a ogni avvio
  estrae tutto in una cartella temporanea.
- **Compatibilità con l'installazione classica**: si può offrire anche quella;
  in quel caso l'app installata e quella sul disco devono accordarsi sulla
  versione del formato dell'indice.

## Domande da discutere al rientro

1. ✅ Le **239 foto mancanti** (collegamenti `.lnk`) e il file da 0 byte: **probabilmente perse, già noto.**
   → L'app deve permettere di **segnare un problema come "noto / accettato"**,
   così non viene riproposto a ogni check (resta comunque nello storico).
2. ✅ **Filesystem**: exFAT su dischi nuovi, inizializzati dall'app (punto 7).
3. ✅ Normalizzare la struttura: **fuori scope**, i vecchi dati si ricaricano così come sono.
4. ✅ Musica e PDF: **no**, l'app gestisce solo foto e video; gli altri file sono ignorati.
5. ✅ Cestino dell'app: **sì**, con svuotamento a tempo e/o a mano.
6. ✅ Miniature: **sui dischi**, in `.photosaver/` su entrambi, così sono pronte su ogni computer.
