import pandas as pd
import funktionen
import streamlit as st
import requests
import yfinance as yf
from datetime import datetime


# st.caption("Kostenloser ETF Steuer Rechner für Deutschland (FIFO, Vorabpauschale, Teilfreistellung)")

# st.markdown("""
# # ETF Steuer Rechner (Deutschland)

# ---

# ### ETF Steuer beim Verkauf berechnen

# Dieser **ETF Steuer Rechner für Deutschland** hilft Ihnen dabei:

# - zu berechnen, **wie viele ETF-Anteile Sie steuerfrei verkaufen können**
# - herauszufinden, **wie viele Anteile Sie verkaufen müssen, um einen bestimmten Nettobetrag zu erhalten**
# - die **voraussichtliche Steuer beim Verkauf von ETFs** zu berechnen

# Der Rechner eignet sich besonders für Anleger, die ihren **Sparerpauschbetrag optimal nutzen** oder einen ETF-Verkauf planen.

# Für die Berechnung benötigen Sie lediglich Ihre ETF-Käufe (**Anzahl, Preis und Kaufdatum**).

# ---

# ### Welche Steuerregeln werden berücksichtigt?

# Der ETF Steuer Rechner berücksichtigt wichtige steuerliche Regeln für ETFs in Deutschland:

# - **FIFO-Prinzip (First-In-First-Out)** bei Verkäufen  
# - **Teilfreistellung für Aktien-ETFs** (30% steuerfrei)  
# - **Vorabpauschale** bei thesaurierenden ETFs  
# - **Sparerpauschbetrag**  
# - **Verlustverrechnung über den Verlusttopf**

# Damit erhalten Sie eine möglichst realistische Schätzung der Steuer beim Verkauf Ihrer ETF-Anteile.

# ---

# ### Beispiel

# Beispiel:  
# Wenn Sie herausfinden möchten, **wie viele ETF-Anteile Sie verkaufen können, ohne Steuern zu zahlen**, berechnet der Rechner für Sie:

# - die **Anzahl der steuerfrei verkaufbaren Anteile**
# - den **Nettoerlös aus diesem steuerfreien Verkauf**
# - den **verbleibenden Sparerpauschbetrag**

# So können Sie leicht prüfen, wie Sie Ihren **Sparerpauschbetrag optimal ausnutzen**, ohne unnötig Steuern zu zahlen.

# ---

# ### Hinweis

# Die Ergebnisse sind eine **realistische Schätzung** und dienen nur zur Orientierung.  
# In der tatsächlichen Abrechnung Ihrer Bank können leichte Abweichungen entstehen, zum Beispiel durch Rundungen oder unterschiedliche Kursdaten.

# Dieses Tool ersetzt **keine steuerliche Beratung**.

# ---

# ### Datenschutz

# Alle Berechnungen erfolgen direkt in Ihrem Browser.  
# Es werden **keine persönlichen Finanzdaten gespeichert**.

# ---

# # Eingabe Ihrer Daten
# """)



