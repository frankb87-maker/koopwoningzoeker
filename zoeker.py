import os, requests, smtplib, json
from email.mime.text import MIMEText
from datetime import date

GEBIEDEN = ["beverwijk", "heemskerk", "castricum",
            "velsen", "uitgeest"]
MAX_PRIJS = 330000
MIN_SLAAPKAMERS = 2

def bouw_funda_url(gebied):
    return (
        f"https://www.funda.nl/zoeken/koop/"
        f"?selected_area=%5B%22{gebied}%22%5D"
        f"&price_max={MAX_PRIJS}"
        f"&bedrooms_min={MIN_SLAAPKAMERS}"
        f"&publication_date=1"
    )

def stuur_email(links):
    msg = MIMEText(
        "Nieuwe woningen gevonden!\n\n" +
        "\n".join(links) +
        "\n\nFijne dag!", "plain", "utf-8"
    )
    msg["Subject"] = f"Woningzoeker {date.today()}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"]   = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_FROM"],
                os.environ["EMAIL_PASS"])
        s.send_message(msg)

links = [bouw_funda_url(g) for g in GEBIEDEN]
stuur_email(links)
print("E-mail verstuurd!")
