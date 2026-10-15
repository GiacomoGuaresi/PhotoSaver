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

## 1. Avvio e riconoscimento dei dischi

All'avvio, e ogni volta che si collega un disco, l'app cerca le cartelle
`.photosaver/` sui volumi collegati (in sviluppo: nei percorsi configurati).

| Situazione | Cosa succede |
|---|---|
| Nessun disco | Pagina di benvenuto: "Collega un disco" / "Crea un nuovo archivio" / "Apri un disco a mano" |
| Un disco dell'archivio | **Sola lettura**: visualizzatore e storico. Caricamento e check disattivati, con il motivo spiegato |
| Entrambi i dischi | Tutto attivo. Parte subito il **check rapido**; se trova differenze compare un avviso |
| Disco collegato ma vuoto, nuovo | Proposta: "Inizializza questo disco" |
| Due dischi di archivi diversi | Errore chiaro, nessuna operazione |
| Indici di A e B non allineati (es. operazione interrotta) | Il check rapido lo segnala e propone di ripristinare |

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

## 4. Check

- **Rapido**: automatico quando si collegano entrambi i dischi, dura secondi.
- **Completo**: lanciato a mano (o su promemoria), rilegge e verifica tutti
  gli hash; avanzamento visibile, può riprendere.

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
