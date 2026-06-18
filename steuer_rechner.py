import pandas as pd
import funktionen
import streamlit as st
import requests
import yfinance as yf
from datetime import datetime
from datetime import date
from streamlit_searchbox import st_searchbox



st.set_page_config(
    page_title="ETF Steuer Rechner",
    layout="wide",
    initial_sidebar_state="collapsed"
)

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display:none;}
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# st.caption("Kostenloser ETF Steuer Rechner für Deutschland (FIFO, Vorabpauschale, Teilfreistellung)")

st.markdown("""
## ETF Steuer Rechner - [etfsteuerrechner.de](https://www.etfsteuerrechner.de)

*Hinweis: Die Berechnungen dienen nur zur unverbindlichen Orientierung und stellen keine steuerliche Beratung dar.*

#### Was kann dieser Rechner?
            
• steuerfrei verkaufbare Anteile ermitteln
            
• Anteile für gewünschten Netto‑Betrag bestimmen
            
• Steuer beim ETF‑Verkauf berechnen

Der Rechner berücksichtigt:
FIFO, Teilfreistellung, Vorabpauschale, Verlusttopf und Sparerpauschbetrag.
            
Mehr Informationen auf <a href="https://www.etfsteuerrechner.de" target="_blank">etfsteuerrechner.de</a>
            
---
        
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def suche_etf(searchterm: str):

    if len(searchterm) < 2:
        return []

    url = "https://query2.finance.yahoo.com/v1/finance/search"

    headers = {"User-Agent": "Mozilla/5.0"}

    params = {
        "q": searchterm,
        "quotesCount": 10,
        "newsCount": 0
    }

    r = requests.get(url, headers=headers, params=params, timeout=5)
    data = r.json()

    results = []

    for q in data["quotes"]:
        if q.get("quoteType") in ["ETF", "EQUITY"]:
            results.append(f"{q.get('shortname', q['symbol'])} ({q['symbol']})")

    return results

@st.cache_data(ttl=600)
def lade_kursdaten(ticker, startjahr):

    ticker_obj = yf.Ticker(ticker)

    kurs_data = ticker_obj.history(start=f"{startjahr}-01-01")

    if kurs_data.empty:
        st.warning("Die Kursdaten konnten nicht geladen werden. Bitte versuchen Sie es erneut. Falls das Problem weiterhin besteht, nutzen Sie die manuelle Eingabeoption.")
        st.stop()

    kurs_data["jahr"] = kurs_data.index.year

    jahresstart = kurs_data.groupby("jahr").first()

    jahresstart = jahresstart.loc[startjahr:]

    jahresstart = jahresstart[["Close"]]

    jahresstart = jahresstart.reset_index()

    jahresstart.columns = ["jahr", "preis_1_jan"]

    return jahresstart



eingabe_optionen = st.selectbox("Wie möchten Sie Ihre Daten eingeben?", ["CSV‑Export von Trade Republic", "ETF Suche", "Manuelle Eingabe"])

st.markdown("""
• **CSV‑Export:** Laden Sie eine CSV‑Exportdatei von Trade Republic hoch, um Ihre Transaktionen automatisch zu importieren.

• **ETF‑Suche:** Wählen Sie Ihren ETF über die Suche aus. Sparpläne können automatisch generiert werden, und die Kursdaten für die Vorabpauschale werden automatisch geladen.

• **Manuell:** Geben Sie alle Daten selbst ein.

*Hinweis:* Bei der ETF‑Suche und der manuellen Eingabe können Sie Ihre Daten anschließend als CSV herunterladen. So können Sie sie bei einer späteren Berechnung wieder hochladen, ohne alles erneut eingeben zu müssen.
""")

if eingabe_optionen == "Manuelle Eingabe":
    aktueller_kurs = st.number_input("Verkaufskurs pro Anteil (€)", value=100.00, format="%.2f")
    etf_name = "Unbekannt"
elif eingabe_optionen == "CSV‑Export von Trade Republic":
    st.write("Hinweis zum CSV‑Import: Sie können eine CSV‑Exportdatei aus Trade Republic hochladen, um Ihre Transaktionen automatisch einzulesen. Die Datei wird ausschließlich zur Durchführung der Berechnung verwendet und nicht dauerhaft gespeichert. Die Verarbeitung erfolgt nur für die Dauer der Berechnung. Bitte überprüfen Sie die importierten Daten sorgfältig. Änderungen am Exportformat des Brokers oder unvollständige Daten können zu Abweichungen in der Berechnung führen. Trade Republic ist eine Marke der Trade Republic Bank GmbH. Dieses Tool steht in keiner Verbindung zu Trade Republic und wird nicht von Trade Republic bereitgestellt oder unterstütztt.")
    
    trade_republic_file = st.file_uploader("CSV‑Import für Trade Republic Exportdateien", type="csv", help="CSV-Datei von trade republic hochladen.")


    if not trade_republic_file:
        st.warning("Bitte laden Sie eine CSV-Datei hoch, um fortzufahren. Es werden keine persönlichen Daten gespeichert.")
        st.stop()

    entry_df = pd.read_csv(trade_republic_file)

    # sicherstellen, dass die notwendigen spalten vorhanden sind
    if not set(["datetime", "type", "symbol", "asset_class", "shares", "price"]).issubset(entry_df.columns):
        st.warning("Die hochgeladene CSV-Datei entspricht nicht dem erwarteten Format. Bitte stellen Sie sicher, dass die Datei richtig von Trade Republic exportiert wurde.")
        st.stop()

    # Datum konvertieren
    entry_df["datetime"] = pd.to_datetime(entry_df["datetime"], errors="coerce")

    # Nur Käufe von Wertpapieren
    kaeufe = entry_df[
        (entry_df["type"] == "BUY") &
        (entry_df["asset_class"].isin(["ETF", "STOCK", "FUND"]))
    ]

    if kaeufe.empty:
        st.warning("In der CSV wurden keine ETF- oder Aktienkäufe gefunden.")
        st.stop()

    # vorhandene ETFs/Aktien sammeln
    etf_liste = (
        kaeufe[["symbol", "name"]]
        .dropna()
        .drop_duplicates()
    )

    optionen = [
        f"{row['name']} ({row['symbol']})"
        for _, row in etf_liste.iterrows()
    ]

    auswahl = st.selectbox(
        "Gefundene ETFs/Wertpapiere in der CSV",
        optionen,
        help="Wählen Sie das Wertpapier aus, für das die Berechnung durchgeführt werden soll."
    )

    etf_name = auswahl

    ticker = auswahl.rsplit("(", 1)[-1].replace(")", "")

    ticker_obj = yf.Ticker(ticker)

    try:
        aktueller_kurs = ticker_obj.fast_info["lastPrice"]
        st.success(f"Aktueller Marktpreis für {auswahl}: {aktueller_kurs:.2f} €. Dieser Wert wird als Verkaufskurs für die Berechnung verwendet.")

        kursoptionen = st.checkbox("Verkaufskurs manuell festlegen", help="Aktivieren Sie diese Option, um einen eigenen Verkaufskurs zu simulieren. Dies ist nützlich, wenn Sie berechnen möchten, wie sich Steuern bei einem zukünftigen Kurs verändern.")

        if kursoptionen:
            aktueller_kurs = st.number_input("Verkaufskurs (€)", value=100.00, format="%.2f", help="Aktueller Verkaufskurs eines ETF-Anteils. Dieser Wert bestimmt den Erlös beim Verkauf. Wenn Sie einen ETF über die Suche auswählen, wird der Kurs automatisch geladen. Alternativ können Sie einen eigenen Verkaufskurs eingeben.")
    except:
        st.warning("Der aktuelle Kurs konnte nicht automatisch geladen werden.")
        aktueller_kurs = st.number_input(
            "Verkaufskurs pro Anteil (€)",
            value=100.0,
            format="%.2f"
        )

        data = pd.DataFrame({
        "Anzahl": [],
        "Preis": [],
        "Kaufdatum": []
    })

    # nehme jede zeile die mit dem ausgewählten ticker übereinstimmt und füge sie der datentabelle hinzu
    kaeufe_ticker = entry_df[
        (entry_df["symbol"] == ticker) &
        (entry_df["type"] == "BUY")
    ]

    # Datum konvertieren
    kaeufe_ticker["datetime"] = pd.to_datetime(
        kaeufe_ticker["datetime"], errors="coerce"
    ).dt.tz_localize(None)


    # Daten übernehmen
    data = pd.DataFrame({
        "Anzahl": kaeufe_ticker["shares"],
        "Preis": kaeufe_ticker["price"],
        "Kaufdatum": kaeufe_ticker["datetime"]
    }).reset_index(drop=True)

    st.write("Erkannte Käufe aus der CSV:")
    st.dataframe(data)

    # sammele alle vekäufe dieser aktie 
    #addiere alle um eine anzahl verkaufter anteile zu bekommen
    verkaeufe_ticker = entry_df[
        (entry_df["symbol"] == ticker) &
        (entry_df["type"] == "SELL")
    ]

    # Summe der verkauften Anteile
    bereits_verkauft = verkaeufe_ticker["shares"].sum()

    st.success(f"Anzahl bereits verkaufter Anteile: {bereits_verkauft:.5f}".replace(".", ","))

    upload = "Trade Republic CSV Import"

    thesaurierend = not ((entry_df["type"] == "DIVIDEND") & (entry_df["symbol"] == ticker)).any()

else:
    auswahl = st_searchbox(
        suche_etf,
        placeholder="ETF suchen (Name, ISIN oder Ticker)",
        key="etf_search"
    )

    if auswahl:

        ticker = auswahl.split("(")[-1].replace(")", "")

        ticker_obj = yf.Ticker(ticker)

        try:
            # info = ticker_obj.info
            info = funktionen.lade_etf_info(ticker)
            name = info.get("shortName") or info.get("longName") or ticker
            isin = info.get("isin")
            if isin:
                etf_name = f"{name} ({isin})"
            else:
                etf_name = name
        except:
            etf_name = ticker

        try:
            preis = funktionen.lade_preis(ticker)
            # preis = ticker_obj.fast_info["lastPrice"]
            kurs_ändern = True
        except:
            st.warning("Der aktuelle Kurs konnte nicht geladen werden. Bitte geben Sie den Kurs manuell ein.")
            kurs_ändern = False
            kursoptionen = True

    else:
        st.warning("Bitte wählen Sie einen ETF aus, um den aktuellen Kurs automatisch zu laden, oder aktivieren Sie die Option 'Verkaufskurs manuell festlegen', um einen eigenen Kurs einzugeben.")
        st.stop()

    if kurs_ändern:
        kursoptionen = st.checkbox("Verkaufskurs manuell festlegen", help="Aktivieren Sie diese Option, um einen eigenen Verkaufskurs zu simulieren. Dies ist nützlich, wenn Sie berechnen möchten, wie sich Steuern bei einem zukünftigen Kurs verändern.")

    if kursoptionen:
        aktueller_kurs = st.number_input("Verkaufskurs (€)", value=100.00, format="%.2f", help="Aktueller Verkaufskurs eines ETF-Anteils. Dieser Wert bestimmt den Erlös beim Verkauf. Wenn Sie einen ETF über die Suche auswählen, wird der Kurs automatisch geladen. Alternativ können Sie einen eigenen Verkaufskurs eingeben.")
        if kurs_ändern:
            st.write(f"Aktueller Marktpreis: {preis:.2f}€")
    else:
        aktueller_kurs = preis
        st.success(f"Aktueller Marktpreis: {aktueller_kurs:.2f}€. Dieser Wert wird als Verkaufskurs für die Berechnung verwendet.")

if aktueller_kurs < 0:
    st.warning("Bitte geben Sie einen gültigen aktuellen Kurs ein.")
    st.stop()

if not eingabe_optionen == "CSV‑Export von Trade Republic":
    thesaurierend = st.checkbox("Thesaurierender ETF", value = True, help="Aktivieren Sie diese Option, wenn es sich bei Ihrem ETF um einen thesaurierenden ETF handelt. Bei thesaurierenden ETFs wird die Vorabpauschale relevant, da sie jährlich von der Bank berechnet und von den zu zahlenden Steuern abgezogen wird. Bei ausschüttenden ETFs entfällt die Vorabpauschale.")

freibetrag = st.number_input("Noch verfügbarer Sparerpauschbetrag (€)", value=1000.00, min_value=0.00, max_value=2000.00, help="Noch verfügbarer Sparerpauschbetrag für das aktuelle Jahr. Kapitalerträge bis zu diesem Betrag bleiben steuerfrei. In Deutschland beträgt der maximale Sparerpauschbetrag derzeit 1000€ pro Person.")
if freibetrag < 0:
    st.warning("Bitte geben Sie einen gültigen Freibetrag ein.")
    st.stop()

verlusttopf = st.number_input("Allgemeiner Verlusttopf (€)", value=0.00, min_value=0.00, help="Wenn Sie früher Wertpapiere mit Verlust verkauft haben, speichert Ihre Bank diese Verluste im sogenannten Allgemeinen Verlusttopf. Diese können mit Gewinnen verrechnet werden.")
if verlusttopf < 0:
    st.warning("Bitte geben Sie einen gültigen Verlusttopf ein.")
    st.stop()

teilfreistellung = st.checkbox("Teilfreistellung für Aktien-ETFs (30%)", value=True, help="Aktien-ETFs mit mindestens 51% Aktienanteil haben eine steuerliche Teilfreistellung. 30% der Gewinne sind steuerfrei, sodass nur 70% des Gewinns versteuert werden.")
Solidaritätszuschlag = st.checkbox("Solidaritätszuschlag (5,5%)", value=True, help="Der Solidaritätszuschlag beträgt 5,5% der Abgeltungssteuer. Viele Banken führen ihn automatisch ab. Deaktivieren Sie diese Option nur, wenn er auf Ihre Kapitalerträge nicht angewendet wird.")
kirchensteuer = st.checkbox("Kirchensteuerpflichtig", help="Wenn Kirchensteuerpflicht besteht, erhöht sich die Steuer auf Kapitalerträge. Der genaue Satz hängt vom Bundesland ab.")


if kirchensteuer:
    kirchensteuer_bundesland = st.selectbox(
        "Kirchensteuersatz",
        options=["Bayern / Baden-Württemberg (8%)", "Andere (9%)"],
        index=1,
        help="Kirchensteuer auf Kapitalerträge beträgt 8% (Bayern, Baden-Württemberg) oder 9% (übrige Bundesländer)."
    )

    kirchensteuer_bundesland = 0.09 if kirchensteuer_bundesland == "Andere (9%)" else 0.08

if eingabe_optionen == "Manuelle Eingabe":
    upload = st.selectbox(
            "Kaufhistorie eingeben",
            options=["CSV hochladen", "Käufe manuell eingeben"],
            index=0, 
            help="Laden Sie eine CSV-Datei mit Ihren ETF-Käufen hoch. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten sind essentiell für die Steuerberechnung."
        )
elif eingabe_optionen == "ETF Suche":
    upload = st.selectbox(
            "Kaufhistorie eingeben",
            options=["automatische Eingabe für Sparpläne", "CSV hochladen", "Käufe manuell eingeben"],
            index=0, 
            help="Laden Sie eine CSV-Datei mit Ihren ETF-Käufen hoch. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten sind essentiell für die Steuerberechnung."
        )
elif eingabe_optionen == "CSV‑Export von Trade Republic":
    upload = "Trade Republic CSV Import"


if upload == "Käufe manuell eingeben":
    st.write("ETF-Käufe manuell eingeben")

    data = pd.DataFrame({
        "Anzahl": [None],
        "Preis": [None],
        "Kaufdatum": [None]
    })

    data = st.data_editor(
        data,
        num_rows="dynamic",
        column_config={
            "Anzahl": st.column_config.NumberColumn(
                "Anzahl",
                help="Anzahl der gekauften ETF-Anteile in dieser Transaktion. (z.B. 10.2)",
                format="%.8f"
            ),
            "Preis": st.column_config.NumberColumn(
                "Preis (€)",
                help="Kaufpreis pro Anteil zum Zeitpunkt der Transaktion. (z.B. 105.34)",
                format="%.8f"
            ),
            "Kaufdatum": st.column_config.DateColumn(
                "Kaufdatum",
                help="Datum, an dem die ETF-Anteile gekauft wurden. Dieses Datum bestimmt die Reihenfolge der Verkäufe nach dem steuerlichen FIFO-Prinzip, sowie die Anteile der Vorabpauschale. (Format: YYYY-MM-DD)",
            ),
        },
        use_container_width=True
    )

    # option einfügen das als csv zu downloaden
    st.write("Es wird empfohlen die Daten als CSV herunterzuladen, um sie später wieder hochladen zu können, ohne sie erneut eingeben zu müssen.")
    st.download_button(
        label="Ihre Kaufdaten als CSV herunterladen",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="Persönliche_ETF_Käufe.csv",
        mime="text/csv"
    )

    if data.isnull().values.any():
        st.warning("Bitte füllen Sie alle Felder aus, um fortzufahren oder laden Sie eine CSV-Datei mit den Kaufdaten hoch. Falls Sie eine Zeile löschen möchten, klicken Sie links auf den Haken der entsprechenden Zeile und drücken anschließend auf den Mülleimer oben rechts in der Ecke der Tabelle.")
        st.stop()


elif upload == "CSV hochladen":

    uploaded_file = st.file_uploader("CSV hochladen", type="csv", help="CSV-Datei mit Ihren ETF-Käufen hochladen. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten werden genutzt, um die Verkaufsreihenfolge nach dem FIFO-Prinzip zu bestimmen und den steuerpflichtigen Gewinn zu berechnen. Falls Sie keine CSV-Datei haben, können Sie Ihre Käufe auch manuell eingeben.")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)

        data["Kaufdatum"] = pd.to_datetime(data["Kaufdatum"], errors="coerce")

        st.write("Hier können Sie Ihre Käufe manuell ergänzen oder korrigieren. Sie können Zeilen löschen indem Sie links auf den haken drücken und anschließend aud sen mülleimer oben rechts in der ecke der Tabelle drücken")
        st.write("Es wird empfohlen die Daten als CSV herunterzuladen, um sie später wieder hochladen zu können, ohne sie erneut eingeben zu müssen.")

        data = st.data_editor(
            data,
            num_rows="dynamic",
            hide_index=True,
                    column_config={
            "Anzahl": st.column_config.NumberColumn(
                "Anzahl",
                help="Anzahl der gekauften ETF-Anteile in dieser Transaktion. (z.B. 10.2)",
                format="%.5f"
            ),
            "Preis": st.column_config.NumberColumn(
                "Preis (€)",
                help="Kaufpreis pro Anteil zum Zeitpunkt der Transaktion. (z.B. 105.34)",
                format="%.2f"
            ),
            "Kaufdatum": st.column_config.DateColumn(
                "Kaufdatum",
                help="Datum, an dem die ETF-Anteile gekauft wurden. Dieses Datum bestimmt die Reihenfolge der Verkäufe nach dem steuerlichen FIFO-Prinzip, sowie die Anteile der Vorabpauschale. (Format: YYYY-MM-DD)",
            ),
        },
            use_container_width=True
        )

        data = data.sort_values("Kaufdatum").reset_index(drop=True)

        st.download_button(
            label="Daten als CSV herunterladen",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name="Persönliche_ETF_Käufe.csv",
            mime="text/csv"
        )


    else:
        st.warning("Bitte laden Sie eine CSV-Datei hoch mit den Spalten Kaufdatum, Anzahl und Preis. Es werden keine persönlichen Daten gespeichert.")
        data = pd.DataFrame({
            "Anzahl": [],
            "Preis": [],
            "Kaufdatum": []
        })
        st.stop()

elif upload == "automatische Eingabe für Sparpläne":

    # st.write("Hier können Sie Eckdaten genutzter Sparpläne eingeben. bei Änderungen müssen sie eine neue Zeile ergänzen und die Änderung wie ein neuen Sparplan ansehen. Beachten Sie, dass diese automatische Schätzung eher ungenau ist, da die genauen kurse beim Kauf nicht bekannt sind. Später können Sie die Daten noch bearbeiten oder ergänzen.")
    st.write("""
    Hier können Sie die Eckdaten Ihrer genutzten Sparpläne eingeben. 
    **Wichtig bei Anpassungen Ihres Sparplans:** Falls sich Ihre Sparrate oder der Ausführungstag im Laufe der Zeit geändert haben, legen Sie dafür bitte einfach einen neuen Eintrag mit dem entsprechenden Startdatum an.
    *Hinweis zur Genauigkeit:* Da der genaue Ausführungszeitpunkt (Uhrzeit) variiert, nutzt diese Schätzung den durchschnittlichen Kurs des Kauftages. Keine Sorge: Alle generierten Kaufdaten können Sie im nächsten Schritt flexibel bearbeiten oder korrigieren.
    """)
    if "sparplaene" not in st.session_state:
        st.session_state.sparplaene = []

    st.write("Geben Sie hier ihre Daten für Ihren Sparplan ein und fügen Sie ihn mit dem Button 'Sparplan hinzufügen' der Liste Ihrer Sparpläne hinzu. Sie können beliebig viele Sparpläne eingeben. ")

    default_start = date.today().replace(year=date.today().year - 1)

    with st.form("sparplan_form"):

        start = st.date_input("Startdatum", value=default_start, max_value=date.today(), help="Startdatum Ihres Sparplans. Das Datum des ersten Kaufs bestimmt die Reihenfolge der Verkäufe nach dem steuerlichen FIFO-Prinzip, sowie die Anteile der Vorabpauschale.")
        ende = st.date_input("Enddatum", value=date.today(), help="Das Datum des letzten Kaufs.")
        rate = st.number_input("Sparplanrate (€)", value=100.00, min_value=0.00, step=10.0, help="Monatliche Sparplanrate in Euro.")
        tag = st.number_input("Ausführungstag", min_value=1, max_value=28, step=1, help="Tag des Monats, an dem der Sparplan ausgeführt wird. (z. B. 1 oder 15) ")

        submitted = st.form_submit_button("Sparplan hinzufügen")

        if submitted:
            st.session_state.sparplaene.append({
                "Startdatum": start,
                "Enddatum": ende,
                "Sparplanrate": rate,
                "Ausführungstag": tag
            })
            st.success("Sparplan gespeichert. Sie können einen weiteren hinzufügen.")

    if st.session_state.sparplaene:
        st.write("### Ihre aktiven Sparpläne:")
        
        for index, plan in enumerate(st.session_state.sparplaene):
            # Container hält alles kompakt zusammen
            with st.container():
                # [11, 1] sorgt dafür, dass 92% für Text und 8% für den Button reserviert sind
                col_text, col_btn = st.columns([11, 1], gap="small", vertical_alignment="center")
                
                with col_text:
                    # Ganz normaler Text ohne 'nowrap' – bricht bei Bedarf sauber um
                    st.markdown(
                        f"Monatlich **{plan['Sparplanrate']:.2f} €** am **{plan['Ausführungstag']}.** des Monats "
                        f"(vom {plan['Startdatum']} bis {plan['Enddatum']})"
                    )
                    
                with col_btn:
                    # Der Button bleibt stur in seiner rechten Spalte fixiert
                    if st.button("🗑️", key=f"del_{index}", help="Löschen", use_container_width=True):
                        st.session_state.sparplaene.pop(index)
                        st.success("Gelöscht!")
                        st.rerun()
            
            # Die super-schmale Trennlinie direkt darunter
            st.markdown("<hr style='margin: 4px 0px; height: 1px; border: none; background-color: rgba(128, 128, 128, 0.3);'>", unsafe_allow_html=True)


    sparplan_data = pd.DataFrame(st.session_state.sparplaene)

    if sparplan_data.isnull().all(axis=1).all():
        st.warning("Bitte fügen Sie mindestens einen Sparplan hinzu.")
        st.stop()

    if sparplan_data.isnull().values.any():
        st.warning("Es dürfen keine leeren Werte vorhanden sein. Bitte füllen Sie alle Felder aus oder löschen Sie unvollständige Zeilen.")
        st.stop()

    sparplan_data["Startdatum"] = pd.to_datetime(sparplan_data["Startdatum"], errors="coerce")
    sparplan_data["Enddatum"] = pd.to_datetime(sparplan_data["Enddatum"], errors="coerce")

    today = pd.Timestamp.today()

    if (sparplan_data["Ausführungstag"] > 28).any() or (sparplan_data["Ausführungstag"] < 1).any():
        st.warning("Der Ausführungstag muss zwischen 1 und 28 liegen.")
        st.stop()

    if (sparplan_data["Startdatum"] > today).any():
        st.warning("Das Startdatum darf nicht in der Zukunft liegen.")
        st.stop()

    if (sparplan_data["Enddatum"] > today).any():
        st.warning("Das Enddatum darf nicht in der Zukunft liegen.")
        st.stop()

    if (sparplan_data["Enddatum"] < sparplan_data["Startdatum"]).any():
        st.warning("Das Enddatum muss nach dem Startdatum liegen.")
        st.stop()

    if (sparplan_data["Sparplanrate"] <= 0).any():
        st.warning("Waählen Sie eine gültige Sparplanrate größer als 0 aus.")
        st.stop()

    # nutze die daten um mit yahoo die kurse zu finden und die anzahl der gekauften anteile zu berechnen
    data = funktionen.erstelle_kaufhistorie_aus_sparplan(sparplan_data, ticker)

    # if len(data) == 0:
    if data.empty:
        st.warning("Es konnten keine Käufe aus den Sparplänen generiert werden. Bitte überprüfen Sie die eingegebenen Sparplandaten oder geben Sie Ihre Käufe manuell ein.")
        st.stop()
    else:
        st.success(f"Es wurden {len(data)} Käufe aus dem Sparplan / den Sparplänen generiert. Sie können die Daten nun manuell ergänzen oder korrigieren.")

    data = data.sort_values("Kaufdatum")
    data = data.reset_index(drop=True)


    data = st.data_editor(
        data,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Anzahl": st.column_config.NumberColumn(
                "Anzahl",
                help="Anzahl der gekauften ETF-Anteile in dieser Transaktion. (z.B. 10.2)",
                format="%.5f"
            ),
            "Preis": st.column_config.NumberColumn(
                "Preis (€)",
                help="Kaufpreis pro Anteil zum Zeitpunkt der Transaktion. (z.B. 105.34)",
                format="%.2f"
            ),
            "Kaufdatum": st.column_config.DateColumn(
                "Kaufdatum",
                help="Datum, an dem die ETF-Anteile gekauft wurden. Dieses Datum bestimmt die Reihenfolge der Verkäufe nach dem steuerlichen FIFO-Prinzip, sowie die Anteile der Vorabpauschale. (Format: YYYY-MM-DD)",
            ),
        },
        use_container_width=True
    )


    data = data.sort_values("Kaufdatum")
    
    st.write("Es wird empfohlen die Daten als CSV herunterzuladen, um sie später wieder hochladen zu können, ohne sie erneut eingeben zu müssen.")

    st.download_button(
        label="Daten als CSV herunterladen",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="Persönliche_ETF_Käufe.csv",
        mime="text/csv"
    )


# if len(data) == 0:
if data.empty:
    st.warning("Bitte geben Sie mindestens einen ETF-Kauf ein.")
    st.stop()

# checke anzahl datum und preis sind positiv
if (data["Anzahl"] <= 0).any() or (data["Preis"] <= 0).any():
    st.warning("Anzahl und Preis müssen positive Werte sein. Bitte korrigieren Sie die Eingaben.")
    st.stop()

# sorge dafür das kein kaufdatum in der zukunft liegt
data["Kaufdatum"] = pd.to_datetime(data["Kaufdatum"])
data = data.sort_values("Kaufdatum")


if (data["Kaufdatum"] > pd.Timestamp.today()).any():
    st.warning("Kaufdatum darf nicht in der Zukunft liegen. Bitte korrigieren Sie die Eingaben.")
    st.stop()

# wenn irgendwo ein nan ist dann stoppe die berechnung und zeige eine warnung an
if data.isnull().values.any():
    st.warning("Es dürfen keine leeren Werte vorhanden sein. Bitte füllen Sie alle Felder aus oder löschen Sie unvollständige Zeilen.")
    st.stop()

if not eingabe_optionen == "CSV‑Export von Trade Republic":
    bereits_verkauft = st.number_input("Anzahl bereits verkaufter Anteile (für FIFO-Berechnung)", value=0.00000, format="%.5f",help="Gesamtzahl der Anteile, die Sie aus diesem ETF bereits verkauft haben. Der Rechner nutzt diese Information für die FIFO-Berechnung (First-In-First-Out), da steuerlich immer die zuerst gekauften Anteile zuerst verkauft werden.")

max_anteile = data["Anzahl"].sum()

if bereits_verkauft > max_anteile:
    st.warning("Die Anzahl bereits verkaufter Anteile kann nicht größer sein als die insgesamt gekauften Anteile. Bitte korrigieren Sie die Eingabe.")
    st.stop()

if bereits_verkauft < 0:
    st.warning("Bitte geben Sie eine gültige Anzahl bereits verkaufter Anteile ein.")
    st.stop()

if teilfreistellung:
    teilfreistellung_quote = 0.30 # oder null bei nicht-aktien etf
else:
    teilfreistellung_quote = 0.0

if Solidaritätszuschlag:
    steuersatz = 0.26375
else:
    steuersatz = 0.25
if kirchensteuer:
    steuersatz *= (1 + kirchensteuer_bundesland)
else:
    steuersatz = steuersatz

###################################################
# vorabpauschale 
###################################################



if thesaurierend:
    # lade älteste jahr aus hochgeladener csv datei
    aeltestes_jahr = data["Kaufdatum"].dt.year.min()
    startjahr = int(max(aeltestes_jahr, 2018)) # vorabpauschale gibt es erst seit 2018
    # nehme von dem ältesten jahr bis zum aktuellen jahr jeweils den kurs zum 1.1. 
    heute = datetime.today().year 

    if eingabe_optionen == "ETF Suche" or eingabe_optionen == "CSV‑Export von Trade Republic":
        
        jahresstart = lade_kursdaten(ticker, startjahr)

        # lade alle kursdaten vom 1.1. jedes jahres bis heute
        vorabpauschale = funktionen.berechne_vorabpauschalen_df(jahresstart, teilfreistellung_quote)

    elif eingabe_optionen == "Manuelle Eingabe":
        # kursdaten manuell einfügen oder ohne vorabpauschale rechnen lassen

        st.markdown("""
        Die Vorabpauschale ist eine jährliche Mindestbesteuerung für thesaurierende ETFs. 
        Beim Verkauf wird sie vom steuerpflichtigen Gewinn abgezogen, da darauf bereits Steuern gezahlt wurden.
        """)

        ohne_vorabpauschale = st.checkbox("Ohne Vorabpauschale rechnen", value=True, help="Wenn diese Option aktiviert ist, wird keine Vorabpauschale berücksichtigt. Dadurch kann die Steuerberechnung weniger genau sein. Die Vorabpauschale wird normalerweise jährlich von der Bank berechnet und von den zu zahlenden Steuern abgezogen.")

        aktuelles_jahr = datetime.today().year

        if ohne_vorabpauschale or startjahr == aktuelles_jahr:
            vorabpauschale = pd.DataFrame(columns=["jahr", "vorabpauschale_stueck"])
        else:
            jahre = list(range(startjahr, heute + 1))

            jahresstart = pd.DataFrame({
                "jahr": jahre,
                "preis_1_jan": [None] * len(jahre)
            })

            st.write("Bitte geben Sie die Kursdaten zum 1.1. jedes Jahres ein.")

            jahresstart = st.data_editor(
                jahresstart,
                num_rows="fixed",  # keine neuen Zeilen
                hide_index=True,
                column_config={
                    "jahr": st.column_config.NumberColumn(
                        "Jahr",
                        help="Kalenderjahr",
                        disabled=True  # nicht editierbar
                    ),
                    "preis_1_jan": st.column_config.NumberColumn(
                        "Kurs am 1.1. (€)",
                        help="Kurs des ETFs am ersten Handelstag des Jahres. Dieser Wert wird benötigt, um die Vorabpauschale für dieses Jahr zu berechnen. (z.B. 105.34)",
                        format="%.2f"
                    ),
                },
                use_container_width=True
            )

            if jahresstart["preis_1_jan"].isnull().any():
                st.warning("Bitte füllen Sie alle Kursdaten zum 1.1. jedes Jahres aus, um die Vorabpauschale zu berechnen. Sie können die Vorabpauschale auch deaktivieren, wenn Sie diese Daten nicht haben.")
                st.stop()

            vorabpauschale = funktionen.berechne_vorabpauschalen_df(jahresstart, teilfreistellung_quote)
else:
    vorabpauschale = pd.DataFrame(columns=["jahr", "vorabpauschale_stueck"])


berechnungstyp = st.selectbox(
    "Was möchten Sie berechnen?",
    options=["Anteile für gewünschtes Netto berechnen", "Steuerfrei verkaufbare Anteile", "Steuer und Netto für bestimmte Anzahl berechnen"],
    index=1,
    help="Wählen Sie, welche Art von Berechnung durchgeführt werden soll: Steuer für eine bestimmte Anzahl, steuerfrei verkaufbare Anteile oder benötigte Anteile für einen gewünschten Nettoerlös."
)

gesamtkosten = sum(data["Anzahl"] * data["Preis"])

if berechnungstyp == "Steuer und Netto für bestimmte Anzahl berechnen":
    anzahl_verkaufen = st.number_input("Anzahl zu verkaufener Anteile", value=10.00000, format="%.5f", help="Anzahl der ETF-Anteile, die verkauft werden sollen. Der Rechner ermittelt daraus Gewinn, Steuer und Nettoerlös.")

    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    if rest_zu_verkaufen > 0:
        st.error("Nicht genug Anteile vorhanden")
        st.stop()

    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer
    st.markdown("### Ergebnis Ihrer Berechnung")

    
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")
    st.write("Wenn Sie jetzt verkaufen, ergibt sich folgendes Ergebnis:")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Brutto Verkaufserlös", f"{funktionen.eur(brutto)}", help="Der Brutto Verkaufserlös entspricht der Anzahl verkaufter Anteile multipliziert mit dem aktuellen Kurs pro Anteil. Er stellt den Gesamtbetrag dar, bevor Steuern abgezogen werden.")
    col2.metric("Zu zahlende Steuer", f"{funktionen.eur(steuer)}", help="Die zu zahlende Steuer wird mit dem steuerpflichtigen Gewinn (nach Berücksichtigung von Teilfreistellung, Vorabpauschale, Verlusttopf und Sparerpauschbetrag) multipliziert. Sie zeigt den Betrag an, der an Steuern für den Verkauf der angegebenen Anzahl von Anteilen zu zahlen ist.")
    col3.metric("Netto nach Steuern", f"{funktionen.eur(netto)}", help="Der Nettoerlös nach Steuern ist der Betrag, der Ihnen nach Abzug der Steuern vom Brutto Verkaufserlös übrig bleibt. Er berücksichtigt die Teilfreistellung, die Vorabpauschale, den Verlusttopf und den Sparerpauschbetrag.")

    diff_gewinn_vorab = gewinn_teilfreistellung - gesamte_vorabpauschale
    if diff_gewinn_vorab < 0:
        verlusttopf_nach_verkauf = verlusttopf - diff_gewinn_vorab

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig,
        "verlusttopf_nach_verkauf": verlusttopf_nach_verkauf,
    }
    

elif berechnungstyp == "Anteile für gewünschtes Netto berechnen":
    gewolltes_netto = st.number_input("Gewünschtes Netto (€)", value=1000.00, help="Gewünschter Nettoerlös nach Steuern. Der Rechner bestimmt automatisch, wie viele Anteile verkauft werden müssen, um diesen Betrag zu erreichen.")

    anzahl_verkaufen = funktionen.finde_anteile(gewolltes_netto, max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag)
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)

    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer

    if netto < gewolltes_netto - 0.01:
        st.warning("Nicht genug Anteile vorhanden, um das gewünschte Netto zu erreichen. Es werden alle verfügbaren Anteile verkauft.")
        
    st.markdown("### Ergebnis Ihrer Berechnung")
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")
    st.write("Wenn Sie jetzt verkaufen, ergibt sich folgendes Ergebnis:")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Benötigte Anteile", f"{funktionen.anteil(anzahl_verkaufen)}", help="Anzahl der ETF-Anteile, die verkauft werden müssen, um den gewünschten Nettoerlös zu erreichen. Diese Anzahl basiert auf dem FIFO-Prinzip, der Vorabpauschale, der Teilfreistellung und dem verfügbaren Sparerpauschbetrag.")
    col2.metric("Brutto Verkaufserlös", f"{funktionen.eur(brutto)}", help="Der Brutto Verkaufserlös entspricht der Anzahl verkaufter Anteile multipliziert mit dem aktuellen Kurs pro Anteil. Er stellt den Gesamtbetrag dar, bevor Steuern abgezogen werden.")
    col3.metric("Netto nach Steuern", f"{funktionen.eur(netto)}", help="Der Nettoerlös nach Steuern ist der Betrag, der Ihnen nach Abzug der Steuern vom Brutto Verkaufserlös übrig bleibt. Er berücksichtigt die Teilfreistellung, die Vorabpauschale, den Verlusttopf und den Sparerpauschbetrag.")

    diff_gewinn_vorab = gewinn_teilfreistellung - gesamte_vorabpauschale
    if diff_gewinn_vorab < 0:
        verlusttopf_nach_verkauf = verlusttopf - diff_gewinn_vorab

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig,
        "verlusttopf_nach_verkauf": verlusttopf_nach_verkauf,
    }

elif berechnungstyp == "Steuerfrei verkaufbare Anteile":

    anzahl_verkaufen = funktionen.finde_anteile_ohne_steuer(max_anteile-bereits_verkauft, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag)
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer

    st.markdown("### Ergebnis Ihrer Berechnung")
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")
    st.write("Wenn Sie jetzt verkaufen, ergibt sich folgendes Ergebnis:")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Steuerfrei verkaufbare Anteile", f"{funktionen.anteil(anzahl_verkaufen)}", help="Anzahl der ETF-Anteile, die Sie verkaufen können, ohne dass Abgeltungssteuer anfällt. Die Berechnung nutzt Ihren noch verfügbaren Sparerpauschbetrag, mit dem Kapitalerträge bis zu einer bestimmten Höhe pro Jahr steuerfrei bleiben.")
    col2.metric("Nettoerlös", f"{funktionen.eur(netto)}", help="Da keine Steuer anfällt, entspricht der Nettoerlös dem Bruttoerlös.")
    col3.metric("Verbliebender Sparerpauschbetrag", f"{funktionen.eur(max(0, freibetrag - gewinn_nach_verlusttopf))}", help="Der verbleibende Sparerpauschbetrag, der nach dem Verkauf übrig bleibt.")

    diff_gewinn_vorab = gewinn_teilfreistellung - gesamte_vorabpauschale
    if diff_gewinn_vorab < 0:
        verlusttopf_nach_verkauf = verlusttopf - diff_gewinn_vorab

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig,
        "verlusttopf_nach_verkauf": verlusttopf_nach_verkauf,
    }
    
detailierte_darstellung = st.checkbox("Detaillierte Darstellung")

if detailierte_darstellung:
    r = st.session_state.results
    funktionen.detailierte_darstellung(
        r["anzahl_verkaufen"],
        max_anteile,
        bereits_verkauft,
        r["brutto"],
        r["gewinn"],
        r["gewinn_teilfreistellung"],
        r["gewinn_nach_vorabpauschale"],
        r["gewinn_nach_verlusttopf"],
        r["gewinn_steuerpflichtig"],
        r["steuer"],
        r["netto"],
        gesamtkosten,
        vorabpauschale,
        aktueller_kurs,
        r["verlusttopf_nach_verkauf"],
        gesamte_vorabpauschale
    )

if "results" in st.session_state:
    r = st.session_state.results
    pdf = funktionen.create_pdf(
        r["anzahl_verkaufen"], max_anteile, bereits_verkauft,
        r["brutto"], r["gewinn"], r["gewinn_teilfreistellung"],
        r["gewinn_nach_vorabpauschale"], r["gewinn_nach_verlusttopf"],
        r["gewinn_steuerpflichtig"], r["steuer"], r["netto"],
        gesamtkosten, vorabpauschale, aktueller_kurs, freibetrag, etf_name, r["verlusttopf_nach_verkauf"], gesamte_vorabpauschale
    )
    
    st.download_button(
        "Ergebnis als PDF herunterladen",
        pdf,
        "etf_steuer_berechnung.pdf",
        "application/pdf"
    )


