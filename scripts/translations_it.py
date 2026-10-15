"""Italian translations of the interface texts (source text -> translation).

Plural forms (texts with %n) are (singular, plural). Words follow the glossary of
doc/flussi.md: no technical terms in the interface.
"""

ITALIAN: dict[str, str | tuple[str, str]] = {
    # Screens and window
    "Back": "Indietro",
    "More": "Altro",
    "I'm done": "Ho finito",
    "Finish and unplug the disks safely": "Termina e scollega i dischi in sicurezza",
    # Home
    "Your photos": "Le tue foto",
    "Add photos": "Aggiungi foto",
    "Look at your photos": "Guarda le foto",
    "Check the disks": "Controlla i dischi",
    "Your photos are safe on both disks.": "Le tue foto sono al sicuro su entrambi i dischi.",
    # Connecting the disks
    "Connect the two photo disks": "Collega i due dischi delle foto",
    "Take the two disks with the PhotoSaver label and plug them into the USB ports of the "
    "computer with their cable.": (
        "Prendi i due dischi con l'etichetta PhotoSaver e collegali con il loro cavo "
        "alle prese USB del computer."
    ),
    "I can't see any disk. Check that the cable is plugged in well; if the disk has a small "
    "light, it must be on.": (
        "Non vedo nessun disco. Controlla che il cavo sia ben inserito; se il disco ha una "
        "lucina, deve essere accesa."
    ),
    "I only have one disk with me ›": "Ho un solo disco con me ›",
    "Is it the first time? ›": "È la prima volta? ›",
    "Disk %1": "Disco %1",
    "found": "trovato",
    "waiting…": "in attesa…",
    "These two disks are not of the same photo collection. Unplug one of them.": (
        "Questi due dischi non sono della stessa raccolta di foto. Scollegane uno."
    ),
    "This disk is new. Do you want to prepare it for your photos?": (
        "Questo disco è nuovo. Vuoi prepararlo per le tue foto?"
    ),
    "Prepare": "Prepara",
    "I can't read this disk. Unplug it and plug it in again.": (
        "Non riesco a leggere questo disco. Scollegalo e ricollegalo."
    ),
    "This is not a photo disk. Connect the disks with the PhotoSaver label.": (
        "Questo non è un disco delle foto. Collega i dischi con l'etichetta PhotoSaver."
    ),
    "not connected": "non collegato",
    "connected": "collegato",
    "connected · %1 free": "collegato · %1 liberi",
    "Perfect, both disks are here": "Perfetto, ho trovato entrambi i dischi",
    "I'm checking that all the photos are fine… it takes a few seconds.": (
        "Sto controllando che le foto siano tutte a posto… ci vuole qualche secondo."
    ),
    "Last time something was interrupted. Your photos are safe: I'll fix it.": (
        "L'ultima volta qualcosa si è interrotto. Le tue foto sono al sicuro: sistemo io."
    ),
    "Fix": "Sistema",
    "I found %n thing(s) to sort out on the disks.": (
        "Ho trovato %n cosa da sistemare sui dischi.",
        "Ho trovato %n cose da sistemare sui dischi.",
    ),
    "Let's look together": "Vediamo insieme",
    "Some files can't be read. Run a check of the disks.": (
        "Alcuni file non si riescono a leggere. Fai un controllo dei dischi."
    ),
    "Check": "Controlla",
    "I'm finishing what was interrupted…": "Sto completando quello che si era interrotto…",
    "You are looking at Disk %1 only. To add photos, connect Disk %2 too.": (
        "Stai guardando solo il Disco %1. Per aggiungere foto collega anche il Disco %2."
    ),
    "Something went wrong, your photos were not touched: %1": (
        "Qualcosa non è andato, le tue foto non sono state toccate: %1"
    ),
    "You can unplug the disks now": "Ora puoi scollegare i dischi",
    "Put them away in a safe place. See you next time!": (
        "Riponili in un posto sicuro. Alla prossima!"
    ),
    "Close PhotoSaver": "Chiudi PhotoSaver",
    # Preparing the disks
    "Let's prepare the disks": "Prepariamo i dischi",
    "You need two new disks: your photos will be kept on both, so if one breaks they are "
    "still safe on the other.": (
        "Servono due dischi nuovi: le tue foto staranno su entrambi, così se uno si rompe "
        "sono ancora al sicuro sull'altro."
    ),
    "Everything on the two disks will be erased.": (
        "Tutto quello che c'è sui due dischi verrà cancellato."
    ),
    "Start": "Inizia",
    "Connect the new disk for Disk %1": "Collega il disco nuovo per il Disco %1",
    "Plug it in, then choose it here.": "Collegalo, poi sceglilo qui.",
    "Waiting for a new disk…": "Aspetto un disco nuovo…",
    "Next": "Avanti",
    "A disk that already contains files can't be used yet: it must be empty.": (
        "Un disco che contiene già dei file per ora non si può usare: deve essere vuoto."
    ),
    "Prepare “%1” as Disk %2?": "Preparo “%1” come Disco %2?",
    "Everything on this disk will be erased. This can't be undone.": (
        "Tutto quello che c'è su questo disco verrà cancellato. Non si può tornare indietro."
    ),
    "Yes, this disk can be erased": "Sì, questo disco si può cancellare",
    "Prepare Disk %1": "Prepara il Disco %1",
    "Photos": "Foto",
    "Disk %1 is ready": "Il Disco %1 è pronto",
    "Write “Disk %1” on a sticker and put it on the disk, so you'll always know which one it is.": (
        "Scrivi “Disco %1” su un'etichetta e attaccala al disco, così saprai sempre qual è."
    ),
    "The disks are ready! Now you can add your photos.": (
        "I dischi sono pronti! Ora puoi aggiungere le tue foto."
    ),
    "Done": "Fatto",
    "Next: Disk %1": "Avanti: Disco %1",
    # Adding photos
    "Choose the folders with the photos to add. You can also drag them here.": (
        "Scegli le cartelle con le foto da aggiungere. Puoi anche trascinarle qui."
    ),
    "Choose a folder…": "Scegli una cartella…",
    "This folder is already on the photo disks: choose one on the computer.": (
        "Questa cartella è già sui dischi delle foto: scegline una sul computer."
    ),
    "Remove from the list": "Togli dall'elenco",
    "Choose a folder of photos": "Scegli una cartella di foto",
    "Where do you want to put these photos?": "Dove vuoi mettere queste foto?",
    "In the folder:": "Nella cartella:",
    "With the name:": "Con il nome:",
    "%n photo(s)": ("%n foto", "%n foto"),
    "%n video(s)": ("%n video", "%n video"),
    "Change": "Cambia",
    "They will go in: <b>%1</b>": "Andranno in: <b>%1</b>",
    "They will go in your photos as they are, with their folders.": (
        "Andranno tra le tue foto così come sono, con le loro cartelle."
    ),
    "%n photo(s) are already on the disks: I won't copy them again.": (
        "%n foto è già sui dischi: non la copio di nuovo.",
        "%n foto sono già sui dischi: non le copio di nuovo.",
    ),
    "%n photo(s) are already in your photos in another folder: I'll skip them.": (
        "%n foto è già tra le tue foto in un'altra cartella: la salto.",
        "%n foto sono già tra le tue foto in un'altra cartella: le salto.",
    ),
    "%n photo(s) have the same name as different photos already there: I'll save them with "
    "a new name.": (
        "%n foto ha lo stesso nome di una foto diversa già presente: la salvo con un nome nuovo.",
        "%n foto hanno lo stesso nome di foto diverse già presenti: le salvo con un nome nuovo.",
    ),
    "%n file(s) are not photos or videos: they stay where they are.": (
        "%n file non è una foto né un video: resta dov'è.",
        "%n file non sono foto né video: restano dove sono.",
    ),
    "%n file(s) can't be read.": (
        "%n file non si riesce a leggere.",
        "%n file non si riescono a leggere.",
    ),
    "Here's what I'll do": "Ecco cosa farò",
    "Copy also the photos that are already in another folder": (
        "Copia anche le foto che sono già in un'altra cartella"
    ),
    "There is nothing new to copy: these photos are already safe.": (
        "Non c'è niente di nuovo da copiare: queste foto sono già al sicuro."
    ),
    "Copy %n photo(s) to both disks": (
        "Copia %n foto sui due dischi",
        "Copia %n foto sui due dischi",
    ),
    "I'm looking at the photos…": "Sto guardando le foto…",
    "It may take a while with many photos.": "Con tante foto può volerci un po'.",
    "Stop": "Interrompi",
    "I'm copying the photos to both disks…": "Sto copiando le foto sui due dischi…",
    "Every photo is checked after copying. You can wait calmly, or stop and go on another time.": (
        "Ogni foto viene controllata dopo la copia. Puoi aspettare tranquillamente, "
        "oppure interrompere e continuare un'altra volta."
    ),
    "%1 left": "mancano %1",
    "Done!": "Fatto!",
    "Almost done": "Quasi fatto",
    "%n photo(s) are now safe on both disks.": (
        "%n foto ora è al sicuro su entrambi i dischi.",
        "%n foto ora sono al sicuro su entrambi i dischi.",
    ),
    "%n file(s) could not be copied: they were changed or can't be read. They stay on the "
    "computer.": (
        "%n file non si è potuto copiare: è cambiato o non si legge. Resta sul computer.",
        "%n file non si sono potuti copiare: sono cambiati o non si leggono. Restano sul computer.",
    ),
    "Do you want to delete the original folders from the computer? The photos are already "
    "safe on the two disks.": (
        "Vuoi cancellare le cartelle originali dal computer? Le foto sono già al sicuro "
        "sui due dischi."
    ),
    "Keep them": "Tienile",
    "Delete the originals": "Cancella gli originali",
    "Copy stopped": "Copia interrotta",
    "The photos copied so far are safe on both disks. To go on, add the same folders again: "
    "I'll copy only what is missing.": (
        "Le foto copiate finora sono al sicuro su entrambi i dischi. Per continuare, aggiungi "
        "di nuovo le stesse cartelle: copierò solo quello che manca."
    ),
    "OK": "OK",
    "Something went wrong": "Qualcosa non è andato",
    "%1\n\nCheck that both disks are connected. The photos copied so far are safe; add the "
    "same folders again to go on.": (
        "%1\n\nControlla che entrambi i dischi siano collegati. Le foto copiate finora sono "
        "al sicuro; aggiungi di nuovo le stesse cartelle per continuare."
    ),
    # Durations
    "less than a minute": "meno di un minuto",
    "about %n minute(s)": ("circa %n minuto", "circa %n minuti"),
    "about %n hour(s)": ("circa %n ora", "circa %n ore"),
    # Checking the disks
    "Which check do you want to do?": "Che controllo vuoi fare?",
    "Quick check": "Controllo veloce",
    "A few seconds. Finds photos that are missing, added or moved.": (
        "Pochi secondi. Trova le foto mancanti, aggiunte o spostate."
    ),
    "Thorough check": "Controllo approfondito",
    "%1. Reads every photo again to find the ones that got damaged. You can stop it and go "
    "on another time.": (
        "%1. Rilegge ogni foto per trovare quelle che si sono rovinate. Puoi interromperlo "
        "e continuare un'altra volta."
    ),
    "Start the check": "Inizia il controllo",
    "I'm reading every photo…": "Sto rileggendo ogni foto…",
    "You can wait calmly, or stop and go on another time: I'll start again from here.": (
        "Puoi aspettare tranquillamente, oppure interrompere e continuare un'altra volta: "
        "riprenderò da qui."
    ),
    "I'm checking the disks…": "Sto controllando i dischi…",
    "Not now": "Non ora",
    "I'm sorting things out…": "Sto sistemando…",
    "%n thing(s) could not be sorted out. Check that both disks are connected and try again.": (
        "%n cosa non si è potuta sistemare. Controlla che entrambi i dischi siano collegati "
        "e riprova.",
        "%n cose non si sono potute sistemare. Controlla che entrambi i dischi siano collegati "
        "e riprova.",
    ),
    "Check again": "Controlla di nuovo",
    "Check stopped": "Controllo interrotto",
    "Next time the thorough check starts again from where it stopped.": (
        "La prossima volta il controllo approfondito riparte da dove si è fermato."
    ),
    "%1\n\nCheck that both disks are connected, then try again.": (
        "%1\n\nControlla che entrambi i dischi siano collegati, poi riprova."
    ),
    "Choose what to do…": "Scegli cosa fare…",
    "Show the photos": "Mostra le foto",
    "Hide the photos": "Nascondi le foto",
    "… and %n more": ("… e un'altra", "… e altre %n"),
    "All good!": "Tutto a posto!",
    "I found something to sort out": "Ho trovato qualcosa da sistemare",
    "For each line I've already chosen what to do when it's obvious. Check, then press the "
    "button.": (
        "Per ogni riga ho già scelto cosa fare quando è ovvio. Controlla, poi premi il pulsante."
    ),
    "%n file(s) or folder(s) can't be read. If it happens again, the disk may be failing: "
    "copy your photos to a new disk soon.": (
        "%n file o cartella non si riesce a leggere. Se succede di nuovo, il disco potrebbe "
        "rovinarsi: presto copia le foto su un disco nuovo.",
        "%n file o cartelle non si riescono a leggere. Se succede di nuovo, il disco potrebbe "
        "rovinarsi: presto copia le foto su un disco nuovo.",
    ),
    "%n known problem(s) not shown.": (
        "%n problema noto non è mostrato.",
        "%n problemi noti non sono mostrati.",
    ),
    "The lines without a choice stay as they are.": "Le righe senza una scelta restano come sono.",
    "Back to the start": "Torna all'inizio",
    "Sort out %n thing(s)": ("Sistema %n cosa", "Sistema %n cose"),
    " and ": " e ",
    "%n photo(s) got damaged on both disks": (
        "%n foto si è rovinata su entrambi i dischi",
        "%n foto si sono rovinate su entrambi i dischi",
    ),
    "%n photo(s) got damaged on %1": (
        "%n foto si è rovinata sul %1",
        "%n foto si sono rovinate sul %1",
    ),
    "%n photo(s) are missing on %1": ("%n foto manca sul %1", "%n foto mancano sul %1"),
    "%n photo(s) are missing on both disks": (
        "%n foto manca su entrambi i dischi",
        "%n foto mancano su entrambi i dischi",
    ),
    "%n photo(s) were changed on both disks": (
        "%n foto è stata modificata su entrambi i dischi",
        "%n foto sono state modificate su entrambi i dischi",
    ),
    "%n photo(s) were changed on %1": (
        "%n foto è stata modificata sul %1",
        "%n foto sono state modificate sul %1",
    ),
    "The folder “%1” was renamed “%2” on %3 (%n photo(s))": (
        "La cartella “%1” è stata rinominata “%2” sul %3 (%n foto)",
        "La cartella “%1” è stata rinominata “%2” sul %3 (%n foto)",
    ),
    "the main folder": "la cartella principale",
    "%n photo(s) were moved from “%1” to “%2” on %3": (
        "%n foto è stata spostata da “%1” a “%2” sul %3",
        "%n foto sono state spostate da “%1” a “%2” sul %3",
    ),
    "%n photo(s) were moved on %1": (
        "%n foto è stata spostata sul %1",
        "%n foto sono state spostate sul %1",
    ),
    "%n photo(s) were added without the app": (
        "%n foto è stata aggiunta senza l'app",
        "%n foto sono state aggiunte senza l'app",
    ),
    "%n photo(s) were added without the app, only on %1": (
        "%n foto è stata aggiunta senza l'app, solo sul %1",
        "%n foto sono state aggiunte senza l'app, solo sul %1",
    ),
    "%n photo(s) have different problems on the two disks": (
        "%n foto ha problemi diversi sui due dischi",
        "%n foto hanno problemi diversi sui due dischi",
    ),
    "Put back the original": "Rimetti l'originale",
    "Repair with the good copy from %1": "Ripara con la copia buona del %1",
    "Copy them again from %1": "Copia di nuovo dal %1",
    "Delete them from %1 too (they go to the trash)": "Cancella anche dal %1 (va nel cestino)",
    "Remove them from the list of your photos": "Togli dall'elenco delle tue foto",
    "Keep the version of %1": "Tieni la versione del %1",
    "That's fine, keep them there": "Va bene così, lascia lì",
    "Keep the change": "Tieni la modifica",
    "Do the same on %1": "Fai lo stesso sul %1",
    "Put them back where they were": "Rimetti com'era",
    "Add them to your photos (copy them to %1 too)": (
        "Aggiungi alle tue foto (e copia anche sul %1)"
    ),
    "Add them to your photos": "Aggiungi alle tue foto",
    "Delete them (they go to the trash)": "Cancella (va nel cestino)",
    "Leave it as it is, don't tell me again": "Lascia così, non dirmelo più",
    # History and trash
    "History": "Storico",
    "Trash": "Cestino",
    "Some photos could not be restored: a photo with the same name is already there.": (
        "Alcune foto non si sono potute ripristinare: c'è già una foto con lo stesso nome."
    ),
    "Everything done on your photos, most recent first.": (
        "Tutto quello che è stato fatto sulle tue foto, dal più recente."
    ),
    "Nothing yet.": "Ancora niente.",
    "You prepared Disk 1": "Hai preparato il Disco 1",
    "You prepared Disk %1": "Hai preparato il Disco %1",
    "Added %n photo(s)": ("Aggiunta %n foto", "Aggiunte %n foto"),
    "(stopped before the end)": "(interrotto prima della fine)",
    "Thorough check: %n thing(s) to sort out": (
        "Controllo approfondito: %n cosa da sistemare",
        "Controllo approfondito: %n cose da sistemare",
    ),
    "Thorough check: all good": "Controllo approfondito: tutto a posto",
    "Repaired %n photo(s)": ("Riparata %n foto", "Riparate %n foto"),
    "Deleted %n photo(s) (to the trash)": (
        "Cancellata %n foto (nel cestino)",
        "Cancellate %n foto (nel cestino)",
    ),
    "Removed %n photo(s) from the list": (
        "Tolta %n foto dall'elenco",
        "Tolte %n foto dall'elenco",
    ),
    "Kept the new version of %n photo(s)": (
        "Tenuta la versione nuova di %n foto",
        "Tenuta la versione nuova di %n foto",
    ),
    "Accepted %n change(s) made without the app": (
        "Accettata %n modifica fatta senza l'app",
        "Accettate %n modifiche fatte senza l'app",
    ),
    "Moved %n photo(s)": ("Spostata %n foto", "Spostate %n foto"),
    "Put back %n photo(s) where they were": (
        "Rimessa %n foto dov'era",
        "Rimesse %n foto dov'erano",
    ),
    "Added %n photo(s) found on the disks": (
        "Aggiunta %n foto trovata sui dischi",
        "Aggiunte %n foto trovate sui dischi",
    ),
    "%n problem(s) marked as known": (
        "%n problema segnato come noto",
        "%n problemi segnati come noti",
    ),
    "Restored %n file(s) from the trash": (
        "Ripristinato %n file dal cestino",
        "Ripristinati %n file dal cestino",
    ),
    "Emptied the trash (%n file(s))": (
        "Svuotato il cestino (%n file)",
        "Svuotato il cestino (%n file)",
    ),
    "Finished %n interrupted operation(s)": (
        "Completata %n operazione interrotta",
        "Completate %n operazioni interrotte",
    ),
    "Photos deleted or replaced by the app. They are deleted for good after %n day(s).": (
        "Foto cancellate o sostituite dall'app. Vengono eliminate definitivamente dopo %n giorno.",
        "Foto cancellate o sostituite dall'app. Vengono eliminate definitivamente dopo %n giorni.",
    ),
    "Photo": "Foto",
    "Folder": "Cartella",
    "Deleted": "Cancellata",
    "Deleted for good in": "Eliminata definitivamente tra",
    "%n day(s)": ("%n giorno", "%n giorni"),
    "%n file(s)": ("%n file", "%n file"),
    "Connect both disks to restore photos or empty the trash.": (
        "Collega entrambi i dischi per ripristinare le foto o svuotare il cestino."
    ),
    "Restore": "Ripristina",
    "Empty the trash": "Svuota il cestino",
    "Delete for good %n file(s)? This can't be undone.": (
        "Eliminare definitivamente %n file? Non si può tornare indietro.",
        "Eliminare definitivamente %n file? Non si può tornare indietro.",
    ),
    "Yes, delete them for good": "Sì, eliminali definitivamente",
    "Delete for good": "Elimina definitivamente",
    # Viewer
    "All your photos": "Tutte le tue foto",
    # Preview
    "Previous": "Precedente",
    "%1 of %2": "%1 di %2",
    "Loading…": "Caricamento…",
    "This photo can't be opened: it may be damaged.": (
        "Questa foto non si riesce ad aprire: potrebbe essere rovinata."
    ),
    "This video can't be played on this computer.": (
        "Questo video non si riesce a riprodurre su questo computer."
    ),
    # Badges
    "Missing on %1": "Manca sul %1",
    "Damaged on %1": "Rovinata sul %1",
    "Changed on %1": "Modificata sul %1",
    "Something is wrong on %1": "Qualcosa non va sul %1",
    "Check the disks to sort it out.": "Controlla i dischi per sistemare.",
    "%n photo(s) here need attention. Check the disks.": (
        "Qui %n foto ha bisogno di attenzione. Controlla i dischi.",
        "Qui %n foto hanno bisogno di attenzione. Controlla i dischi.",
    ),
}
