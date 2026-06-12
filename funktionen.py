import streamlit as st
import pandas as pd

def bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft):
    rest_zu_verkaufen = anzahl_verkaufen
    gewinn = 0
    brutto = 0
    gesamte_vorabpauschale = 0

    for _, row in data.iterrows():

        if rest_zu_verkaufen <= 0:
            break

        anzahl = row["Anzahl"]
        kaufpreis = row["Preis"]
        datum = row["Kaufdatum"]

        # print(bereits_verkauft, anzahl, datum)

        if bereits_verkauft > 0:
            if anzahl <= bereits_verkauft:
                bereits_verkauft -= anzahl
                # print(f"nichts verkauft von {datum}, da bereits verkauft")
                continue
            else:
                anzahl -= bereits_verkauft
                bereits_verkauft = 0

        # wie viele aus dieser position verkaufen
        zu_verkaufen = min(anzahl, rest_zu_verkaufen)

        # gewinn berechnen
        gewinn += (aktueller_kurs - kaufpreis) * zu_verkaufen
        brutto += (aktueller_kurs) * zu_verkaufen

        rest_zu_verkaufen -= zu_verkaufen

        # berechne gesamte vorabpauschale für diese position
        rows = vorabpauschale.loc[vorabpauschale["jahr"] >= datum.year]

        for _, vp_row in rows.iterrows():

            vorabpauschale_stueck = vp_row["vorabpauschale_stueck"]
    
            if datum.year == vp_row["jahr"]:
                # passe pauschale an die zeit pro jahr an
                monate_gehalten_im_Jahr = 12 - datum.month + 1
            else:
                monate_gehalten_im_Jahr = 12

            vorabpauschale_anteil = vorabpauschale_stueck * monate_gehalten_im_Jahr / 12
            gesamte_vorabpauschale += vorabpauschale_anteil * zu_verkaufen 
    
    if rest_zu_verkaufen -0.000001 > 0:
        raise ValueError("Nicht genug Anteile vorhanden")

        
    return gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen



def bestimme_netto(brutto, gewinn, steuersatz, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag):
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)

    steuer = gewinn_steuerpflichtig * steuersatz
    netto = brutto - steuer

    return netto

def bestimme_steuerpflichtigen_gewinnn(gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag):
    gewinn_teilfreistellung = gewinn * (1 - teilfreistellung_quote)
    gewinn_nach_vorabpauschale = max(0, gewinn_teilfreistellung - gesamte_vorabpauschale)
    gewinn_nach_verlusttopf = max(0, gewinn_nach_vorabpauschale - verlusttopf)
    gewinn_steuerpflichtig = max(0, gewinn_nach_verlusttopf - freibetrag)

    return gewinn_steuerpflichtig


