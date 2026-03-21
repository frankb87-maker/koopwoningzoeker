import os, json, smtplib, requests, re, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from pathlib import Path

# ── Instellingen ──────────────────────────────────────────────
GEBIEDEN = [
    {"naam": "Beverwijk",  "slug": "beverwijk"},
    {"naam": "Heemskerk",  "slug": "heemskerk"},
    {"naam": "Castricum",  "slug": "castricum"},
    {"naam": "Uitgeest",   "slug": "uitgeest"},
]
MIN_PRIJS       = 200000
MAX_PRIJS       = 350000
MIN_SLAAPKAMERS = 2
DATA_BESTAND    = "woningen_cache.json"

# ── Funda URL helpers ─────────────────────────────────────────
def funda_url(slug, vandaag=True):
    pub = "&publication_date=1" if vandaag else ""
    return (
        f"https://www.funda.nl/zoeken/koop/"
        f"?selected_area=%5B%22{slug}%22%5D"
        f"&price=%22{MIN_PRIJS}-{MAX_PRIJS}%22"
        f"&bedrooms_min={MIN_SLAAPKAMERS}"
        f"&availability=%5B%22available%22%5D"
        f"{pub}"
        f"&sort=%22date_down%22"
    )

# ── Funda scraper ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def haal_woningen_op(slug):
    """Haalt woningen op van Funda voor een specifiek gebied."""
    url = funda_url(slug, vandaag=False)
    woningen = {}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text

        # Probeer listing data te extraheren uit de HTML
        # Funda embed data als JSON in script tags
        pattern = r'"id":(\d{7,9}).*?"askingPrice":(\d+).*?"street":"([^"]+)".*?"city":"([^"]+)"'
        for m in re.finditer(pattern, html, re.DOTALL):
            wid, prijs, straat, stad = m.groups()
            prijs_num = int(prijs)
            if not (MIN_PRIJS <= prijs_num <= MAX_PRIJS):
                continue
            woningen[wid] = {
                "id": wid,
                "adres": f"{straat}, {stad}",
                "prijs": prijs_num,
                "prijs_str": "€ {:,}".format(prijs_num).replace(",", "."),
                "url": f"https://www.funda.nl/detail/koop/{slug}/huis-{wid}/",
                "gebied": slug,
            }

        # Alternatief patroon
        if not woningen:
            pattern2 = r'"GlobalId":(\d+).*?"Koopprijs":(\d+).*?"Adres":"([^"]+)".*?"Woonplaats":"([^"]+)"'
            for m in re.finditer(pattern2, html, re.DOTALL):
                wid, prijs, adres, stad = m.groups()
                prijs_num = int(prijs)
                if not (MIN_PRIJS <= prijs_num <= MAX_PRIJS):
                    continue
                woningen[wid] = {
                    "id": wid,
                    "adres": f"{adres}, {stad}",
                    "prijs": prijs_num,
                    "prijs_str": "€ {:,}".format(prijs_num).replace(",", "."),
                    "url": f"https://www.funda.nl/detail/koop/{slug}/huis-{wid}/",
                    "gebied": slug,
                }

        print(f"  {slug}: {len(woningen)} woningen gevonden")

    except Exception as e:
        print(f"  Fout bij ophalen {slug}: {e}")

    return woningen

# ── Cache beheer ──────────────────────────────────────────────
def laad_cache():
    if Path(DATA_BESTAND).exists():
        with open(DATA_BESTAND, "r") as f:
            return json.load(f)
    return {}

