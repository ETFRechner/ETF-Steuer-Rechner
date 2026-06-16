import pandas as pd
import funktionen
import streamlit as st
import requests
import yfinance as yf
from datetime import datetime
from datetime import date

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

Geben Sie hier Ihre Daten ein um:
- zu berechnen, **wie viele ETF-Anteile Sie steuerfrei verkaufen können**
- herauszufinden, **wie viele Anteile Sie verkaufen müssen, um einen bestimmten Nettobetrag zu erhalten**
- die **voraussichtliche Steuer beim Verkauf von ETFs** zu berechnen

Mehr Informationen auf der Website: <a href="https://www.etfsteuerrechner.de" target="_blank">etfsteuerrechner.de</a>
            
---
        
""", unsafe_allow_html=True)

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
        st.warning("Die Kursdaten konnten nicht geladen werden. Bitte versuchen Sie es erneut. Falls das Problem weiterhin besteht, nutzen Sie die manuelle Eingabeoption.")
        st.stop()

    kurs_data["jahr"] = kurs_data.index.year

    jahresstart = kurs_data.groupby("jahr").first()

    jahresstart = jahresstart.loc[startjahr:]

    jahresstart = jahresstart[["Close"]]

    jahresstart = jahresstart.reset_index()

    jahresstart.columns = ["jahr", "preis_1_jan"]

    return jahresstart


# --- ZENTRIERTER RESET BUTTON GANZ OBEN ---
# Drei Spalten: Die mittlere Spalte hält den Button zentriert
col_left, col_mid, col_right = st.columns([2, 2, 2])

with col_mid:
    if st.button("🔄 Rechner zurücksetzen", type="secondary", use_container_width=True, help="Löscht alle Eingaben und setzt den Rechner in den Startzustand zurück."):
        # 1. Alle Einträge im Session State löschen
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # 2. Caches leeren
        st.cache_data.clear()
        
        # 3. Seite komplett neu laden
        st.rerun()

# Eine schmale Trennlinie unter dem Reset-Bereich
st.markdown("<hr style='margin: 12px 0px 8px 0px; height: 1px; border: none; background-color: rgba(128, 128, 128, 0.2);'>", unsafe_allow_html=True)
# ------------------------------------------


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

if manuelle_eingabe:
    upload = st.selectbox(
            "Kaufhistorie eingeben",
            options=["CSV hochladen", "Käufe manuell eingeben"],
            index=0, 
            help="Laden Sie eine CSV-Datei mit Ihren ETF-Käufen hoch. Die Datei muss die Spalten Kaufdatum, Anzahl und Preis enthalten. Diese Daten sind essentiell für die Steuerberechnung."
        )
else:
    upload = st.selectbox(
            "Kaufhistorie eingeben",
            options=["automatische Eingabe für Sparpläne", "CSV hochladen", "Käufe manuell eingeben"],
            index=0, 
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
        rate = st.number_input("Sparplanrate (€)", min_value=100.00, step=10.0, help="Monatliche Sparplanrate in Euro.")
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

    if len(data) == 0:
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
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")

    
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
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")

    
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
    st.write("*Hinweis: Die Berechnungen dienen ausschließlich zur unverbindlichen Information und stellen keine steuerliche Beratung dar.*")

    
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

if "results" in st.session_state:
    pdf = funktionen.create_pdf(
        anzahl_verkaufen, max_anteile, bereits_verkauft,
        brutto, gewinn, gewinn_teilfreistellung,
        gewinn_nach_vorabpauschale, gewinn_nach_verlusttopf,
        gewinn_steuerpflichtig, steuer, netto,
        gesamtkosten, vorabpauschale, aktueller_kurs, freibetrag
    )

    st.download_button(
        "Ergebnis als PDF herunterladen",
        pdf,
        "etf_steuer_berechnung.pdf",
        "application/pdf"
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



# execute with streamlit run test.py

# domain wie etfsteuerrechner.de oder mit bindestrichen, checke vor kauf ob ok mit dpma markenregister, ist ok 

# reddit post, „Ich habe einen ETF-Steuerrechner gebaut, der FIFO, Vorabpauschale und Freibetrag berücksichtigt.“

# domain kaufen bei netcup.de

# Plausible nutzen für traffic gucken


