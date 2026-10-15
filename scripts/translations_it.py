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
}
