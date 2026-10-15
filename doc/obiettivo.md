# PhotoSaver — Obiettivo del progetto

> Nome: **PhotoSaver**.
> Riferimento: [PrintPicker](https://github.com/GiacomoGuaresi/PrintPicker) (solo per design e stack tecnologico).

## In una frase

Una utility semplice per gestire un archivio di foto duplicato su due hard disk,
in stile RAID 1 (mirroring): ogni foto sta su entrambi i dischi.

## Il problema

Flusso attuale, ripetuto ogni tanto:

1. Scarico le foto dal cellulare.
2. Le sposto sul desktop.
3. Le organizzo in cartelle.
4. Copio le cartelle sul **disco 1**.
5. Copio le stesse cartelle sul **disco 2**.

Uso due dischi per avere una copia di riserva se il primo si rompe.

Il flusso funziona ma è **lento**: le copie si fanno a mano, un disco alla volta.
Inoltre non ho un modo semplice per sapere se i due dischi sono davvero allineati.

## Cosa deve fare

- **Caricare** cartelle di foto dall'interfaccia.
- **Sincronizzarle** su entrambi i dischi in un solo passaggio, verificando
  la copia (checksum). A copia verificata, l'app **propone di cancellare**
  la cartella originale dal desktop.
- **Destinazione**: per ogni cartella caricata l'app propone dove metterla
  nell'archivio (es. per anno, in base alle date delle foto); posso modificarla.
- **Duplicati**: se una foto che carico è già nell'archivio (stesso contenuto,
  anche in un'altra cartella), l'app avvisa e chiede se caricarla comunque.
- **Verificare** che i due dischi contengano le stesse foto.
- **Tenere traccia delle modifiche**, in particolare:
  - foto aggiunte (cosa e quando);
  - foto cancellate o spostate;
  - file corrotti su uno dei due dischi (serve un controllo del contenuto, es. checksum);
  - file o cartelle rinominati / riorganizzati.
- **Gestire modifiche fatte fuori dall'app**: se copio o tocco file sui dischi
  senza passare dall'app, al check successivo l'app deve accorgersene e
  riallineare i due dischi, o almeno mostrarmi le differenze e chiedermi cosa fare.

## Gestione delle differenze

Quando il check trova una differenza tra i due dischi:

- l'app **chiede sempre** conferma prima di toccare i file;
- se la soluzione è ovvia (es. foto mancante su un disco, o corrotta su un disco
  e integra sull'altro) l'azione è **già proposta / precompilata** e basta confermare;
- per i casi ambigui (es. stesso file diverso su entrambi) decido io;
- **cancellazioni volute**: se una foto è stata cancellata da un disco, al check
  l'app propone di cancellarla anche dall'altro (oppure di ripristinarla), e io confermo.

### Cestino

Le cancellazioni confermate non sono definitive: i file finiscono in un
**cestino dell'app** (`.photosaver/cestino/` su entrambi i dischi), da cui si
possono ripristinare. Il cestino si svuota:

- **a tempo**: i file più vecchi di N giorni (configurabile, es. 30) vengono eliminati;
- **a mano**, quando decido io.

Le due modalità possono convivere.

## Quando parte il check completo

- **A mano**, quando lo lancio io.
- **Promemoria** dopo X tempo dall'ultimo check (X configurabile).
- **Quando l'app nota incongruenze** durante l'uso normale (es. navigando
  l'archivio), suggerisce di fare il check.

## Visualizzatore

L'app fa anche da **visualizzatore** dell'archivio: posso sfogliare le foto
dei dischi direttamente dall'app.

- **Sfoglia cartelle**: albero delle cartelle con miniature.
- **Anteprima grande**: foto e video a schermo intero.
- **Stato sync per file/cartella**: vedo se ogni elemento è OK su entrambi i dischi.
- **Ricerca e filtri**: per data, tipo, nome, ecc.
- **Mappa**: posizione delle foto dai dati GPS (EXIF) su una mappa, con i pin
  vicini raggruppati in cluster (es. "120 foto qui") che si separano zoomando.

Le **miniature** vengono salvate sui dischi (`.photosaver/`, circa 2 GB ogni
60.000 foto), così sono già pronte su qualsiasi computer.

Per usare il visualizzatore **basta un disco collegato** (uno qualsiasi dei due).
Sincronizzazione e check completo invece richiedono entrambi.

## Vincoli

- Per sincronizzare e verificare, **entrambi i dischi devono essere collegati
  contemporaneamente**. Oggi non lo faccio, ma è un vincolo accettabile.
- **Piattaforme**: app desktop multipiattaforma. Priorità: **Linux e Windows**;
  **macOS è un obiettivo secondario** (firma Apple e notarizzazione rimandate).
- **Dimensioni archivio**: oggi tra 100 GB e 1 TB. Il check completo (checksum)
  richiederà tempo: va mostrato l'avanzamento e deve poter riprendere se interrotto.
- **Riconoscimento dischi**: l'app riconosce da sola i suoi dischi appena collegati
  (grazie a un file identificativo nella cartella dell'app sul disco); posso anche
  indicare a mano il percorso di un archivio.
- **Lingua**: interfaccia in italiano e inglese, scelta dalla lingua del sistema (come PrintPicker).
- **Più computer**: posso collegare i dischi a PC diversi. Indice, checksum e
  storico delle modifiche vanno quindi salvati **sui dischi stessi** (es. una
  cartella nascosta dell'app), così viaggiano con loro.
- **Tipi di file**: foto (JPG, HEIC), video (MP4, MOV), RAW da fotocamera.
  **Tutto il resto viene ignorato**: musica, PDF e documenti non vengono copiati,
  verificati né mostrati. Al caricamento l'app dice quanti file ha saltato,
  così non si perde nulla senza saperlo (es. la musica dell'archivio vecchio).
- **Punto di partenza**: l'app parte da cartelle già organizzate sul desktop.
  Scaricare dal telefono e organizzare le foto restano fuori dall'app.

## Inizializzazione del disco

I dischi usano **exFAT**, leggibile e scrivibile da Windows, macOS e Linux.
L'app ha una procedura guidata di **inizializzazione**:

1. sceglie il disco e chiede una conferma esplicita, perché il disco viene cancellato;
2. lo formatta in exFAT;
3. crea la struttura di base: cartella archivio e cartella dati dell'app
   (`.photosaver/` con identificativo del disco e indice vuoto);
4. lo associa all'archivio come primo o secondo disco.

## Primo avvio: archivio esistente

Si parte con **due dischi nuovi**, inizializzati dall'app. Non si migrano e
non si adottano i vecchi dischi NTFS, che restano come copia di riserva.

L'archivio esistente (~400 GB, vedi [analisi-disco.md](analisi-disco.md)) viene
**ricaricato** sui dischi nuovi passando dall'app, come un normale caricamento,
ma di un intero albero di cartelle. Il caricamento deve quindi reggere anche:

- un'intera struttura **Anno → Evento** in una volta, mantenendola così com'è;
- volumi grandi (ore di copia), con avanzamento visibile e ripresa se si interrompe.

**Fuori scope**: pulizia e riorganizzazione dei vecchi dati (doppioni, nomi,
cartelle nell'anno sbagliato, `.lnk`, file da 0 byte). L'app copia quello che
trova.

## Prima versione (MVP)

1. **Carica + sync + verifica**: copia delle cartelle su entrambi i dischi, con checksum.
2. **Check e riallineamento**: confronto dei dischi, elenco differenze, azioni proposte.
3. **Visualizzatore base**: sfoglia cartelle, miniature, anteprima grande, stato sync.
4. **Inizializzazione e sostituzione dei dischi**: creare l'archivio su due dischi
   nuovi e, se un disco si rompe, ricostruirlo su un disco nuovo dal disco sano.

Versione successiva: **mappa GPS con cluster** e **ricerca/filtri**.

## Futuro (fuori scope per ora)

- App Android che lavori direttamente dal telefono.
- Terza copia (o più): un disco in più, ad esempio tenuto fuori casa. I dati sono già pensati per N dischi.

## Note

- È un mirroring gestito dall'applicazione, non un RAID hardware o di sistema:
  i dischi restano normali dischi, leggibili anche senza l'app. ✅ confermato
