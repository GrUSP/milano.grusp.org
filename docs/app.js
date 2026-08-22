/* Rendering degli incontri e invio del form di contatto.
   I dati arrivano da data/events.json, generato due volte al mese da
   .github/workflows/events.yml: same-origin, quindi nessun CORS e nessun proxy. */
(() => {
  "use strict";

  const MEETUP = "https://www.meetup.com/it-it/milanophp/";
  const PASSATI_MAX = 6;

  const giorno = new Intl.DateTimeFormat("it-IT", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
  const oraMin = new Intl.DateTimeFormat("it-IT", { hour: "2-digit", minute: "2-digit" });
  const breve = new Intl.DateTimeFormat("it-IT", { day: "numeric", month: "long", year: "numeric" });

  /* Titoli, estratti e nomi delle sedi arrivano da Meetup: sono testo di terze parti.
     Si costruiscono nodi e si assegna textContent, mai innerHTML. */
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  /* Per un gruppo milanese "Milano" accanto al nome della sede è rumore, e Meetup
     lo scrive in modo incoerente ("Milan" per una venue, "Milano" per un'altra).
     La città si mostra solo quando non è Milano, cioè quando aggiunge qualcosa. */
  const MILANO = /^milan(o)?$/i;
  const luogo = (ev) => {
    if (ev.online) return "Online";
    const citta = ev.venue?.city;
    return [ev.venue?.name, MILANO.test(citta || "") ? null : citta]
      .filter(Boolean).join(", ");
  };

  function cardProssimo(ev) {
    const d = new Date(ev.start);
    const box = el("article", "next-card");
    box.append(el("p", "when", `${giorno.format(d)} · ore ${oraMin.format(d)}`));

    const h4 = el("h4");
    h4.append(el("span", null, ev.title));
    box.append(h4);

    if (ev.excerpt) box.append(el("p", "excerpt", ev.excerpt));

    const dettagli = [luogo(ev), ev.going ? `${ev.going} iscritti` : ""].filter(Boolean);
    if (dettagli.length) box.append(el("p", "meta", dettagli.join(" · ")));

    const a = el("a", "btn btn-orange", "Iscriviti su Meetup");
    a.href = ev.url || MEETUP;
    box.append(a);
    return box;
  }

  function cardPassato(ev) {
    const box = el("article", "event-card");

    const t = el("time", null, breve.format(new Date(ev.start)));
    t.dateTime = ev.start;
    box.append(t);

    const h4 = el("h4");
    const a = el("a", null, ev.title);
    a.href = ev.url || MEETUP;
    h4.append(a);
    box.append(h4);

    const dettagli = [luogo(ev), ev.going ? `${ev.going} iscritti` : ""].filter(Boolean);
    if (dettagli.length) box.append(el("p", "meta", dettagli.join(" · ")));
    return box;
  }

  function statoVuoto(testo) {
    const box = el("div", "empty");
    box.append(el("p", null, testo));
    const a = el("a", "btn btn-orange", "Iscriviti al gruppo Meetup");
    a.href = MEETUP;
    box.append(a);
    return box;
  }

  /* Il conteggio esatto invecchia male e non dice più di un ordine di grandezza,
     quindi si arrotonda per difetto ai 500: 1488 diventa "1000+", e quando il gruppo
     passa 1500 diventa "1500+" da sé, senza toccare l'HTML. Sotto i 500 il numero
     tondo direbbe "0+", perciò lì si mostra il valore preciso. */
  const ordineDiGrandezza = (n) =>
    n < 500 ? n.toLocaleString("it-IT") : `${Math.floor(n / 500) * 500}+`;

  function stats(gruppo) {
    const ul = document.getElementById("stats");
    if (!ul || !gruppo) return;
    const membri = document.getElementById("stat-members");
    const voto = document.getElementById("stat-rating");
    if (gruppo.members) membri.textContent = ordineDiGrandezza(gruppo.members);
    if (gruppo.rating) voto.textContent = `${gruppo.rating.toFixed(2).replace(".", ",")}★`;
    // Si mostra solo se almeno un numero è arrivato: niente riga di trattini.
    if (gruppo.members || gruppo.rating) ul.hidden = false;
    // La stessa cifra compare nella sezione "Ospita una serata": una sola fonte,
    // così i due numeri non possono contraddirsi. Il valore in HTML fa da ripiego.
    const platea = document.getElementById("platea");
    if (platea && gruppo.members) platea.textContent = ordineDiGrandezza(gruppo.members);
  }

  async function incontri() {
    const prossimo = document.getElementById("prossimo");
    const passati = document.getElementById("passati");
    const titolo = document.getElementById("passati-titolo");
    try {
      const r = await fetch("data/events.json", { cache: "no-cache" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const dati = await r.json();

      stats(dati.group);

      prossimo.replaceChildren(
        dati.upcoming?.length
          ? cardProssimo(dati.upcoming[0])
          : statoVuoto("Nessun incontro in calendario in questo momento. "
              + "Iscriviti al gruppo Meetup: l’annuncio del prossimo arriva prima di tutto lì."));

      const elenco = (dati.past || []).slice(0, PASSATI_MAX);
      if (elenco.length) passati.replaceChildren(...elenco.map(cardPassato));
      else titolo.hidden = true;
    } catch (err) {
      // Il sito non deve mostrare un errore per un JSON mancante: si rimanda a Meetup.
      console.error("incontri non disponibili:", err);
      prossimo.replaceChildren(
        statoVuoto("Non riesco a caricare il calendario in questo momento. "
          + "Gli incontri sono sempre aggiornati su Meetup."));
      if (titolo) titolo.hidden = true;
    }
  }

  function form() {
    const f = document.getElementById("contact-form");
    if (!f) return;
    const esito = document.getElementById("form-status");
    const bottone = f.querySelector("button[type=submit]");

    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      esito.className = "form-status";
      esito.textContent = "Invio…";
      bottone.disabled = true;
      try {
        const r = await fetch(f.action, {
          method: "POST",
          headers: { Accept: "application/json" },
          body: new FormData(f),
        });
        const dati = await r.json().catch(() => ({}));
        if (!r.ok || dati.success === false) throw new Error(dati.message || `HTTP ${r.status}`);
        f.reset();
        esito.className = "form-status ok";
        esito.textContent = "Ricevuto, grazie. Ti rispondiamo appena possibile.";
      } catch (err) {
        console.error("invio form:", err);
        esito.className = "form-status ko";
        esito.textContent = "Invio non riuscito. Scrivi direttamente a milano@grusp.org.";
      } finally {
        bottone.disabled = false;
      }
    });
  }

  incontri();
  form();
})();
