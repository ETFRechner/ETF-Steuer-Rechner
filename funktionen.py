import streamlit as st
import pandas as pd
import yfinance as yf
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import io
from reportlab.platypus import TableStyle
from datetime import datetime
import numpy as np

def eur(x):
    return f"{x:.2f}".replace(".", ",") + " €"

def anteil(x):
    return f"{x:.5f}".replace(".", ",")

import numpy as np
from datetime import datetime
import pandas as pd
import streamlit as st

def bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft, tagesgenau=False):

    shares = data["Anzahl"].to_numpy(dtype=float)
    prices = data["Preis"].to_numpy(dtype=float)
    dates = pd.to_datetime(data["Kaufdatum"]).to_numpy()

    # bereits verkaufte Anteile entfernen (FIFO)
    remaining = shares.copy()
    verkauft = bereits_verkauft

    for i in range(len(remaining)):
        if verkauft <= 0:
            break
        if remaining[i] <= verkauft:
            verkauft -= remaining[i]
            remaining[i] = 0
        else:
            remaining[i] -= verkauft
            verkauft = 0

    cum_shares = np.cumsum(remaining)

    if cum_shares[-1] < anzahl_verkaufen - 1e-9:
        st.warning("Sie verfügen nicht über ausreichend Anteile für das gewünschte Netto.")
        st.stop()

    idx = np.searchsorted(cum_shares, anzahl_verkaufen)

    verkaufte_shares = np.zeros_like(remaining)

    if idx > 0:
        verkaufte_shares[:idx] = remaining[:idx]

    if idx < len(remaining):
        vorher = cum_shares[idx-1] if idx > 0 else 0
        verkaufte_shares[idx] = anzahl_verkaufen - vorher

    # Gewinn und brutto (vektorisiert)
    gewinn = np.sum((aktueller_kurs - prices) * verkaufte_shares)
    brutto = np.sum(aktueller_kurs * verkaufte_shares)

    gesamte_vorabpauschale = 0

    if len(vorabpauschale) == 0:
        return gewinn, brutto, gesamte_vorabpauschale, 0

    vp_jahre = vorabpauschale["jahr"].to_numpy()
    vp_values = vorabpauschale["vorabpauschale_stueck"].to_numpy()

    for i in np.where(verkaufte_shares > 0)[0]:

        kaufdatum = pd.Timestamp(dates[i])
        jahr_kauf = kaufdatum.year

        mask = vp_jahre >= jahr_kauf

        jahre = vp_jahre[mask]
        vp = vp_values[mask]

        if len(jahre) == 0:
            continue

        if not tagesgenau:

            monate = np.where(
                jahre == jahr_kauf,
                12 - kaufdatum.month + 1,
                12
            )

            anteil = monate / 12

        else:

            anteil = np.ones_like(jahre, dtype=float)

            first_year_mask = jahre == jahr_kauf

            if np.any(first_year_mask):

                ende = datetime(jahr_kauf, 12, 31)
                tage = (ende - kaufdatum).days + 1
                anteil[first_year_mask] = tage / 365

        gesamte_vorabpauschale += np.sum(vp * anteil) * verkaufte_shares[i]

    return gewinn, brutto, gesamte_vorabpauschale, 0

def bestimme_netto(brutto, gewinn, steuersatz, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag):
    gewinn_steuerpflichtig = bestimme_steuerpflichtigen_gewinnn(gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag, all = False)
                                       
    # gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    # gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    # gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    # gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)

    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer

    return netto

