# Flussi e schermate (bozza)

> Proposta da discutere. I punti con _(?)_ sono aperti.

## Concetti

- **Archivio**: l'insieme delle foto protette. Ha un identificativo e vive su
  **due dischi** (A e B) con lo stesso contenuto. Interfaccia e flussi
  gestiscono 2 dischi, ma indice e codice sono pensati per **N dischi**, così
  in futuro si può aggiungere una terza copia (es. tenuta fuori casa) senza
  rifare tutto.
- **Disco**: una cartella radice (un disco vero o una cartella simulata in
  sviluppo) con dentro `.photosaver/` e la cartella dell'archivio.
- **Indice**: il database in `.photosaver/` con un record per ogni file
  (percorso, dimensione, data, hash), lo storico e i problemi noti. È uguale
  su A e B.

## Principi di UX: "granny software"

L'app deve poterla usare chi sa usare pochissimo il computer. Ogni scelta di
interfaccia si misura su questo.

- **Guidata, passo per passo.** Ogni schermata dice tre cose: *dove sei*,
  *cosa devi fare adesso*, *cosa succede dopo*. Una sola domanda per volta.
- **Un pulsante principale** per schermata, grande e ben visibile. Le scelte
  secondarie sono più piccole e meno evidenti.
- **Niente tecnicismi** nei testi. L'interfaccia non mostra mai parole come
  hash, indice, exFAT, sincronizzazione, mirror, `.photosaver`, percorsi di
  file, codici di errore. Glossario:

  | Nel codice / nei doc | Nell'interfaccia |
  |---|---|
  | Archivio | Le tue foto |
  | Disco A / Disco B | Disco 1 / Disco 2 _(?) con etichetta adesiva colorata sul disco vero_ |
  | Check rapido / completo | Controllo veloce / Controllo approfondito |
  | Caricamento | Aggiungere foto |
  | Corrotto, mancante, divergenze | "Una foto si è rovinata", "Una foto manca sul Disco 2" |
  | Formattare / inizializzare | Preparare il disco |

- **Spiegare con le immagini**: illustrazioni semplici (collegare il cavo,
  quale disco, dove guardare) accanto ai testi.
- **Rassicurare.** Lo stato normale si dice in chiaro: "Le tue foto sono al
  sicuro su entrambi i dischi ✓". Le operazioni lunghe dicono quanto manca e
  che si può aspettare tranquillamente.
- **Errori spiegati come a una persona**: cosa è successo, se le foto sono a
  rischio (quasi mai) e cosa fare, con un pulsante che lo fa.
- **Difficile sbagliare.** Le azioni che cancellano qualcosa chiedono una
  conferma chiara e, quando si può, si annullano (cestino). L'app non lascia
  mai fare un'operazione pericolosa per distrazione.
- **Leggibile**: testi grandi, contrasto alto, aree cliccabili ampie.
- **L'app fa da sola** tutto ciò che non serve chiedere (controllo veloce
  all'avvio, destinazione delle foto, doppioni), e chiede solo le decisioni
  vere.
- **Si chiude in modo guidato**: alla fine l'app dice quando si possono
  scollegare i dischi in sicurezza (vedi §1).

## Finestra principale

```
┌───────────────┬──────────────────────────────────────────────┐
│  PhotoSaver   │                                              │
│               │                                              │
│  ▣ Archivio   │         contenuto della sezione scelta       │
│  ⇪ Carica     │                                              │
│  ✓ Check   ②  │                                              │
│  ⟲ Storico    │                                              │
│  🗑 Cestino    │                                              │
│               │                                              │
├───────────────┴──────────────────────────────────────────────┤
│ ● Disco A  collegato  1,2 TB liberi   ● Disco B  non collegato │
└──────────────────────────────────────────────────────────────┘
```

- **Barra laterale** con le sezioni; il numero accanto a "Check" indica i
  problemi da risolvere.
- **Barra in basso**, sempre visibile, con lo stato dei due dischi. Molte
  funzioni dipendono da quali dischi sono collegati.

_(?) Con i principi "granny software" la barra laterale potrebbe essere
troppo da "programma per esperti". Alternativa: una **home** con pochi
pulsanti grandi ("Aggiungi foto", "Guarda le foto", "Controlla i dischi",
"Ho finito") e ogni funzione come procedura a passi con "Indietro" /
"Avanti". Storico e Cestino finirebbero in un menu secondario._

## 1. Avvio e riconoscimento dei dischi

All'avvio, e ogni volta che si collega un disco, l'app cerca le cartelle
`.photosaver/` sui volumi collegati (in sviluppo: nei percorsi configurati).

### La prima schermata: "Collega i dischi"