@st.cache_data
def suche_etf(query):
    url = "https://query2.finance.yahoo.com/v1/finance/search"

    headers = {"User-Agent": "Mozilla/5.0"}

    params = {
        "q": query,
        "quotesCount": 10,
        "newsCount": 0
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
    except:
        st.warning("Es gibt aktuell leider Probleme bei der Verbindung zu Yahoo Finance. Bitte versuchen Sie es erneut oder nutzen Sie die manuelle Eingabeoption.")
        st.stop()

    r = requests.get(url, headers=headers, params=params, timeout=5)
    data = r.json()

    results = []

    for q in data["quotes"]:
        if q.get("quoteType") in ["ETF", "EQUITY"]:
            results.append({
                "symbol": q["symbol"],
                "name": q.get("shortname", q["symbol"])
            })

    return results

@st.cache_data(ttl=600)
def lade_kursdaten(ticker, startjahr):

    ticker_obj = yf.Ticker(ticker)

    kurs_data = ticker_obj.history(start=f"{startjahr}-01-01")

    if kurs_data.empty:
        st.warning("Die Kursdaten konnten nicht geladen werden. Bitte geben Sie die Kursdaten manuell ein oder versuchen Sie es später erneut.")
        st.stop()

    kurs_data["jahr"] = kurs_data.index.year

    jahresstart = kurs_data.groupby("jahr").first()

    jahresstart = jahresstart.loc[startjahr:]

    jahresstart = jahresstart[["Close"]]

    jahresstart = jahresstart.reset_index()

    jahresstart.columns = ["jahr", "preis_1_jan"]

    return jahresstart

manuelle_eingabe = st.checkbox("ETF Daten manuell eingeben (ohne automatische Kurse)", help="Aktivieren Sie diese Option, wenn Sie keinen ETF über die Suche auswählen möchten. In diesem Fall müssen aktueller Kurs und historische Kursdaten selbst eingegeben werden.")

if manuelle_eingabe:
    aktueller_kurs = st.number_input("Aktueller Kurs (€)", value=100.00, format="%.2f")
else:
    query = st.text_input("ETF suchen (Name, ISIN oder Börsenkürzel)", help="Geben Sie den Namen, die ISIN oder das Börsenkürzel des ETFs ein. Der Rechner lädt anschließend automatisch den aktuellen Kurs sowie historische Kursdaten zur Berechnung der Vorabpauschale.")

    if len(query) >= 2:

        treffer = suche_etf(query)

        if not treffer:
            st.warning("Es wurden keine passenden ETFs gefunden. Versuchen Sie es mit einer anderen Methode (Name, ISIN oder Börsenkürzel) oder nutzen Sie die manuelle Eingabeoption.")
            st.stop()

        else:

            optionen = [f"{t['name']} ({t['symbol']})" for t in treffer]

            auswahl = st.selectbox("Suchergebnisse", optionen, help="Hier sehen Sie die ETFs, die zu Ihrer Suche passen. Wählen Sie den gewünschten ETF aus, damit der aktuelle Kurs und die historischen Kursdaten automatisch geladen werden. Falls der gewünschte ETF nicht erscheint, versuchen Sie die Suche mit der ISIN oder dem Börsenkürzel oder nutzen Sie die manuelle Eingabeoption.")

            ticker = treffer[optionen.index(auswahl)]["symbol"]

            ticker_obj = yf.Ticker(ticker)

            # preis = ticker_obj.fast_info["lastPrice"]
            try:
                preis = ticker_obj.fast_info["lastPrice"]
            except:
                st.warning("Der aktuelle Kurs konnte nicht geladen werden. Bitte geben Sie den Kurs manuell ein.")
                st.stop()


    else:
        if not manuelle_eingabe:
            st.warning("Bitte geben Sie mindestens 2 Zeichen ein, um nach einem ETF zu suchen oder nutzen Sie die manuelle Eingabe.")
            st.stop()

    kursoptionen = st.checkbox("Verkaufskurs manuell festlegen", help="Aktivieren Sie diese Option, um einen eigenen Verkaufskurs zu simulieren. Dies ist nützlich, wenn Sie berechnen möchten, wie sich Steuern bei einem zukünftigen Kurs verändern.")

    if kursoptionen:
        aktueller_kurs = st.number_input("Verkaufskurs (€)", value=100.00, format="%.2f", help="Aktueller Verkaufskurs eines ETF-Anteils. Dieser Wert bestimmt den Erlös beim Verkauf. Wenn Sie einen ETF über die Suche auswählen, wird der Kurs automatisch geladen. Alternativ können Sie einen eigenen Verkaufskurs eingeben.")
        st.write(f"Aktueller Kurs: {preis:.2f}€")
    else:
        aktueller_kurs = preis
        st.success(f"Aktueller Kurs: {aktueller_kurs:.2f}€")

if aktueller_kurs < 0:
    st.warning("Bitte geben Sie einen gültigen aktuellen Kurs ein.")
    st.stop()

thesaurierend = st.checkbox("Thesaurierender ETF", value = True, help="Aktivieren Sie diese Option, wenn es sich bei Ihrem ETF um einen thesaurierenden ETF handelt. Bei thesaurierenden ETFs wird die Vorabpauschale relevant, da sie jährlich von der Bank berechnet und von den zu zahlenden Steuern abgezogen wird. Bei ausschüttenden ETFs entfällt die Vorabpauschale.")

freibetrag = st.number_input("Noch verfügbarer Sparerpauschbetrag (€)", value=1000.00, help="Noch verfügbarer Sparerpauschbetrag für das aktuelle Jahr. Kapitalerträge bis zu diesem Betrag bleiben steuerfrei. In Deutschland beträgt der maximale Sparerpauschbetrag derzeit 1000€ pro Person.")
if freibetrag < 0:
    st.warning("Bitte geben Sie einen gültigen Freibetrag ein.")
    st.stop()

verlusttopf = st.number_input("Allgemeiner Verlusttopf (€)", value=0.00, help="Allgemeiner Verlusttopf Ihrer Bank. Verluste aus früheren Kapitalanlagen können mit Gewinnen verrechnet werden und reduzieren dadurch die zu zahlende Steuer.")
if verlusttopf < 0:
    st.warning("Bitte geben Sie einen gültigen Verlusttopf ein.")
    st.stop()

teilfreistellung = st.checkbox("Teilfreistellung für Aktien-ETFs (30%)", value=True, help="Aktien-ETFs mit mindestens 51% Aktienanteil haben eine steuerliche Teilfreistellung. 30% der Gewinne sind steuerfrei, sodass nur 70% des Gewinns versteuert werden.")
Solidaritätszuschlag = st.checkbox("Solidaritätszuschlag (5,5%)", value=True, help="Der Solidaritätszuschlag beträgt 5,5% der Abgeltungssteuer. Viele Banken führen ihn automatisch ab. Deaktivieren Sie diese Option nur, wenn er auf Ihre Kapitalerträge nicht angewendet wird.")
kirchensteuer = st.checkbox("Kirchensteuer", help="Wenn Kirchensteuerpflicht besteht, erhöht sich die Steuer auf Kapitalerträge. Der genaue Satz hängt vom Bundesland ab.")


if kirchensteuer:
    kirchensteuer_bundesland = st.selectbox(
        "Kirchensteuersatz",
        options=["Bayern / Baden-Württemberg (8%)", "Andere (9%)"],
        index=1,
        help="Kirchensteuer auf Kapitalerträge beträgt 8% (Bayern, Baden-Württemberg) oder 9% (übrige Bundesländer)."
    )

    kirchensteuer_bundesland = 0.09 if kirchensteuer_bundesland == "Andere (9%)" else 0.08


upload = st.selectbox(
        "Kaufhistorie eingeben",
        options=["CSV hochladen", "Käufe manuell eingeben", "CSV hochladen und bearbeiten"],
        index=1, 
        help="Laden Sie eine CSV-Datei mit Ihren ETF-Käufen hoch. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten sind essentiell für die Steuerberechnung."
    )

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

    beispiel = pd.DataFrame({
        "Anzahl": [10.0],
        "Preis": [105.34],
        "Kaufdatum": [pd.Timestamp("2026-01-01")]
    })

    st.download_button(
        label="Beispiel CSV-Datei herunterladen",
        data=beispiel.to_csv(index=False).encode("utf-8"),
        file_name="Beispiel_ETF_Käufe.csv",
        mime="text/csv"
    )

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        #checken on alle notwendigen spalten vorhanden sind
        notwendige_spalten = ["Kaufdatum", "Anzahl", "Preis"]

        fehlende_spalten = [s for s in notwendige_spalten if s not in data.columns]

        if fehlende_spalten:
            st.warning(f"Die CSV-Datei enthält nicht alle benötigten Spalten. Fehlend: {', '.join(fehlende_spalten)}. Falls Sie keine passende CSV-Datei haben, können Sie Ihre Käufe auch manuell eingeben.")
            st.stop()

        # checken ob es keine leeren werte gibt
        if data.isnull().values.any():
            st.warning("Die CSV-Datei enthält leere Werte. Bitte füllen Sie alle Felder aus oder laden Sie eine CSV-Datei ohne fehlende Werte hoch. Alternativ können Sie Ihre Käufe auch manuell eingeben.")
            st.stop()

    else:
        st.warning("Bitte laden Sie eine CSV-Datei hoch mit den spalten Kaufdatum, Anzahl und Preis.")
        data = pd.DataFrame({
            "Anzahl": [],
            "Preis": [],
            "Kaufdatum": []
        })
        st.stop()

elif upload == "CSV hochladen und bearbeiten":

    uploaded_file = st.file_uploader("CSV hochladen", type="csv", help="CSV-Datei mit Ihren ETF-Käufen hochladen. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten werden genutzt, um die Verkaufsreihenfolge nach dem FIFO-Prinzip zu bestimmen und den steuerpflichtigen Gewinn zu berechnen. Falls Sie keine CSV-Datei haben, können Sie Ihre Käufe auch manuell eingeben.")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)

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

        data = data.sort_values("Kaufdatum")

        st.download_button(
            label="Daten als CSV herunterladen",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name="Persönliche_ETF_Käufe.csv",
            mime="text/csv"
        )


    else:
        st.warning("Bitte laden Sie eine CSV-Datei hoch mit den Spalten Kaufdatum, Anzahl und Preis.")
        data = pd.DataFrame({
            "Anzahl": [],
            "Preis": [],
            "Kaufdatum": []
        })
        st.stop()