def bestimme_steuerpflichtigen_gewinnn(gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag, all = False):
    gewinn_nach_vorabpauschale = gewinn - gesamte_vorabpauschale
    gewinn_teilfreistellung = gewinn_nach_vorabpauschale * (1 - teilfreistellung_quote)
    gewinn_nach_verlusttopf = max(0, gewinn_teilfreistellung - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    if all:
        return gewinn_nach_vorabpauschale, gewinn_teilfreistellung, gewinn_nach_verlusttopf, gewinn_steuerpflichtig
    else:
        return gewinn_steuerpflichtig


def finde_anteile(ziel_netto, max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag, tagesgeanue_berechnung):

    low = 0.0
    high = float(max_anteile)

    for _ in range(60):   # genügend Iterationen für hohe Genauigkeit

        mid = (low + high) / 2

        gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(
            mid, aktueller_kurs, data, vorabpauschale, bereits_verkauft, tagesgenau = tagesgeanue_berechnung
        )

        netto = bestimme_netto(
            brutto, gewinn, steuersatz, teilfreistellung_quote,
            gesamte_vorabpauschale, verlusttopf, freibetrag
        )

        if abs(netto - ziel_netto) < 0.000001:
            return round(mid, 6)

        if netto < ziel_netto:
            low = mid
        else:
            high = mid

    return round(mid, 6)

def finde_anteile_ohne_steuer(max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag, tagesgeanue_berechnung):

    low = 0.0
    high = float(max_anteile)

    # prüfen ob überhaupt Steuern entstehen
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(
        high, aktueller_kurs, data, vorabpauschale, bereits_verkauft, tagesgenau = tagesgeanue_berechnung
    )

    steuerpflichtiger_gewinn = bestimme_steuerpflichtigen_gewinnn(
        gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag
    )

    for _ in range(100):

        mid = (low + high) / 2

        gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(
            mid, aktueller_kurs, data, vorabpauschale, bereits_verkauft, tagesgenau = tagesgeanue_berechnung
        )

        steuerpflichtiger_gewinn = bestimme_steuerpflichtigen_gewinnn(
            gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag
        )

        if abs(high - low) < 0.000001:
            return round(mid, 6)

        if steuerpflichtiger_gewinn > 0:
            high = mid
        else:
            low = mid

    return round(mid, 6)

def detailierte_darstellung(anzahl_verkaufen, max_anteile, bereits_verkauft, brutto, gewinn, gewinn_teilfreistellung, gewinn_nach_vorabpauschale, gewinn_nach_verlusttopf, gewinn_steuerpflichtig, steuer, netto, gesamtkosten, vorabpauschale, aktueller_kurs, verlusttopf_nach_verkauf, gesamte_vorabpauschale, freibetrag):
    # gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    # st.markdown("## Detaillierte Berechnung")

    # -------------------------------
    # Überblick
    # -------------------------------

    st.markdown("### Überblick Ihrer Position (vor Verkauf)")

    col1, col2, col3 = st.columns(3)

    aktueller_besitz = max_anteile - bereits_verkauft
    gesamtwert = aktueller_besitz * aktueller_kurs

    col1.metric("Gekaufte Anteile", f"{anteil(max_anteile)}")
    col2.metric("Aktuell im Besitz", f"{anteil(aktueller_besitz)}")
    col3.metric("Gesamtwert", f"{eur(gesamtwert)}")

    durchschnittlicher_kaufpreis = gesamtkosten / max_anteile

    st.caption(f"Durchschnittlicher Kaufpreis: {eur(durchschnittlicher_kaufpreis)} pro Anteil")

    # -------------------------------
    # Verkaufsübersicht
    # -------------------------------

    st.markdown("### Verkaufsübersicht")

    col1, col2, col3 = st.columns(3)

    col1.metric("Verkaufte Anteile", f"{anteil(anzahl_verkaufen)}")
    col2.metric("Kurs bei Verkauf", f"{eur(aktueller_kurs)}")
    col3.metric("Verlusttopf nach Verkauf", f"{eur(verlusttopf_nach_verkauf)}")
    

    # -------------------------------
    # Steuerberechnung
    # -------------------------------

    st.markdown("### Steuerberechnung")

    steuer_df = pd.DataFrame({
        "Berechnungsschritt": [
            "Anzahl zu verkaufender Anteile",
            "Kurs bei Verkauf",
            "Brutto Verkaufserlös",
            "Gewinn vor Steuer",
            "Abzuziehende Vorabpauschale",
            "Gewinn nach Vorabpauschale",
            "Gewinn nach Teilfreistellung",
            "Gewinn nach Verlusttopf",
            "Neuer Verlusttopf",
            "Gewinn nach Sparerpauschbetrag",
            "Ungenutzter Sparerpauschbetrag",
            "Zu zahlende Steuer",
            "Netto nach Steuern"
        ],
        "Betrag": [
            f"{anteil(anzahl_verkaufen)}",
            f"{eur(aktueller_kurs)}",
            f"{eur(brutto)}",
            f"{eur(gewinn)}",
            f"{eur(gesamte_vorabpauschale)}",
            f"{eur(gewinn_nach_vorabpauschale)}",
            f"{eur(gewinn_teilfreistellung)}",
            f"{eur(gewinn_nach_verlusttopf)}",
            f"{eur(verlusttopf_nach_verkauf)}",
            f"{eur(gewinn_steuerpflichtig)}",
            f"{eur(max(0, freibetrag - gewinn_nach_verlusttopf))}",
            f"{eur(steuer)}",
            f"{eur(netto)}"
        ]
    })

    st.dataframe(steuer_df, use_container_width=True)

    # -------------------------------
    # Vorabpauschale
    # -------------------------------

    st.markdown("### Berücksichtigte Vorabpauschale")

    # st.caption("Vorabpauschale pro Anteil und Jahr")

    vorab_display = vorabpauschale.rename(columns={
        "jahr": "Kalenderjahr",
        "vorabpauschale_stueck": "VAP/Anteil (€)"
    })

    vorab_display["VAP/Anteil (€)"] = (
        vorab_display["VAP/Anteil (€)"]
        .map(lambda x: f"{x:.8f}".replace(".", ","))
    )
    

    st.markdown("""
        Die Tabelle zeigt die jährlich angesetzte Vorabpauschale (VAP) pro Anteil. Sie wird aber nur anteilig pro Jahr berücksichtigt.
        Dieser Wert reduziert den steuerpflichtigen Gewinn beim Verkauf, da darauf bereits Steuer gezahlt wurde.
        """)

    st.dataframe(vorab_display, use_container_width=True)


@st.cache_data
def berechne_vorabpauschalen_df(kursdaten):

    basiszins_df = pd.read_csv("basiszins.csv")

    ergebnisse = []

    for jahr in kursdaten["jahr"].unique():

        if jahr not in basiszins_df["jahr"].values or jahr == datetime.today().year:
            continue


        jahr_daten = kursdaten[kursdaten["jahr"] == jahr]
        folgejahr_daten = kursdaten[kursdaten["jahr"] == jahr + 1]


        preis_1_jan = jahr_daten.iloc[0]["preis_1_jan"]
        preis_31_dez = folgejahr_daten.iloc[0]["preis_1_jan"] if not folgejahr_daten.empty else jahr_daten.iloc[-1]["preis_1_jan"]

        wertsteigerung = max(0, preis_31_dez - preis_1_jan)

        basiszins = basiszins_df.loc[
            basiszins_df["jahr"] == jahr, "basiszins"
        ].values[0]

        basisertrag = preis_1_jan * basiszins/100 * 0.7 # gesetzliche konstante

        vorabpauschale = min(wertsteigerung, basisertrag)

        ergebnisse.append({
            "jahr": jahr,
            "vorabpauschale_stueck": vorabpauschale 
        })

    # erstelle ein leeres df mit nur spaltennemen

    if not ergebnisse:
        ergebnisse = pd.DataFrame(columns=["jahr", "vorabpauschale_stueck"])
    else:
        ergebnisse = pd.DataFrame(ergebnisse)

    return ergebnisse

@st.cache_data(ttl=3600)
def erstelle_kaufhistorie_aus_sparplan(sparplan_data, ticker):

    ticker_obj = yf.Ticker(ticker)

    kaufhistorie = []

    # frühestes Startdatum und spätestes Enddatum bestimmen
    start_global = pd.to_datetime(sparplan_data["Startdatum"]).min()
    end_global = pd.to_datetime(sparplan_data["Enddatum"]).max()

    # einmal alle Kursdaten laden
    kursdaten = ticker_obj.history(start=start_global, end=end_global + pd.Timedelta(days=7))

    kursdaten.index = kursdaten.index.tz_localize(None)

    for _, row in sparplan_data.iterrows():

        startdatum = pd.to_datetime(row["Startdatum"])
        enddatum = pd.to_datetime(row["Enddatum"])
        rate = row["Sparplanrate"]
        ausfuehrungstag = int(row["Ausführungstag"])

        if pd.isna(startdatum) or pd.isna(enddatum) or pd.isna(rate):
            continue

        # erstes Ausführungsdatum bestimmen
        if startdatum.day <= ausfuehrungstag:
            aktuelles_datum = startdatum.replace(day=ausfuehrungstag)
        else:
            aktuelles_datum = (startdatum + pd.DateOffset(months=1)).replace(day=ausfuehrungstag)

        while aktuelles_datum <= enddatum:

            # nächsten Handelstag finden
            daten = kursdaten[kursdaten.index >= aktuelles_datum]

            if daten.empty:
                break

            # kurs = daten["Close"].iloc[0]
            kurs = (daten["Open"].iloc[0] + daten["Close"].iloc[0]) / 2
            kaufdatum_real = daten.index[0]

            anzahl = rate / kurs

            kaufhistorie.append({
                "Anzahl": anzahl,
                "Preis": kurs,
                "Kaufdatum": kaufdatum_real
            })

            aktuelles_datum += pd.DateOffset(months=1)

    return pd.DataFrame(kaufhistorie)


def footer(canvas, doc):
    canvas.saveState()

    canvas.setFont("Helvetica", 9)

    text = "Berechnet mit etfsteuerrechner.de – Angaben ohne Gewähr."
    x = 2 * cm
    y = 1.5 * cm

    canvas.drawString(x, y, text)

    canvas.linkURL(
        "https://www.etfsteuerrechner.de",
        (x, y, x + 200, y + 10),
        relative=0
    )

    canvas.restoreState()


def create_pdf(
    anzahl_verkaufen, max_anteile, bereits_verkauft,
    brutto, gewinn, gewinn_teilfreistellung,
    gewinn_nach_vorabpauschale, gewinn_nach_verlusttopf,
    gewinn_steuerpflichtig, steuer, netto,
    gesamtkosten, vorabpauschale, aktueller_kurs, freibetrag, 
    etf_name, verlusttopf_nach_verkauf, gesamte_vorabpauschale, 
    teilfreistellung_quote, kirchensteuer
):

    aktueller_besitz = max_anteile - bereits_verkauft
    gesamtwert = aktueller_besitz * aktueller_kurs
    durchschnittlicher_kaufpreis = gesamtkosten / max_anteile if max_anteile else 0

    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph(
            '<link href="https://www.etfsteuerrechner.de">etfsteuerrechner.de</link> – Ergebnis',
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 20))

    # ---------------------------------------------------
    # Überblick Position
    # ---------------------------------------------------

    elements.append(Paragraph("Überblick Ihrer Position (vor Verkauf)", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>ETF:</b> {etf_name}", styles["Normal"]))

    elements.append(
        Paragraph(
            f"<font size=9>"
            f"Teilfreistellungsquote: <b>{teilfreistellung_quote * 100:.2f} %</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Kirchensteuer: <b>{kirchensteuer}</b>"
            f"</font>",
            styles["Normal"]
        )
    )


    elements.append(Spacer(1, 6))

    ergebnis_data = [
        [
            "Anzahl Anteile im Besitz",
            "Kurs bei Verkauf",
            "Gesamtwert der Anteile"
        ],
        [
            f"{anteil(aktueller_besitz)}",
            f"{eur(aktueller_kurs)}",
            f"{eur(gesamtwert)}"
        ]
    ]

    ergebnis_table = Table(ergebnis_data)

    ergebnis_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
    ]))

    elements.append(ergebnis_table)
    elements.append(Spacer(1, 8))

    # Zusatzinfos
    elements.append(
        Paragraph(
            f"<font size=9>"
            f"Gekaufet Anteile: <b>{anteil(max_anteile)}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Davon verkauft: <b>{anteil(bereits_verkauft)}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Durchschnittlicher Kaufpreis: <b>{eur(durchschnittlicher_kaufpreis)}</b>"
            f"</font>",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 20))

    # ---------------------------------------------------
    # Verkaufsübersicht
    # ---------------------------------------------------

    elements.append(Paragraph("Infos über Verkauf", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    verkauf_data = [
        [
            "Anzahl zu verkaufender Anteile",
            "Brutto Verkaufserlös",
            "Netto nach Steuern"
        ],
        [
            f"{anteil(anzahl_verkaufen)}",
            f"{eur(brutto)}",
            f"{eur(netto)}"
        ]
    ]

    verkauf_table = Table(verkauf_data)

    verkauf_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
    ]))

    elements.append(verkauf_table)
    elements.append(Spacer(1, 12))

    # Zusatzinfos Verkauf
    elements.append(
        Paragraph(
            f"<font size=9>"
            f"Gewinn aus Verkauf: <b>{eur(gewinn)}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Ungenutzter Sparerpauschbetrag: <b>{eur(max(0, freibetrag - gewinn_nach_verlusttopf))}</b>"
            f"</font>",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<font size=9>"
            f"Allgemeiner Verlusttopf nach Verkauf: <b>{eur(verlusttopf_nach_verkauf)}</b>"
            f"</font>",
            styles["Normal"]
        )
    )


    elements.append(Spacer(1, 20))

    # ---------------------------------------------------
    # Steuerberechnung
    # ---------------------------------------------------

    elements.append(Paragraph("Steuerberechnung", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    steuer_data = [
        ["Berechnungsschritt", "Betrag"],
        ["Anzahl zu verkaufender Anteile", f"{anteil(anzahl_verkaufen)}"],
        ["Kurs bei Verkauf", f"{eur(aktueller_kurs)}"],
        ["Brutto Verkaufserlös", eur(brutto)],
        ["Gewinn vor Steuern", eur(gewinn)],
        ["Abzuziehende Vorabpauschale", eur(gesamte_vorabpauschale)],
        ["Gewinn nach Abzug Vorabpauschale", eur(gewinn_nach_vorabpauschale)],
        ["Gewinn nach Teilfreistellung", eur(gewinn_teilfreistellung)],
        ["Gewinn nach Verlustverrechnung", eur(gewinn_nach_verlusttopf)],
        ["Neuer Verlusttopf", eur(verlusttopf_nach_verkauf)],
        ["Gewinn nach Sparerpauschbetrag", eur(gewinn_steuerpflichtig)],
        ["Ungenutzter Sparerpauschbetrag", eur(max(0, freibetrag - gewinn_nach_verlusttopf))],
        # ["Steuerpflichtiger Gewinn", eur(gewinn_steuerpflichtig)],
        ["Zu zahlende Steuer", eur(steuer)],
        ["Netto nach Steuern", eur(netto)],
    ]

    steuer_table = Table(steuer_data, colWidths=[280,120])

    steuer_table.setStyle(TableStyle([
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),   # ganze Betrag-Spalte rechts
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
    ]))

    elements.append(steuer_table)
    elements.append(Spacer(1, 10))



    elements.append(Spacer(1, 20))

    # ---------------------------------------------------
    # Vorabpauschale Tabelle
    # ---------------------------------------------------

    if vorabpauschale is not None and len(vorabpauschale) > 0:

        elements.append(Paragraph("Vorabpauschale pro Anteil", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        data = [["Kalenderjahr", "Vorabpauschale pro Anteil"]]

        for _, row in vorabpauschale.iterrows():
            data.append([
                f"{row['jahr']:.0f}",
                f"{row['vorabpauschale_stueck']:.8f}".replace(".", ",")
            ])

        table = Table(data, colWidths=[150,200])

        table.setStyle(TableStyle([
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),   # ganze Betrag-Spalte rechts
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ]))


        elements.append(table)

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    doc.build(
        elements,
        onFirstPage=footer,
        onLaterPages=footer
    )


    buffer.seek(0)

    return buffer


@st.cache_data(ttl=3600)
def lade_etf_info(ticker):
    ticker_obj = yf.Ticker(ticker)
    return ticker_obj.info


@st.cache_data(ttl=3600)
def lade_preis(ticker: str):
    ticker_obj = yf.Ticker(ticker)
    return ticker_obj.fast_info["lastPrice"]
