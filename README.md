# milano.grusp.org

Sito del [#pugMi](https://www.meetup.com/it-it/milanophp/), il PHP User Group di Milano.
Una pagina statica servita da GitHub Pages. Nessun build step, nessuna dipendenza da installare.

## Com'è organizzato

```
docs/                  la sorgente di GitHub Pages: solo ciò che sta qui viene pubblicato
  index.html           la pagina, unica
  style.css
  app.js               rendering degli incontri e invio del form
  data/events.json     generato dal workflow, committato nel repo
scripts/fetch_events.py   scarica gli eventi da Meetup
.github/workflows/events.yml
_imports/              archivio dell'export WordPress del vecchio sito, non pubblicato
```

La sorgente di Pages è impostata su `main` / `/docs`: tutto quello che sta fuori da `docs/`
non è raggiungibile dal web. È una scelta voluta, `_imports/` contiene dati che non devono
finire online.

## Guardarlo in locale

```sh
python3 -m http.server -d docs
# poi apri http://localhost:8000
```

Va servito `docs/`, non la radice del repo: così il perimetro locale è identico a quello di
produzione e un percorso relativo sbagliato si rompe subito invece che dopo il deploy.

## Gli eventi

Meetup non ha più un'API pubblica, e i feed iCal e RSS del gruppo sono vuoti e senza header
CORS: il browser non può leggerli. I dati si ricavano dal blob `__NEXT_DATA__` della pagina
del gruppo, e a farlo è un workflow GitHub Actions che gira **il 1° e il 15 di ogni mese** e
committa `docs/data/events.json`. La pagina legge quel file same-origin.

Quando pubblicate un evento nuovo e volete che compaia subito, senza aspettare il cron:

```sh
gh workflow run events.yml
```

In locale:

```sh
python3 scripts/fetch_events.py          # scarica e riscrive il JSON
python3 scripts/fetch_events.py --demo   # self-check offline su scripts/fixture.html
```

Se Meetup cambia la struttura della pagina, lo script esce con errore e il workflow fallisce in
modo visibile, **senza** sovrascrivere l'ultimo JSON buono. In quel caso il sito continua a
mostrare gli eventi vecchi, e il `--demo` serve a capire offline cosa è cambiato.

## Il form di contatto

Passa da [Web3Forms](https://web3forms.com) e recapita all'indirizzo associato alla access key
in `docs/index.html`. La key è pubblica per progetto: è un alias dell'indirizzo email, non
autorizza altro che l'invio a quell'indirizzo, e in un sito statico non potrebbe comunque
essere tenuta segreta. Piano gratuito: 250 invii al mese.

Web3Forms rifiuta gli invii server-side sul piano gratuito, quindi il form si prova solo da
un browser vero: `curl` riceve sempre un rifiuto anche quando la configurazione è corretta.

## Modificare i contenuti

Tutti i testi stanno in `docs/index.html`, in chiaro: non c'è un CMS né un file di
configurazione separato. Le sezioni sono nell'ordine in cui appaiono, ognuna con il suo `id`.

| Cosa cambiare | Dove |
|---|---|
| Testi di qualsiasi sezione | `docs/index.html`, dentro la `<section>` corrispondente |
| Richiesta di una sala | la sezione `#ospitanti` (`Cosa serve` / `Cosa offriamo`) |
| Organizzatori | la sezione `#organizzatori` |
| Indirizzo del form, social | la sezione `#contatti` e il `<footer>` |
| Colori e spaziature | le variabili in cima a `docs/style.css` |
| Prossimi incontri e incontri passati | **non si toccano a mano**: arrivano da Meetup |

I colori sono definiti una volta sola come variabili CSS in `:root`. Se ne cambiate uno,
ricontrollate il contrasto: la palette del PUG ha due colori (il blu `#6683B9` e l'arancio
`#F29200`) che **non** raggiungono 4.5:1 su fondo bianco e non vanno usati per il testo
corrente. L'arancio funziona come fondo dei bottoni, con il testo scuro sopra.

Il numero di sviluppatori citato in `Cosa offriamo` e quello nei numeri dell'hero vengono
dalla stessa funzione in `app.js`, arrotondati per difetto ai 500 partendo dal conteggio vero
di Meetup: non possono contraddirsi, e il valore scritto in HTML fa solo da ripiego se il
JavaScript non gira.

## Dominio

`docs/CNAME` contiene `milano.grusp.org`. Perché risolva serve un record DNS sul dominio
`grusp.org`:

```
CNAME   milano   ->   grusp.github.io
```

Un solo record, non i quattro record A dell'apex: `milano` è un sottodominio. Finché il DNS
punta altrove il sito resta visibile su `https://grusp.github.io/milano.grusp.org/`.
Dopo la propagazione va spuntato *Enforce HTTPS* in Settings → Pages.

## Licenza

MIT, vedi [LICENSE](LICENSE).