if len(data) == 0:
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


bereits_verkauft = st.number_input("Anzahl bereits verkaufte Anteile (für FIFO-Berechnung)", value=0, help="Gesamtzahl der Anteile, die Sie aus diesem ETF bereits verkauft haben. Der Rechner nutzt diese Information für die FIFO-Berechnung (First-In-First-Out), da steuerlich immer die zuerst gekauften Anteile zuerst verkauft werden.")
if bereits_verkauft < 0:
    st.warning("Bitte geben Sie eine gültige Anzahl bereits verkaufte Anteile ein.")
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

    if not manuelle_eingabe:
        jahresstart = lade_kursdaten(ticker, startjahr)

        # lade alle kursdaten vom 1.1. jedes jahres bis heute
        vorabpauschale = funktionen.berechne_vorabpauschalen_df(jahresstart, teilfreistellung_quote)

    else:
        # kursdaten manuell einfügen oder ohne vorabpauschale rechnen lassen
        ohne_vorabpauschale = st.checkbox("Ohne Vorabpauschale rechnen", value=True, help="Wenn diese Option aktiviert ist, wird keine Vorabpauschale berücksichtigt. Dadurch kann die Steuerberechnung weniger genau sein. Die Vorabpauschale wird normalerweise jährlich von der Bank berechnet und von den zu zahlenden Steuern abgezogen.")

        if ohne_vorabpauschale:
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
                        format="%.6f"
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