L'app si apre **sempre** chiedendo di collegare i dischi, finché non li trova.
Non c'è niente da cliccare: appena un disco viene collegato, la schermata si
aggiorna da sola.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              Collega i due dischi delle foto                 │
│                                                              │
│      [illustrazione: disco → cavo → computer]                │
│                                                              │
│      Prendi i due dischi con l'etichetta PhotoSaver e        │
│      collegali con il loro cavo alle prese USB del computer. │
│                                                              │
│        ✓ Disco 1   trovato                                   │
│        ◌ Disco 2   in attesa…                                │
│                                                              │
│      Ho un solo disco con me ›          È la prima volta? ›  │
└──────────────────────────────────────────────────────────────┘
```

- Mentre aspetta, l'app mostra che sta "ascoltando" (animazione leggera),
  così è chiaro che non è bloccata.
- Quando entrambi i dischi sono collegati: "Perfetto, ho trovato entrambi i
  dischi" → parte da solo il **controllo veloce** ("Sto controllando che le
  foto siano tutte a posto…", pochi secondi) → schermata principale con
  "Le tue foto sono al sicuro ✓".
- Se dopo un po' non trova niente, compare un aiuto: "Non vedo nessun disco.
  Controlla che il cavo sia ben inserito; se il disco ha una lucina, deve
  essere accesa." _(?) quanto aspettare: 30 s?_
- **Ho un solo disco con me**: spiega che si possono *guardare* le foto ma non
  aggiungerne né controllarle, e perché ("servono tutti e due, così le foto
  restano uguali su entrambi"). Poi apre l'app in sola lettura.
- **È la prima volta?** → procedura "Prepara i dischi" (§2).

### Casi particolari, detti in modo semplice

| Situazione | Cosa vede l'utente |
|---|---|
| Un solo disco dell'archivio | Sola lettura, con un promemoria sempre visibile: "Stai guardando solo il Disco 1. Per aggiungere foto collega anche il Disco 2" |
| Entrambi i dischi | Controllo veloce automatico, poi tutto attivo |
| Disco nuovo, vuoto | "Questo disco è nuovo. Vuoi prepararlo per le tue foto?" → §2 |
| Disco che non c'entra (chiavetta, disco di altro) | Ignorato; se è l'unico collegato: "Questo non è un disco delle foto. Collega i dischi con l'etichetta PhotoSaver" |
| Dischi di due archivi diversi | "Questi due dischi non sono della stessa raccolta di foto. Scollegane uno." Nessuna operazione |
| Operazione interrotta (es. disco staccato durante la copia) | "L'ultima volta qualcosa si è interrotto. Le tue foto sono al sicuro: sistemo io." [Sistema] |
| Il controllo veloce trova differenze | Messaggio chiaro con il numero di problemi e un unico pulsante "Vediamo insieme" che porta al Check (§4) |

### Fine: scollegare i dischi

Un pulsante sempre visibile **"Ho finito"**: l'app termina quello che sta
facendo (o chiede se interrompere), smonta i dischi in sicurezza e dice
"Ora puoi scollegare i dischi e riporli". Così non serve sapere cos'è
"rimozione sicura dell'hardware".

## 2. Creare un archivio (inizializzazione)

Procedura guidata:

1. **Scegli il disco A** → avviso "verrà cancellato" → conferma scrivendo il
   nome del disco → formattazione exFAT (sui dischi simulati: niente formattazione).
2. Creazione di `.photosaver/` e della cartella archivio.
3. **Scegli il disco B** → stessi passaggi.
4. Fine: archivio vuoto, pronto per il primo caricamento.

### Sostituire un disco ✅ (nell'MVP)

Se un disco si rompe: "Sostituisci disco" → inizializza un disco nuovo come
A o B dello stesso archivio → copia completa con verifica dal disco sano.
È il motivo per cui esiste il mirror: senza questo flusso, rimettere in piedi la
seconda copia andrebbe fatto a mano.

## 3. Caricare foto

1. **Scegli una o più cartelle** (pulsante o trascinamento nella finestra).
2. **Analisi**: conta i file, legge le date, calcola gli hash, cerca doppioni
   già in archivio.
3. **Anteprima** prima di copiare:
   ```
   MARE 2027            412 foto · 38 video · 9,1 GB
     → destinazione:  FOTO 2027/MARE 2027            [cambia]
     ⚠ 3 foto già presenti in archivio                [vedi]
     ℹ 12 file ignorati (non sono foto o video)      [vedi]
   ```
   La destinazione può essere una cartella **nuova** o una **già esistente**
   (es. aggiungere foto a `LAGO 2026`). Se un file con lo stesso nome esiste già:
   - stesso contenuto → viene saltato (è lo stesso file);
   - contenuto diverso → l'app chiede: rinomina il nuovo (`nome_2.jpg`) / salta.
     Un file in archivio non viene mai sovrascritto dal caricamento.
   **Destinazione proposta**: la cartella dell'anno della maggior parte delle
   foto (quella esistente, es. `FOTO 2026`, o una nuova chiamata come le altre,
   o solo `2026`) + il nome della cartella caricata. Un intero albero di
   archivio (tutte le foto dentro cartelle con un anno nel nome) va nella
   radice dell'archivio, così com'è. I confronti dei nomi ignorano
   maiuscole e minuscole, come exFAT.
   **Doppioni** (stesso contenuto già in archivio o due volte nel caricamento):
   saltati, a meno di chiedere di caricarli comunque.
4. **Copia** su A e B in parallelo, con verifica. Barra di avanzamento,
   tempo stimato, pausa/annulla. Se si interrompe, riprende da dove era rimasta.
5. **Riepilogo** → "Copia verificata su entrambi i dischi. Eliminare le
   cartelle originali?" [Elimina] [Tieni].
   Si eliminano solo i file il cui contenuto è nell'indice come integro su
   **tutti** i dischi e che non sono cambiati dopo l'analisi. Restano i file
   ignorati (non foto), quelli saltati per un conflitto di nome e le
   cartelle non vuote.

**Ripresa**: rifare analisi e caricamento riprende da dove si era interrotto.
I file già copiati risultano "già presenti"; un file trovato sul disco ma non
ancora nell'indice (interruzione tra copia e registrazione) viene verificato
con l'hash e adottato, senza ricopiarlo.

## 4. Check

- **Rapido**: automatico quando si collegano entrambi i dischi, dura secondi.
  Confronta ogni disco con l'indice per dimensione e data (tolleranza 2 s,
  per FAT/exFAT) e rilegge solo i file che sembrano diversi o nuovi:
  - **mancante**: nell'indice ma non sul disco;
  - **non registrato**: sul disco ma non nell'indice (aggiunto fuori dall'app);
  - **corrotto**: contenuto diverso con la stessa data (nessuno l'ha toccato);
  - **modificato**: contenuto e data diversi (modificato fuori dall'app);
  - data cambiata ma contenuto uguale: nessun problema.
  - **spostato o rinominato**: un file mancante e uno nuovo con lo stesso
    contenuto sullo stesso disco; tra più candidati vince quello con lo
    stesso nome. Una copia (l'originale è ancora al suo posto) non è uno
    spostamento.

  Una cartella illeggibile è un errore, non "file mancanti".
- **Completo**: lanciato a mano (o su promemoria), rilegge e verifica tutti
  gli hash; avanzamento visibile, può riprendere.
  I dischi si leggono **in parallelo** (un thread per disco). Lo stato di ogni
  copia (`ok`, `missing`, `corrupt`, `modified`) e l'ora della verifica si
  salvano nell'indice man mano: se il check si interrompe, il successivo
  riparte saltando i file già verificati, e ripropone i problemi già trovati.
  Si può fare anche con un solo disco collegato (verifica solo quel disco).

Risultato: un **elenco di differenze raggruppate per tipo**, ognuna con
l'azione proposta già selezionata quando è ovvia:

```
Corrotti (2)                 azione proposta
  FOTO 2021/…/IMG_01.jpg     ripristina da B ✓