def finde_anteile(ziel_netto, max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag):

    low = 0
    high = max_anteile

    while low <= high:

        mid = (low + high) // 2
        # netto = berechne_netto(mid)
        gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(mid, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
        netto = bestimme_netto(brutto, gewinn, steuersatz, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag)

        if abs(netto - ziel_netto) < 1:
            return mid

        if netto < ziel_netto:
            low = mid + 1
        else:
            high = mid - 1

    return low

def finde_anteile_ohne_steuer(max_anteile, aktueller_kurs, data, vorabpauschale, bereits_verkauft, steuersatz, teilfreistellung_quote, verlusttopf, freibetrag):
    low = 0
    high = max_anteile

    # checken ob überhaupt steuern gezahlt werden müssen
    gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(high, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    # st.write(f"Gewinn bei Verkauf aller Anteile: {rest_zu_verkaufen}€")
    steuerpflichtiger_gewinn = bestimme_steuerpflichtigen_gewinnn(gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag)
    if steuerpflichtiger_gewinn == 0:
        return high

    while low <= high:

        mid = (low + high) // 2
   
        gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(mid, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
        steuerpflichtiger_gewinn = bestimme_steuerpflichtigen_gewinnn(gewinn, teilfreistellung_quote, gesamte_vorabpauschale, verlusttopf, freibetrag)

        if abs(low - high) <= 1:
            return mid

        if steuerpflichtiger_gewinn > 0:
            high = mid - 1
        else:
            low = mid 
        
    return low


def detailierte_darstellung(anzahl_verkaufen, max_anteile, bereits_verkauft, brutto, gewinn, gewinn_teilfreistellung, gewinn_nach_vorabpauschale, gewinn_nach_verlusttopf, gewinn_steuerpflichtig, steuer, netto, gesamtkosten, vorabpauschale, aktueller_kurs):
    # gewinn, brutto, gesamte_vorabpauschale, rest_zu_verkaufen = bestimme_steuer(anzahl_verkaufen, aktueller_kurs, data, vorabpauschale, bereits_verkauft)
    # st.markdown("## Detaillierte Berechnung")

    # -------------------------------
    # Überblick
    # -------------------------------

    st.markdown("### Überblick Ihrer Position (vor Verkauf)")

    col1, col2, col3 = st.columns(3)

    aktueller_besitz = max_anteile - bereits_verkauft
    gesamtwert = aktueller_besitz * aktueller_kurs

    col1.metric("Gekaufte Anteile", f"{max_anteile:.0f}")
    col2.metric("Aktuell im Besitz", f"{aktueller_besitz:.0f}")
    col3.metric("Gesamtwert", f"{gesamtwert:.2f}€")
    

    durchschnittlicher_kaufpreis = gesamtkosten / max_anteile

    st.caption(f"Durchschnittlicher Kaufpreis: {durchschnittlicher_kaufpreis:.2f} €")

    # -------------------------------
    # Verkaufsübersicht
    # -------------------------------

    st.markdown("### Verkaufsübersicht")

    col1, col2 = st.columns(2)

    col1.metric("Verkaufte Anteile", f"{anzahl_verkaufen:.0f}")
    col2.metric("Kurs bei Verkauf", f"{aktueller_kurs:.2f} €")
    # col3.metric("Gewinn vor Steuern", f"{gewinn:.2f} €")
    

    # -------------------------------
    # Steuerberechnung
    # -------------------------------

    st.markdown("### Steuerberechnung")

    steuer_df = pd.DataFrame({
        "Berechnungsschritt": [
            "Bruttoverkauf",
            "Gewinn vor Steuer",
            "Nach Teilfreistellung",
            "Nach Vorabpauschale",
            "Nach Verlusttopf",
            "Nach Sparerpauschbetrag",
            "Zu zahlende Steuer",
            "Netto nach Steuern"
        ],
        "Betrag (€)": [
            f"{brutto:.2f}",
            f"{gewinn:.2f}",
            f"{gewinn_teilfreistellung:.2f}",
            f"{gewinn_nach_vorabpauschale:.2f}",
            f"{gewinn_nach_verlusttopf:.2f}",
            f"{gewinn_steuerpflichtig:.2f}",
            f"{steuer:.2f}",
            f"{netto:.2f}"
        ]
    })

    st.dataframe(steuer_df, use_container_width=True)

    # -------------------------------
    # Vorabpauschale
    # -------------------------------

    st.markdown("### Berücksichtigte Vorabpauschale")

    st.caption("Vorabpauschale pro Anteil und Jahr")

    st.dataframe(vorabpauschale, use_container_width=True)




@st.cache_data
def berechne_vorabpauschalen_df(kursdaten, teilfreistellung_quote):

    basiszins_df = pd.read_csv("basiszins.csv")

    ergebnisse = []

    for jahr in kursdaten["jahr"].unique():

        if jahr not in basiszins_df["jahr"].values:
            continue


        jahr_daten = kursdaten[kursdaten["jahr"] == jahr]
        folgejahr_daten = kursdaten[kursdaten["jahr"] == jahr + 1]


        preis_1_jan = jahr_daten.iloc[0]["preis_1_jan"]
        preis_31_dez = folgejahr_daten.iloc[0]["preis_1_jan"] if not folgejahr_daten.empty else jahr_daten.iloc[-1]["preis_1_jan"]

        wertsteigerung = max(0, preis_31_dez - preis_1_jan)

        basiszins = basiszins_df.loc[
            basiszins_df["jahr"] == jahr, "basiszins"
        ].values[0]

        basisertrag = preis_1_jan * basiszins/100 * (1 - teilfreistellung_quote)

        vorabpauschale = min(wertsteigerung, basisertrag)

        ergebnisse.append({
            "jahr": jahr,
            # "preis_1_jan": preis_1_jan,
            # "preis_31_dez": preis_31_dez,
            # "wertsteigerung": wertsteigerung,
            # "basiszins": basiszins,
            "vorabpauschale_stueck": vorabpauschale * (1 - teilfreistellung_quote)
        })

    # erstelle ein leeres df mit nur spaltennemen

    if not ergebnisse:
        ergebnisse = pd.DataFrame(columns=["jahr", "vorabpauschale_stueck"])
    else:
        ergebnisse = pd.DataFrame(ergebnisse)

    return ergebnisse