alle_anteile= data["Anzahl"].to_list()
max_anteile = sum(alle_anteile)

gesamtkosten = sum(data["Anzahl"] * data["Preis"])

if berechnungstyp == "Steuer und Netto für bestimmte Anzahl berechnen":
    anzahl_verkaufen = st.number_input("Anzahl zu verkaufener Anteile", value=20, help="Anzahl der ETF-Anteile, die verkauft werden sollen. Der Rechner ermittelt daraus Gewinn, Steuer und Nettoerlös.")

    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    if rest_zu_verkaufen > 0:
        raise ValueError("Nicht genug Anteile vorhanden")
    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer
    st.markdown("### Ergebnis Ihrer Berechnung")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Brutto Verkaufserlös", f"{brutto:.2f} €", help="Der Brutto Verkaufserlös entspricht der Anzahl verkaufter Anteile multipliziert mit dem aktuellen Kurs pro Anteil. Er stellt den Gesamtbetrag dar, bevor Steuern abgezogen werden.")
    col2.metric("Zu zahlende Steuer", f"{steuer:.2f}€", help="Die zu zahlende Steuer wird mit dem steuerpflichtigen Gewinn (nach Berücksichtigung von Teilfreistellung, Vorabpauschale, Verlusttopf und Sparerpauschbetrag) multipliziert. Sie zeigt den Betrag an, der an Steuern für den Verkauf der angegebenen Anzahl von Anteilen zu zahlen ist.")
    col3.metric("Netto nach Steuern", f"{netto:.2f}€", help="Der Nettoerlös nach Steuern ist der Betrag, der Ihnen nach Abzug der Steuern vom Brutto Verkaufserlös übrig bleibt. Er berücksichtigt die Teilfreistellung, die Vorabpauschale, den Verlusttopf und den Sparerpauschbetrag.")

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig
    }
    

