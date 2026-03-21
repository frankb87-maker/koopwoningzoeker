import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

GEBIEDEN = [
    {"naam": "Beverwijk",  "slug": "beverwijk"},
    {"naam": "Heemskerk", "slug": "heemskerk"},
    {"naam": "Castricum", "slug": "castricum"},
    {"naam": "Uitgeest",  "slug": "uitgeest"},
]

MIN_PRIJS  = 200000
MAX_PRIJS  = 350000
MIN_SLAAPKAMERS = 2

def bouw_funda_url(slug):
    return (
        f"https://www.funda.nl/zoeken/koop/"
        f"?selected_area=%5B%22{slug}%22%5D"
        f"&price=%22{MIN_PRIJS}-{MAX_PRIJS}%22"
        f"&bedrooms_min={MIN_SLAAPKAMERS}"
        f"&availability=%5B%22available%22%5D"
        f"&publication_date=1"
        f"&sort=%22date_down%22"
    )

def bouw_html_mail(gebieden):
    vandaag = date.today().strftime("%-d %B %Y")

    rijen = ""
    for g in gebieden:
        url = bouw_funda_url(g["slug"])
        rijen += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #e8e8e0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:16px;font-weight:600;color:#1a1a18;">{g['naam']}</span><br>
                  <span style="font-size:13px;color:#7a7a70;">€200.000 – €350.000 · min. 2 slaapkamers · vandaag</span>
                </td>
                <td align="right" style="white-space:nowrap;">
                  <a href="{url}"
                     style="background:#1a6b4a;color:white;text-decoration:none;
                            padding:9px 20px;border-radius:8px;font-size:14px;
                            font-weight:600;display:inline-block;">
                    Bekijk op Funda →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f5f0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5f0;padding:24px 12px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e0d8;">

        <!-- HEADER -->
        <tr>
          <td style="background:#1a6b4a;padding:24px 28px;">
            <div style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
              Koopwoningzoeker
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.75);margin-top:4px;">
              Dagelijks overzicht · {vandaag}
            </div>
          </td>
        </tr>

        <!-- INTRO -->
        <tr>
          <td style="padding:20px 28px 4px;">
            <p style="margin:0;font-size:15px;color:#1a1a18;line-height:1.6;">
              Goedemorgen! Hieronder vind je de <strong>nieuwste koopwoningen</strong> van vandaag
              in jouw zoekgebieden. Klik op een knop om direct de resultaten te bekijken.
            </p>
          </td>
        </tr>

        <!-- CRITERIA BALK -->
        <tr>
          <td style="padding:16px 28px;">
            <table cellpadding="0" cellspacing="0"
                   style="background:#e8f5ef;border-radius:10px;padding:12px 16px;width:100%;">
              <tr>
                <td style="font-size:12px;color:#0f6e56;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">
                  Zoekcriteria
                </td>
              </tr>
              <tr>
                <td style="font-size:14px;color:#1a6b4a;padding-top:4px;">
                  💰 €200.000 – €350.000 &nbsp;·&nbsp;
                  🛏 Min. 2 slaapkamers &nbsp;·&nbsp;
                  🏠 Koop &nbsp;·&nbsp;
                  📅 Vandaag toegevoegd
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- GEBIEDEN -->
        <tr>
          <td style="padding:0 28px 8px;">
            <div style="font-size:12px;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.07em;color:#7a7a70;margin-bottom:4px;">
              Zoekgebieden
            </div>
            <table width="100%" cellpadding="0" cellspacing="0">
              {rijen}
            </table>
          </td>
        </tr>

        <!-- ALLES KNOP -->
        <tr>
          <td style="padding:16px 28px;">
            <a href="https://frankb87-maker.github.io/koopwoningzoeker"
               style="display:block;text-align:center;background:#f7f5f0;color:#1a6b4a;
                      text-decoration:none;padding:12px;border-radius:10px;
                      font-size:14px;font-weight:600;border:1px solid #c8e8d8;">
              🔍 Open de volledige woningzoeker-app
            </a>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="padding:16px 28px;border-top:1px solid #e8e8e0;">
            <p style="margin:0;font-size:12px;color:#aaa89a;text-align:center;line-height:1.6;">
              Koopwoningzoeker · automatisch verstuurd om 07:00<br>
              Beverwijk · Heemskerk · Castricum · Uitgeest
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return html

def stuur_email():
    html = bouw_html_mail(GEBIEDEN)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏠 Woningzoeker {date.today().strftime('%-d %b')} — nieuwe koopwoningen"
    msg["From"]    = os.environ["EMAIL_FROM"]
    msg["To"]      = os.environ["EMAIL_TO"]

    # Platte tekst fallback
    tekst = f"Koopwoningzoeker {date.today()}\n\n"
    for g in GEBIEDEN:
        tekst += f"{g['naam']}: {bouw_funda_url(g['slug'])}\n\n"
    tekst += "App: https://frankb87-maker.github.io/koopwoningzoeker\n"

    msg.attach(MIMEText(tekst, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASS"])
        s.send_message(msg)

    print(f"E-mail verstuurd op {date.today()}!")

stuur_email()
