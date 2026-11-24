# CATALINA (Python): guida per lo sviluppatore

(English version: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md))

Questa guida spiega come è fatto il codice, come scorrono i dati tra i componenti e dove mettere le mani per
realizzare variazioni ed esperimenti. I dettagli di ogni classe e funzione sono nelle docstring del codice
(ogni modulo ha in testa una docstring che ne descrive il ruolo e i comportamenti del Java mantenuti di proposito).
Installazione e comandi di uso: `INSTALL.it.md`. Come è stata verificata la fedeltà al Java: `README.md`.

## 1. Che cosa è

Port in Python dell'agente CATALINA (Java V0.3, "Case Study Journal 001"): un agente BDI con Global Workspace
(Baars) e funzioni esecutive (Buehler). Il caso di studio è un veicolo autonomo che visita città su una mappa
di 47 città e 132 route (66 archi bidirezionali), con pericoli sulle route e carburante in riserva.

Scelte di progetto concordate:
- le funzioni esecutive sono thread veri, che girano in parallelo (come nell'executive system di Buehler);
- il nucleo gira senza GUI; la GUI legge soltanto il registro degli eventi;
- comportamento compatibile con il Java prima di tutto (anche dove il Java ha difetti), correzioni dopo;
- verifica differenziale contro il Java originale.

## 2. Struttura delle cartelle

| Cartella | Contenuto |
|---|---|
| `catalina/` | il motore dell'architettura (indipendente dal caso di studio) |
| `case_study/` | il caso di studio: dominio, mappa, funzioni, wiring, scenari, esperimenti, GUI |
| `case_study/Data/` | i file XML del caso di studio (desideri, credenze, sensori, azioni...), dal repository Java, con `Beliefs.xml` aggiornato e `Critical_Beliefs.xml` vuoto |
| `tests/` | test differenziali contro output registrato dal Java (vedi `tests/README.md`) |
| `tools/` | `run_scenario.py` (scenario senza GUI) e utilità usate dai test |
| `docs/` | questa guida |

### 2.1 `catalina/` (motore)

| Modulo | Ruolo |
|---|---|
| `agent.py` | `Agent`: crea Long Memory, Global Workspace e le funzioni esecutive; getter e API di registrazione |
| `agent_thread.py` | `AgentBaseThread`: base dei thread esecutivi (ciclo, pausa, stop) |
| `clock.py` | `RealClock` e `SimClock` (orologio simulato con velocità e pausa) |
| `global_workspace.py` | `GlobalWorkspace`: lavagna condivisa e hub dei segnali di aggiornamento |
| `messages.py` | la "casella postale" di flag e code di messaggi di ogni componente |
| `long_memory.py` | `LongMemory`: credenze, predicati, desideri, regioni; caricamento XML e normalizzazione |
| `memory_maintenance.py` | passaggio stimoli filtrati -> credenze (Working Memory Maintenance) |
| `model.py`, `desires.py`, `plan.py` | modello dati: predicati, credenze, stimoli, regioni; desideri; azioni, opzioni, intenzioni |
| `formula.py` | formule booleane e temporali |
| `plan_library.py`, `sorters.py` | libreria di piani GLITTER (trie) e ordinamento canonico delle espressioni |
| `handlers.py` | i registri "nome -> funzione" usati dalle funzioni esecutive |
| `executive_*.py` | le funzioni esecutive (vedi 3.2) |
| `action_control.py` | esecuzione delle azioni tramite le funzioni registrate per nome |
| `protected.py`, `conscious_data.py`, `desire_data.py`, `maps.py`, `xmlio.py`, `enums.py` | contenitori thread-safe, dati coscienti, bundle di desideri, mappe da XML, helper XML, enumerazioni |

### 2.2 `case_study/`

| Modulo | Ruolo |
|---|---|
| `demo.py` | `AutonomousVehicleDemo`: collega tutto (equivalente del `Start()` Java) |
| `environment.py`, `map_data.py`, `domain.py` | mappa, route, percorsi (DFS) e simulazioni; coordinate generate dal Java; enum (`TCity`, ...) |
| `functions_perception.py` | sensori, estrazione stimoli, filtri di salienza, aggiornamento credenze |
| `functions_desires.py` | promozione di desideri esogeni (pericolo, poco carburante) |
| `functions_inhibition.py` | quali credenze e regioni restano "coscienti" per ogni desiderio; callback del GW |
| `functions_reasoner.py` | generazione delle opzioni (means-end), filtri green/quality, deliberazione |
| `functions_execution.py` | le 10 azioni eseguibili (movimento, attesa, rifornimento...) |
| `traffic_control.py`, `map_panel.py`, `common.py` | servizio di controllo del traffico simulato, modello del pannello mappa/auto, utilità |
| `events.py` | registro degli eventi (sostituisce il `Log_Memo` e la finestra del GW) |
| `scenario.py`, `experiment.py` | stimoli scriptati e ciclo di esecuzione; esperimenti ripetuti con varianti e CSV |
| `gui.py`, `gui_page.html` | GUI nel browser (server HTTP della libreria standard) |
| `javacompat.py` | comportamenti di collezioni Java da cui il caso di studio dipende (ordine di `HashMap`, `ConcurrentModificationException`) |

I nomi seguono quelli Java in snake_case (`TBelief.Get_Name()` diventa `Belief.get_name()`), così si può
confrontare il codice con l'originale riga per riga. Ogni modulo cita nella docstring le classi Java corrispondenti.

## 3. Come funziona

### 3.1 Il quadro generale

```
  sensori ──> [Perception] ──stimoli──> [Memory Maintenance] ──credenze──┐
                                                                          v
  [Desire Handler] <── segnali ── GLOBAL WORKSPACE (lavagna + broadcast) ──> [Inhibition]
        |  desideri attivi                    ^   |                           (cosa è cosciente)
        v                                     |   v
   [Reasoner]: opzioni -> filtri -> deliberazione ──intenzioni──> [Attention] (soglie)
                                                |
                                         [Switching] ──azione──> Action Control ──> funzione registrata
```

Tutti i componenti leggono e scrivono dati nel Global Workspace e si svegliano a vicenda con segnali di
aggiornamento (`broadcast_signal`). Nessuno chiama direttamente un altro.

### 3.2 Le funzioni esecutive

| Executive (file) | Quando agisce | Che cosa fa |
|---|---|---|
| Perception (`executive_perception.py`) | a ogni ciclo | interroga i sensori, estrae stimoli, assegna salienza, filtra con le soglie, pubblica gli stimoli filtrati |
| Memory Maintenance (`executive_memory.py`) | arrivano stimoli filtrati | aggiorna le credenze con la funzione registrata per tipo di stimolo e pubblica gli stimoli |
| Desire Handler (`executive_desires.py`) | segnali di dati/soglie/stimoli | cancella intenzioni fallite o soddisfatte, retrocede desideri poco salienti, promuove desideri esogeni (da stimoli) ed endogeni (condizione di attivazione vera e salienza sufficiente) |
| Inhibition (`executive_inhibition.py`) | cambiano le soglie | decide quali credenze, desideri e regioni restano "coscienti" in base alle intenzioni selezionate |
| Reasoner (`executive_reasoner.py`) | cambiano i desideri attivi | means-end (opzioni), operatore Finally, filtri green e quality, deliberazione, intenzioni selezionate |
| Attention (`executive_attention.py`) | cambiano le intenzioni selezionate | focalizza (soglie alte) se la prima intenzione ha opzioni, altrimenti defocalizza (0.3/0.3) |
| Switching (`executive_switching.py`) | solo mentre l'agente è focalizzato | esegue il piano della prima intenzione un'azione alla volta, controllando pre/post-condizioni |
| Resource Allocation (`executive_resources.py`) | non avviata dal caso di studio | gestione delle credenze critiche |

Ogni executive estende `AgentBaseThread` (`agent_thread.py`). Il ciclo è quello del Java:

```
attendi se in pausa -> attendi 50 ms (sull'orologio dell'agente) -> execute()
```

`execute()` di solito controlla i flag della propria casella postale (`self.message_handler`) e non fa nulla se
nessun segnale a cui è iscritta è arrivato. L'iscrizione ai segnali si dichiara in `insert_in_list_update_contract()`
(i tipi di segnale sono in `enums.TypeUpdateContract`).

### 3.3 Il Global Workspace e i segnali

`global_workspace.py` fa due cose:
1. tiene, sotto lock, le liste condivise: soglie, stimoli, credenze/desideri/regioni non inibiti, precondizioni, intenzioni,
   libreria dei piani;
2. propaga i segnali: `broadcast_signal(contratto)` alza il flag corrispondente nella propria casella e `broadcast()` lo
   copia nella casella di ogni executive iscritta a quel contratto.

I flag e le code di messaggi sono in `messages.py`. I segnali con dati (annulla opzione, cancella intenzione,
intenzione soddisfatta) viaggiano in code di messaggi con mittente e dati.

I lock Java (quattro `ReentrantReadWriteLock`) sono mutex rientranti; l'ordine di acquisizione è quello del Java.
Le callback del GW (`global_workspace_call_back`, `general_call_back`, in `case_study/functions_inhibition.py`)
girano dentro il GW, sotto i suoi lock: conviene tenerle brevi.

### 3.4 Ciclo di vita di un desiderio (flusso completo)

1. **Caricamento.** `LongMemory.load_data` legge gli XML di `Data/` (predicati, credenze, green/quality/epistemic/practical desires)
   e li normalizza (risolve i nomi in oggetti).
2. **Promozione.** Il Desire Handler cerca desideri pratici *standing* la cui `Trigger_Condition_Formula` è vera e la cui salienza
   supera la soglia; promossi diventano *Active* (`GlobalWorkspace.mark_as_active_desires`). In `Practical_Desires.xml`:
   `Visit_Frankfurt` (salienza 0.4), `Visit_Paris` (0.5), `Visit_Rome` (0.8, si attiva dopo `BL_City_Visited_Paris`).
   Gli stimoli (pericolo, poco carburante) generano invece desideri esogeni tramite `case_study/functions_desires.py`.
3. **Ragionamento.** Il Reasoner chiama la funzione means-end registrata per nome del desiderio (pratici) o per tipo di credenza
   (epistemici): produce le *opzioni* (per `Visit_<città>`: un'opzione per ogni percorso semplice trovato dalla DFS, con le sue
   azioni `Initialize_Way`, `GO_TO_Route`, `GO_TO_Step`). Poi: operatore Finally (scarta le opzioni fuori dall'intervallo),
   filtri green/quality (inquinamento, panorama, velocità), deliberazione (sceglie l'intenzione).
4. **Attenzione e inibizione.** L'Attention aggiorna le soglie; l'Inhibition decide quali credenze/regioni restano coscienti per
   l'intenzione scelta (le funzioni di `functions_inhibition.py`).
5. **Esecuzione.** Lo Switching esegue una azione alla volta: controlla le precondizioni, chiama la funzione registrata in Action
   Control per quel nome di azione (`functions_execution.py`), controlla le postcondizioni, e quando l'opzione è completa
   segnala al Desire Handler (intenzione soddisfatta, il piano finisce nella libreria) o la cancella.

### 3.5 Il caso di studio, passo per passo

`AutonomousVehicleDemo.start()` (`case_study/demo.py`) segue il `Start()` Java:
1. costruisce `MapPanelModel`, l'`Agent` (che carica i dati XML);
2. `initialize_data_simulation`: crea la mappa (`create_map`), aggiunge una `RegionSimulation` per ogni route alla Long Memory e
   mette la mappa nel predicato di `BL_Map`;
3. registra i gruppi di funzioni nell'ordine Java: percezione (sensori, estrazione, filtri), manutenzione memoria,
   inibizione di credenze e di regioni, promozione esogena, reasoner (means-end, filtri, deliberazione), esecuzione azioni;
4. sospende le sette executive.

`start_av()` ("Start AVA") avvia e riprende le sette executive, manda un broadcast e imposta le soglie a 0.3/0.3.

Dove si registra cosa (utile per aggiungere elementi):

| Elemento | Dove si registra | Chiave di registrazione |
|---|---|---|
| sensore | `FunctionsForPerceptionProcessing` (`functions_perception.py`) | nome sensore (`Front_Virtual_Camera`, `Traffic_Control_Service`, `Fuel_Sensor`) |
| estrazione stimoli | `FunctionsForInformationExtraction` | nome sensore |
| salienza/filtro stimolo | `FunctionsForStimulusFiltering` | tipo stimolo (`BLTS_Stimulus_...`); le salienze base sono in `Map_Belief_To_Salience_Stimuli.xml` |
| aggiornamento credenze | `FunctionsForGWMemoryMaintenanceUpdateBeliefFunction` | tipo stimolo |
| desiderio esogeno | `FunctionsForExogenousDesirePromotion` | tipo stimolo |
| means-end | `FunctionsForMeansEndReasoner` | nome del desiderio pratico / tipo di credenza dell'epistemico |
| inibizione credenze e regioni | `FunctionsForInhibitionFunction` | nome del desiderio / tipo di credenza |
| filtri green / quality | `FunctionsForFilteringDesiresFunction` | tipo di green desire; un solo filtro quality |
| deliberazione | `FunctionsForDeliberationProcess` | una funzione |
| azione | `FunctionsForOptionExecution` | nome dell'azione (le dieci azioni sono elencate in `add_function_to_switching_function`) |

Per lo stimolo di pericolo: la telecamera lo vede (`see_road_in_front`, **una sola volta per esecuzione**, come nel Java), il Memory
Maintenance segna la route `Under_maintenance`, nasce l'epistemic desire `Inquiry_Estimated_Delay`, la sua opzione ha due azioni:
`Ask Danger Type on the road` (domande al servizio di controllo del traffico: tipo di pericolo e durata) e
`Decide_To_Continue_or_Not`; i dati del servizio tornano come stimolo e il desiderio pratico viene riplanificato dalla route danneggiata.

### 3.6 Orologio simulato

Tutte le attese dell'agente (ciclo da 50 ms, passo dell'auto da 1 s) passano da `agent.clock`. `SimClock(speed)` le scala
insieme, quindi il rapporto 50 ms : 1 s resta quello del Java a qualsiasi velocità; velocità e pausa si cambiano mentre
l'agente gira. Il tempo di calcolo **non** è scalato: generare le opzioni per migliaia di percorsi richiede circa 2 secondi reali,
quindi oltre ~5x l'agente "ragiona" più lentamente in tempo simulato. Per confronti con il Java restare a 1x-3x; per confrontare
effetti relativi di variazioni si può salire.

### 3.7 Registro degli eventi e GUI

`case_study/events.py`: ogni cosa osservabile è un `Event(seq, sim, wall, thread, kind, data)`. Tipi:

| kind | contenuto |
|---|---|
| `log` | testo che il Java scriveva nel `Log_Memo` |
| `car_move` | `frm`, `to`, `duration` (secondi simulati), `route`, `step` |
| `gw_update`, `gw_signal` | riepiloghi delle callback del Global Workspace |
| `stimulus` | stimolo scriptato (pulsante) |
| `scenario` | inizio/fine run |

`event_log.text_lines()` restituisce le righe del log Java; `dump_jsonl(path)` salva tutto. La GUI (`gui.py` + `gui_page.html`) è un
piccolo server HTTP: la pagina interroga `/api/state?since=N`, anima l'auto interpolando linearmente sui `car_move` rispetto al
tempo simulato, e invia comandi a `/api/cmd/<nome>` (start, suspend, resume, danger, low_fuel, tcs, speed, pause, unpause, reset,
save_log). Per una GUI diversa (Tk, Qt...) basta sottoscriversi a `EventLog.subscribe` e chiamare i metodi di `AutonomousVehicleDemo`
(`start_av`, `send_a_danger`, `send_low_fuel_signal`, `submit_tcs_response`, `end_simulation`).

## 4. Variazioni ed esperimenti

### 4.1 Scenari (`case_study/scenario.py`)

```python
from case_study.scenario import Scenario, Stimulus, log_contains, run_scenario

sc = Scenario("danger_on_115", duration=80, tcs_answers=["0", "30"],      # tipo pericolo 0, durata 30 slot
              stimuli=[Stimulus("danger", when=log_contains("I enter Route: [115]"), delay=1.5)])
demo = run_scenario(sc, speed=1.0)
print(demo.event_log.as_text())
```

`Stimulus(kind, at, when, delay)`: `kind` è `"danger"` o `"low_fuel"`; parte quando sono passati `at` secondi simulati e `when(demo)` è vera
(più `delay` secondi). `tcs_answers` sono le risposte alle domande del servizio di controllo del traffico, in ordine.

### 4.2 Esperimenti (`case_study/experiment.py`)

`Variant(name, setup=None, loop_period_ms=None)`: `setup(demo)` viene chiamata dopo la costruzione e prima di "Start AVA", e può cambiare
qualunque cosa (funzioni registrate, soglie, parametri). Ogni run gira in un processo separato (`workers` in parallelo), quindi le
modifiche non si propagano tra le run.

Esempi provati (45 s simulati, velocità 2x, una run per variante):

```python
from case_study.experiment import Variant, run_experiment
from case_study.scenario import Scenario

def faster_car(demo):
    demo.functions_for_plan_execution.global_time_to_move = 0.5      # secondi simulati per passo (default 1.0)

def no_quality_filter(demo):
    reasoner = demo.agent.get_executive_reasoner_function()
    reasoner.set_quality_desire_filtering_process(lambda d, b, r, i: None)   # None = opzioni invariate

rows = run_experiment([Variant("default"), Variant("faster_car", setup=faster_car),
                       Variant("loop_25ms", loop_period_ms=25), Variant("no_quality", setup=no_quality_filter)],
                      Scenario("baseline", duration=45), repetitions=1, speed=2.0, workers=4, csv_path="results.csv")
```

Risultati osservati: `default` e `loop_25ms` arrivano in 5 città in 45 s; `faster_car` ne raggiunge 8 (Pamplona, Barcelona, Marseille,
Paris, Marseille, Rome, Marseille, ...); senza filtro quality l'auto sceglie altri percorsi (Barcelona, Marseille, Zurich, Venice, Munchen...).
Le metriche per run (`metrics()`): arrivi, sequenza di città, istanti del primo e dell'ultimo arrivo, route percorse, "no option",
"route closed", segnali del GW, eventi.

Altri punti di intervento utili:
- `global_workspace.set_default_saliency_thresholds` / `set_default_attention_thresholds`: soglie di default;
- `AgentBaseThread.LOOP_PERIOD_MS` (o `Variant(loop_period_ms=...)`): periodo dei cicli;
- `FunctionsForDeliberationProcess.deliberation_process_function` (`functions_reasoner.py`): quante intenzioni si perseguono e in che ordine;
- salienze e ricompense in `Data/*.xml` (gli XML usano la virgola decimale);
- `Environment`/`create_map`: mappa, colori delle route (`MyCollections` in `domain.py`), pesi.

## 5. Come estendere

**Nuovo desiderio pratico (es. un'altra città).** Aggiungere il desiderio in `Data/Practical_Desires.xml` e le credenze `BL_Destination_<Città>` in
`Data/Beliefs.xml` (con relativi predicati se servono), poi registrare per il suo nome la funzione means-end
(`reasoner_register_practical_function`, vedi `add_functions_to_means_end_reasoner`: oggi i nomi sono elencati nel codice) e le funzioni di inibizione
(`add_lists_for_practical_desires` in `functions_inhibition.py`). Nota: il codice registra anche `Visit_Cadiz`, che non è negli XML.

**Nuovo sensore e stimolo.** Aggiungere il sensore a `Sensors.xml`; in `functions_perception.py`: nome in `self.sensors`/`sensors_avaible`, funzione che
produce `Perception`, funzione di estrazione dello stimolo, filtro di salienza e aggiornamento credenze (tutte registrate per tipo di stimolo);
se deve generare un desiderio, aggiungere la funzione in `functions_desires.py`.

**Nuova azione.** Scrivere la funzione `(global_workspace, action, map_beliefs) -> ActionExecutionResult` in `functions_execution.py` e registrarla in
`add_function_to_switching_function` con lo stesso nome usato nelle azioni create dal means-end. Il risultato porta `beliefs_to_change`
(un dizionario `nome credenza -> [campo, valore, ...]`) che il framework applica alle credenze.

**Nuova executive function.** Sottoclasse di `AgentBaseThread` con `insert_in_list_update_contract()` (a quali segnali risponde) ed `execute()`
(una iterazione); crearla in `Agent.__init__`, aggiungerla a `Agent.executives()` e avviarla/riprenderla in `MapPanelModel.start_av`.
Se serve un nuovo tipo di segnale: voce in `TypeUpdateContract` e in `_SIGNAL_FLAG` / `_BROADCAST_FLAGS_*` di `global_workspace.py`, flag in `messages.py`.

**Nuovo filtro green/quality.** `register_green_filtering_function(tipo, funzione)`; il filtro quality è unico (`set_quality_desire_filtering_process`).

## 6. Fedeltà al Java

- Il port è stato confrontato con il Java reale sul log (`event_log.text_lines()`): sequenze di righe `I enter Route ...`, `I'm arrived in ...`,
  domande/risposte del servizio di traffico e messaggi di decisione, sul prefisso comune delle due tracce. Il Java non è deterministico nei tempi (race tra thread).
- Comportamenti del Java mantenuti di proposito (difetti compresi) sono elencati nel `README.md` ("Known Java quirks") e nelle docstring dei
  moduli `functions_*.py`. Per correggerne uno, farlo in un punto solo e confrontare il log dell'agente prima e dopo.

## 7. Limiti noti

- Prestazioni: la generazione delle opzioni è il collo di bottiglia (migliaia di percorsi per desiderio, ~2 s reali).
- Non confrontati con il Java: simulazioni oltre circa 110 secondi, combinazioni di più pericoli, stimolo di carburante durante un pericolo.
- La telecamera funziona una sola volta per esecuzione e il sensore GPS è ignorato (come nel Java).
- Il Java può fallire all'avvio in modo non deterministico (una volta osservata un'eccezione in `Execute_Movement_Go_TO_Route`): è una race del
  codice originale, non del port.
- Nessun test automatico della GUI; è stata provata a mano con un browser automatizzato (start, danger, risposte TCS, low fuel, suspend/resume, pausa,
  reset, slider).