elif berechnungstyp == "Anteile für gewünschtes Netto berechnen":
    gewolltes_netto = st.number_input("Gewünschtes Netto (€)", value=1000.00, help="Gewünschter Nettoerlös nach Steuern. Der Rechner bestimmt automatisch, wie viele Anteile verkauft werden müssen, um diesen Betrag zu erreichen.")

    anzahl_verkaufen = funktionen.finde_anteile(gewolltes_netto, max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag)
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    if rest_zu_verkaufen > 0:
        raise ValueError("Nicht genug Anteile vorhanden")
    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer
    st.markdown("### Ergebnis Ihrer Berechnung")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Benötigte Anteile", f"{anzahl_verkaufen:.0f}", help="Anzahl der ETF-Anteile, die verkauft werden müssen, um den gewünschten Nettoerlös zu erreichen. Diese Anzahl basiert auf dem FIFO-Prinzip, der Vorabpauschale, der Teilfreistellung und dem verfügbaren Sparerpauschbetrag.")
    col2.metric("Brutto Verkaufserlös", f"{brutto:.2f} €", help="Der Brutto Verkaufserlös entspricht der Anzahl verkaufter Anteile multipliziert mit dem aktuellen Kurs pro Anteil. Er stellt den Gesamtbetrag dar, bevor Steuern abgezogen werden.")
    col3.metric("Netto nach Steuern", f"{netto:.2f}€", help="Der Nettoerlös nach Steuern ist der Betrag, der Ihnen nach Abzug der Steuern vom Brutto Verkaufserlös übrig bleibt. Er berücksichtigt die Teilfreistellung, die Vorabpauschale, den Verlusttopf und den Sparerpauschbetrag.")

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig
    }


elif berechnungstyp == "Steuerfrei verkaufbare Anteile":

    anzahl_verkaufen = funktionen.finde_anteile_ohne_steuer(max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag)
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = funktionen.bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    # teilfreistellung abziehen
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)
    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer

    st.markdown("### Ergebnis Ihrer Berechnung")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Steuerfrei verkaufbare Anteile", f"{anzahl_verkaufen:.0f}", help="Anzahl der ETF-Anteile, die verkauft werden können, ohne dass Steuern anfallen. Diese Anzahl basiert auf dem FIFO-Prinzip, der Vorabpauschale, der Teilfreistellung und dem verfügbaren Sparerpauschbetrag.")
    col2.metric("Nettoerlös", f"{netto:.2f} €", help="Da keine Steuer anfällt, entspricht der Nettoerlös dem Bruttoerlös.")
    col3.metric("Verbliebender Sparerpauschbetrag", f"{freibetrag-gewinn_nach_verlusttopf:.2f}€", help="Der verbleibende Sparerpauschbetrag, der nach dem Verkauf übrig bleibt.")

    st.session_state.results = {
        "anzahl_verkaufen": anzahl_verkaufen,
        "brutto": brutto,
        "gewinn": gewinn,
        "steuer": steuer,
        "netto": netto,
        "gewinn_teilfreistellung": gewinn_teilfreistellung,
        "gewinn_nach_vorabpauschale": gewinn_nach_vorabpauschale,
        "gewinn_nach_verlusttopf": gewinn_nach_verlusttopf,
        "gewinn_steuerpflichtig": gewinn_steuerpflichtig
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
        aktueller_kurs
    )

