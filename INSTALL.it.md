# CATALINA (Python) - installazione ed esecuzione

(English version: [INSTALL.md](INSTALL.md))

## Requisiti
- Python 3.10 o superiore (sviluppato e provato con 3.13). Nessuna libreria esterna: solo libreria standard.
- Un browser (per la GUI). Java non serve.

## Installazione
1. Scompatta lo zip in una cartella qualsiasi (il percorso può contenere spazi).
2. Apri un terminale in quella cartella (`catalina_py`). Non c'è nulla da installare.
3. Controllo rapido: `python3 -c "import catalina, case_study; print('ok')"`
   (su Windows usa `python` o `py` al posto di `python3`).

## Eseguire il caso di studio
**GUI (consigliato):** `python3 -m case_study.gui` (oppure doppio clic su `run_gui.bat` / `./run_gui.sh`).
Si apre il browser su http://127.0.0.1:8765/. Premi "Start AVA". Comandi:
- Start / Suspend / Resume AVA, Reset
- Send a danger (route chiusa): poi rispondi nel campo TCS, prima il tipo (0 sconosciuto, 1 rocce, 2 incidente), poi la durata (1-100), con "Send"
- Low fuel (carburante in riserva)
- Slider velocità dell'orologio simulato (0.1x-100x) e "Pausa clock"
Opzioni: `--port 9000`, `--speed 2`, `--no-browser`.

**Senza GUI (log a terminale):**
`python3 tools/run_scenario.py 60 "never" 0` esegue 60 secondi simulati senza stimoli.
Pericolo dopo l'ingresso nella route 115, risposte TCS 0 e 30:
`python3 tools/run_scenario.py 80 "I enter Route: [115]" 1.5 1 0 30`
Carburante: come sopra con la variabile `STIMULUS=low_fuel` (Windows PowerShell: `$env:STIMULUS="low_fuel"`).

**Esperimenti:** vedi `case_study/experiment.py` (varianti, ripetizioni, CSV) e `case_study/scenario.py`.

## Uso della GUI, passo per passo
1. Avvia la GUI e premi **Start AVA**: l'auto parte, il log a destra mostra "I enter Route: [n]" e "I'm arrived in <città>".
2. **Send a danger** mentre l'auto è su una route (non prima, altrimenti non c'è nulla da vedere): l'auto si ferma e nel log compare
   "Why is the route closed?". Scrivi nel campo TCS `0`, `1` o `2` e premi **Send**; poi la durata (1-100, in slot da 15 minuti) e **Send**.
   L'auto torna indietro e ripianifica.
3. **Low fuel**: l'auto va a rifornirsi nella città più vicina e riprende.
4. Lo slider **Velocità** cambia la velocità dell'orologio simulato; **Pausa clock** lo ferma; **Suspend/Resume AVA** sospende/riprende gli
   agenti; **Reset** ricomincia da capo.

## Problemi comuni
- *La porta 8765 è occupata:* `python3 -m case_study.gui --port 9000`.
- *Il browser non si apre da solo:* aprire a mano l'indirizzo stampato dal programma (`http://127.0.0.1:8765/`).
- *"python3" non trovato (Windows):* usare `py` o `python`.
- *L'auto resta ferma dopo "Send a danger":* il pericolo va inviato quando l'auto è su una route; la telecamera virtuale lo vede una sola volta per esecuzione (come nel Java).

## Documentazione per chi sviluppa
`docs/GUIDA_SVILUPPATORE.md` (in inglese: `docs/DEVELOPER_GUIDE.md`; struttura del codice, flusso dei dati, come fare variazioni ed esperimenti, come estendere) e le docstring
in ogni modulo/classe del codice.

## Test
`python3 -I -m unittest discover -s tests -v` (pochi secondi). Vedi `tests/README.md`.

Opzionale: `pip install -e .` installa i pacchetti `catalina` e `case_study`, importabili da qualsiasi cartella.

## Note
- Velocità consigliata 1x-3x: il tempo di calcolo non scala con l'orologio simulato (vedi README.md).
- `Data/Critical_Beliefs.xml` è volutamente vuoto (conferma dell'autore del Java); `Data/Beliefs.xml` è la versione aggiornata (campi `Confidence` e `Is_Stimulus`, ignorati dal caricatore, perché la logica non li usa).