def sla_cache_op(data):
    with open(DATA_BESTAND, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Vergelijk met vorige dag ──────────────────────────────────
def vergelijk(oud, nieuw):
    nieuwe_woningen = []
    prijs_omlaag    = []
    prijs_omhoog    = []

    for wid, woning in nieuw.items():
        if wid not in oud:
            nieuwe_woningen.append(woning)
        else:
            oude_prijs   = oud[wid].get("prijs", 0)
            nieuwe_prijs = woning.get("prijs", 0)
            if oude_prijs and nieuwe_prijs and oude_prijs != nieuwe_prijs:
                verschil = nieuwe_prijs - oude_prijs
                w = dict(woning)
                w["oude_prijs"]     = oude_prijs
                w["oude_prijs_str"] = "€ {:,}".format(oude_prijs).replace(",", ".")
                w["verschil"]       = verschil
                w["verschil_str"]   = "€ {:,}".format(abs(verschil)).replace(",", ".")
                if verschil < 0:
                    prijs_omlaag.append(w)
                else:
                    prijs_omhoog.append(w)

    return nieuwe_woningen, prijs_omlaag, prijs_omhoog

# ── HTML mail bouwen ──────────────────────────────────────────
def woning_rij_html(w, badge_bg, badge_kleur, badge_tekst, toon_oud=False):
    prijs_extra = ""
    if toon_oud:
        pijl = "▼" if w.get("verschil", 0) < 0 else "▲"
        prijs_extra = (
            f'<span style="font-size:12px;color:#7a7a70;margin-left:8px;">'
            f'was {w["oude_prijs_str"]} &nbsp;{pijl} {w["verschil_str"]}</span>'
        )
    return f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #f0ede8;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="padding-right:12px;">
            <span style="background:{badge_bg};color:{badge_kleur};font-size:10px;font-weight:700;
                         padding:2px 8px;border-radius:10px;text-transform:uppercase;
                         letter-spacing:0.04em;">{badge_tekst}</span><br>
            <span style="font-size:15px;font-weight:600;color:#1a1a18;">{w['prijs_str']}</span>
            {prijs_extra}<br>
            <span style="font-size:13px;color:#5a5a54;">{w['adres']}</span>
          </td>
          <td align="right" style="white-space:nowrap;vertical-align:middle;">
            <a href="{w['url']}" style="background:#1a6b4a;color:white;text-decoration:none;
               padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;display:inline-block;">
              Bekijk →
            </a>
          </td>
        </tr></table>
      </td>
    </tr>"""

def sectie_html(titel, icoon, woningen, badge_bg, badge_kleur, badge_tekst, toon_oud=False):
    if not woningen:
        return ""
    rijen = "".join(woning_rij_html(w, badge_bg, badge_kleur, badge_tekst, toon_oud) for w in woningen)
    return f"""
    <tr><td style="padding:16px 28px 4px;">
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#5a5a54;margin-bottom:6px;">
        {icoon} {titel} ({len(woningen)})
      </div>
      <table width="100%" cellpadding="0" cellspacing="0">{rijen}</table>
    </td></tr>"""

def bouw_mail(nieuwe, omlaag, omhoog, had_cache):
    vandaag   = date.today().strftime("%-d %B %Y")
    totaal    = len(nieuwe) + len(omlaag) + len(omhoog)
    scraper_ok = totaal > 0

    # Samenvatting
    delen = []
    if nieuwe:  delen.append(f"{len(nieuwe)} nieuw")
    if omlaag:  delen.append(f"{len(omlaag)} prijs verlaagd")
    if omhoog:  delen.append(f"{len(omhoog)} prijs verhoogd")
    samenvatting = " · ".join(delen) if delen else "Dagelijks overzicht"

    # Onderwerp
    onderwerp = f"🏠 Woningzoeker {date.today().strftime('%-d %b')} — {samenvatting}"

    # Inhoud sectie
    if scraper_ok:
        inhoud = (
            sectie_html("Nieuwe woningen",  "🏠", nieuwe, "#e8f5ef", "#0f6e56", "Nieuw") +
            sectie_html("Prijs verlaagd",   "📉", omlaag, "#fef3c7", "#92400e", "Prijs ↓", True) +
            sectie_html("Prijs verhoogd",   "📈", omhoog, "#fee2e2", "#991b1b", "Prijs ↑", True)
        )
    else:
        # Scraper kon geen details ophalen: toon knoppen per gebied als fallback
        rijen = ""
        for g in GEBIEDEN:
            url = funda_url(g["slug"], vandaag=True)
            rijen += f"""
            <tr><td style="padding:10px 0;border-bottom:1px solid #f0ede8;">
              <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td>
                  <span style="font-size:15px;font-weight:600;color:#1a1a18;">{g['naam']}</span><br>
                  <span style="font-size:13px;color:#5a5a54;">€200.000–€350.000 · min. 2 slaapkamers</span>
                </td>
                <td align="right">
                  <a href="{url}" style="background:#1a6b4a;color:white;text-decoration:none;
                     padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;display:inline-block;">
                    Bekijk →</a>
                </td>
              </tr></table>
            </td></tr>"""
        inhoud = f"""
        <tr><td style="padding:16px 28px 4px;">
          <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#5a5a54;margin-bottom:6px;">
            🔍 Zoek per gebied
          </div>
          <table width="100%" cellpadding="0" cellspacing="0">{rijen}</table>
        </td></tr>"""

    # Gebied knoppen onderaan
    knoppen = "".join(
        f'<a href="{funda_url(g["slug"])}" style="display:inline-block;margin:3px;background:#f0f0ea;'
        f'color:#1a6b4a;text-decoration:none;padding:5px 13px;border-radius:20px;'
        f'font-size:12px;font-weight:500;border:1px solid #c8e8d8;">{g["naam"]}</a>'
        for g in GEBIEDEN
    )

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f5f0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5f0;padding:24px 12px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e0d8;">

        <tr><td style="background:#1a6b4a;padding:22px 28px;">
          <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.3px;">Koopwoningzoeker</div>
          <div style="font-size:13px;color:rgba(255,255,255,0.75);margin-top:4px;">{vandaag} · {samenvatting}</div>
        </td></tr>

        <tr><td style="padding:14px 28px 8px;">
          <table cellpadding="0" cellspacing="0" style="background:#e8f5ef;border-radius:10px;padding:10px 14px;width:100%;">
            <tr><td style="font-size:13px;color:#1a6b4a;">
              💰 €200.000–€350.000 &nbsp;·&nbsp; 🛏 Min. 2 slaapkamers &nbsp;·&nbsp;
              📍 Beverwijk · Heemskerk · Castricum · Uitgeest
            </td></tr>
          </table>
        </td></tr>

        {inhoud}

        <tr><td style="padding:16px 28px;">
          <a href="https://frankb87-maker.github.io/koopwoningzoeker"
             style="display:block;text-align:center;background:#f7f5f0;color:#1a6b4a;
                    text-decoration:none;padding:12px;border-radius:10px;
                    font-size:14px;font-weight:600;border:1px solid #c8e8d8;">
            🔍 Open de volledige woningzoeker-app
          </a>
        </td></tr>

        <tr><td style="padding:0 28px 16px;text-align:center;">{knoppen}</td></tr>

        <tr><td style="padding:14px 28px;border-top:1px solid #e8e8e0;">
          <p style="margin:0;font-size:11px;color:#aaa89a;text-align:center;line-height:1.6;">
            Koopwoningzoeker · je ontvangt alleen een mail als er nieuws is.<br>
            Beverwijk · Heemskerk · Castricum · Uitgeest
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return html, onderwerp

# ── E-mail versturen ──────────────────────────────────────────
def stuur_email(html, onderwerp, nieuwe, omlaag, omhoog):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = onderwerp
    msg["From"]    = os.environ["EMAIL_FROM"]
    msg["To"]      = os.environ["EMAIL_TO"]

    # Platte tekst fallback
    tekst = f"Koopwoningzoeker — {date.today()}\n\n"
    if nieuwe:
        tekst += f"NIEUW ({len(nieuwe)}):\n"
        for w in nieuwe:
            tekst += f"  {w['prijs_str']} — {w['adres']}\n  {w['url']}\n\n"
    if omlaag:
        tekst += f"PRIJS VERLAAGD ({len(omlaag)}):\n"
        for w in omlaag:
            tekst += f"  {w['prijs_str']} (was {w['oude_prijs_str']}, -{w['verschil_str']}) — {w['adres']}\n  {w['url']}\n\n"
    if omhoog:
        tekst += f"PRIJS VERHOOGD ({len(omhoog)}):\n"
        for w in omhoog:
            tekst += f"  {w['prijs_str']} (was {w['oude_prijs_str']}, +{w['verschil_str']}) — {w['adres']}\n  {w['url']}\n\n"
    for g in GEBIEDEN:
        tekst += f"{g['naam']}: {funda_url(g['slug'])}\n"

    msg.attach(MIMEText(tekst, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASS"])
        s.send_message(msg)
    print(f"✅ Mail verstuurd: {len(nieuwe)} nieuw · {len(omlaag)} prijs↓ · {len(omhoog)} prijs↑")

# ── Hoofdprogramma ────────────────────────────────────────────
def main():
    print(f"🔍 Woningzoeker gestart — {date.today()}")

    cache    = laad_cache()
    had_cache = bool(cache)
    huidig   = {}

    for g in GEBIEDEN:
        print(f"  Zoeken in {g['naam']}...")
        woningen = haal_woningen_op(g["slug"])
        huidig.update(woningen)
        time.sleep(2)

    print(f"  Totaal gevonden: {len(huidig)} woningen")

    nieuwe, omlaag, omhoog = vergelijk(cache, huidig)
    totaal = len(nieuwe) + len(omlaag) + len(omhoog)
    print(f"  Wijzigingen: {len(nieuwe)} nieuw · {len(omlaag)} prijs↓ · {len(omhoog)} prijs↑")

    # Cache opslaan voor morgen
    sla_cache_op(huidig)

    # Mail bouwen en sturen
    html, onderwerp = bouw_mail(nieuwe, omlaag, omhoog, had_cache)

    if totaal > 0 or not had_cache:
        stuur_email(html, onderwerp, nieuwe, omlaag, omhoog)
    else:
        print("📭 Geen wijzigingen vandaag — geen mail verstuurd.")

if __name__ == "__main__":
    main()