Mancanti su B (14)
  FOTO 2027/…                copia da A ✓
Cancellati su A (3)
  FOTO 2026/…                cancella anche da B / ripristina su A   ← da scegliere
Spostati (1)
  … → …                      ripeti spostamento su B ✓
                                         [Applica 17 azioni]
```

Per ogni voce si può anche scegliere **"segna come noto"**, così non viene più
riproposta.

## 5. Archivio (visualizzatore)

```
┌──────────────┬───────────────────────────────────────────┐
│ ▾ FOTO 2026  │ ▢ ▢ ▢ ▢ ▢ ▢                                │
│   LAGO 2026  │ ▢ ▢ ▢ ▢ ▢ ▢     griglia di miniature       │
│   NEVE 2026  │ ▢ ▢ ▢ ▢ ▢ ▢     con indicatore di stato    │
│ ▸ FOTO 2025  │                                            │
└──────────────┴───────────────────────────────────────────┘
```

- Albero delle cartelle a sinistra, miniature a destra; doppio clic per
  l'anteprima a schermo intero (foto e video).
- L'**indicatore di stato** compare solo quando c'è un problema (es. "solo su A"),
  per non riempire la griglia di icone.
- Funziona con un solo disco collegato.
- **Modifiche dall'app**: rinomina, sposta, cancella (nel cestino), crea una
  cartella. Ogni modifica viene applicata **su entrambi i dischi** e
  registrata nello storico, quindi servono tutti e due collegati. Con un solo
  disco il visualizzatore è in sola lettura.

## 6. Storico

Elenco cronologico di tutte le operazioni (caricamenti, check, riparazioni,
cancellazioni, spostamenti), con filtro per tipo e cartella. È salvato
nell'indice, quindi uguale su A e B e visibile su ogni computer.

## 7. Cestino

File cancellati, con data di cancellazione e giorni rimasti prima dello
svuotamento automatico. Azioni: **ripristina** e **svuota**.

## 8. Impostazioni

Giorni prima dello svuotamento del cestino, intervallo del promemoria per il
check completo, lingua. Le impostazioni dell'archivio (es. giorni del cestino)
stanno sui dischi; quelle del computer (es. dimensione della finestra) sul computer.