export_df = pd.DataFrame([st.session_state.results])
export_df["ETF"] = ticker if not manuelle_eingabe else "manuell"
export_df["Gesamt Anteile"] = max_anteile
export_df["Bereits verkaufte Anteile"] = bereits_verkauft
export_df["Gesamtkosten"] = gesamtkosten

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Ergebnisse als CSV herunterladen",
    data=csv,
    file_name="ergebnis_steuer_rechner.csv",
    mime="text/csv"
)


# st.markdown("## Häufige Fragen (FAQ)")

# with st.expander("Was ist der Sparerpauschbetrag?"):
#     st.write("Der Sparerpauschbetrag ist ein Freibetrag für Kapitalerträge. In Deutschland können derzeit bis zu 1000€ pro Person pro Jahr steuerfrei verdient werden. Erst darüber hinaus fällt Abgeltungssteuer an.")

# with st.expander("Was bedeutet FIFO beim ETF-Verkauf?"):
#     st.write("FIFO steht für „First-In-First-Out“. Steuerlich gilt in Deutschland, dass beim Verkauf zunächst die zuerst gekauften ETF-Anteile wieder verkauft werden.")

# with st.expander("Was ist die Teilfreistellung bei ETFs?"):
#     st.write("Bei Aktien-ETFs sind 30% der Gewinne steuerfrei. Das bedeutet, dass nur 70% des Gewinns tatsächlich versteuert werden müssen.")

# with st.expander("Was ist die Vorabpauschale?"):
#     st.write("Die Vorabpauschale ist eine jährliche Mindestbesteuerung für thesaurierende Fonds. Sie stellt sicher, dass ein Teil der Erträge auch dann besteuert wird, wenn der Fonds keine Ausschüttungen vornimmt.")

# with st.expander("Wie genau ist die Steuerberechnung dieses Rechners?"):
#     st.write("Der Rechner verwendet die aktuellen deutschen Steuerregeln und berücksichtigt FIFO, Teilfreistellung, Vorabpauschale, Sparerpauschbetrag und Verlusttopf. Dennoch können in der tatsächlichen Abrechnung Ihrer Bank leichte Abweichungen entstehen.")

# with st.expander("Wie komme ich an meine Kaufdaten?"):
#     st.write("Ihr Broker hat üblicherweise eine Postbox in der Sie ausgeführte Aufträge finden können. In diesen Aufträgen finden Sie dann das Kaufdatum, den Stückpreis, sowie die Anzahl der gekauften Anteile.")


# st.markdown("""
# ---
# ## Impressum
# """)

# with st.expander("Impressum"):
#     st.write(
# """
# ---


# Angaben gemäß §5 DDG

# Name: Dein Name  
# Adresse: Deine Adresse  
# E-Mail: deine@email.de

# Dieses Projekt ist ein privates Informationsangebot. Alle Berechnungen erfolgen ohne Gewähr.
# """)

# online bringen mit website

# execute with streamlit run test.py


# download der ergebnisse als csv datei anbieten
# egebnis schöner darstellen

# domain wie etfsteuerrechner.de oder mit bindestrichen

# reddit post, „Ich habe einen ETF-Steuerrechner gebaut, der FIFO, Vorabpauschale und Freibetrag berücksichtigt.“

# manuell kurs eingeben springt zu aktuell

#impressum
# neues github?
# kann man werbung schalten?
# was muss man mit wernung beachten?

# domain kaufen bei netcup.de

#Datenschutzerklärung
# cookie banner einbauen
# Affiliate‑Links