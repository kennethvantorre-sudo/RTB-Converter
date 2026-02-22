import streamlit as st
import pandas as pd
import PyPDF2
import re
from io import BytesIO

# Pagina instellingen
st.set_page_config(page_title="Certus - RTB Import Tool", page_icon="🚂", layout="wide")

# Logo sectie
try:
    st.image("logo.png", width=250)
except:
    st.title("🚂 Certus RTB Converter")

st.markdown("---")

def rtb_pdf_naar_railcube(pdf_file):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        lines = text.split('\n')
        
        for line in lines:
            # We zoeken naar het wagennummer (bijv: 37 80 7929 409-6)
            # Dit is ons 'anker' punt.
            wagon_match = re.search(r'(\d{2})\s+(\d{2})\s+(\d{4})\s+(\d{3}-\d)', line)
            
            if wagon_match:
                # We halen alle getallen uit de regel
                # RTB regels eindigen ALTIJD op: Lengte, Tara, Lading, Totaal, RemP, RemG
                numbers = re.findall(r'\d+', line)
                
                # Het eerste getal in de regel is de 'Pos' (positie)
                pos = numbers[0]
                
                # Het wagennummer (zonder streepjes)
                w_nr = "".join(wagon_match.groups()).replace('-', '')
                
                # We pakken de gewichten van ACHTEREN naar VOREN (negatieve index)
                # Omdat de opmerkingen (UN-nummers) achteraan staan, kijken we specifiek naar de posities vòòr de stationscodes
                try:
                    # RTB Layout: ... Lengte(dm) Tara(kg) Lading(kg) Totaal(kg) RemP(kg) RemG(kg) ...
                    # In de meeste regels zijn dit de getallen op deze posities vanaf het wagennummer:
                    tarra_kg = float(numbers[-6])
                    lading_kg = float(numbers[-5])
                    totaal_kg = float(numbers[-4])
                    rem_p_kg = float(numbers[-3])
                    lengte_dm = float(numbers[-7])
                    assen = int(numbers[5]) # Assen staat meestal direct na het type
                    
                    # UN-nummer zoeken (UN + 4 cijfers)
                    un_match = re.search(r'UN\s*(\d{4})', line)
                    un_nr = un_match.group(1) if un_match else ""

                    wagons.append({
                        'Type': "Zacns", # Standaard voor deze lijst
                        'Volgorde': int(pos),
                        'Kenteken': w_nr,
                        'Netto': lading_kg / 1000.0,
                        'Tarra': tarra_kg / 1000.0,
                        'Bruto': totaal_kg / 1000.0,
                        'Lengte': lengte_dm / 10.0,
                        'Assen': assen if assen < 10 else 4,
                        'RemP': rem_p_kg / 1000.0,
                        'UN': un_nr
                    })
                except:
                    continue
                    
    except Exception as e:
        st.error(f"Fout bij verwerking: {e}")
        return pd.DataFrame()

    if not wagons:
        return pd.DataFrame()

    headers = [
        "Type\nType\nType", "Volgorde van de wagens\nOrdre de wagons\nWagons Order",
        "Goedkeuring materiaal\nApprobation matériel\nApprouval material",
        "Kenteken wagon (12cijfers)\nImmatriculation de wagon (12 chiffres)\nvehicale registration number (12 figures)",
        "Netto Gewicht\nPoids nette\nNet Weight", "Tarra Gewicht\nPoids Tare\nTare Weight",
        "Bruto Gewicht\nPoids Brut\nGross weight", "Lengte\nLongueur\nLength",
        "Assen\nEssieux\nAxes", "Positie handrem\nPosition du frein\nPosition handbrake",
        "Gewicht handrem\nPoids frein à main\nWeight handbrake",
        "Soort rem (manueel-autom)\nType de frein (manuel-automatique)\nType brake (manuel-autom)",
        "Geremd gewicht ledig (ton)\nPoids frein à vide (tonnes)\nBraked weight empty (ton)",
        "Omstelgewicht\nPoids pivot\nWeight divider", "Geremd gewicht beladen (ton)\nPoids frein à chargé (tonnes)\nBraked weight loaded (ton)",
        "Revisiedatum op wagon\nDate de révision du wagon\nRevision date", "Snelheid\nVitesse\nSpeed", "C4\nC4\nC4", "D4\nD4\nD4",
        "UN Nummer"
    ]
    
    df_result = pd.DataFrame(columns=headers)
    for w in wagons:
        row = {
            headers[0]: w['Type'], headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
            headers[4]: w['Netto'], headers[5]: w['Tarra'], headers[6]: w['Bruto'],
            headers[7]: w['Lengte'], headers[8]: w['Assen'], headers[14]: w['RemP'],
            headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    return df_result

st.write("### 📂 Stap 1: Upload PDF")
upped = st.file_uploader("Sleep de RTB PDF hierheen", type="pdf")

if upped:
    df = rtb_pdf_naar_railcube(upped)
    if not df.empty:
        st.success(f"✅ {len(df)} wagens gevonden!")
        st.write("### 📊 Overzicht")
        st.dataframe(df, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Wagonlijst')
            workbook  = writer.book
            worksheet = writer.sheets['Wagonlijst']
            header_format = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 20)

        st.write("### 💾 Stap 2: Download")
        st.download_button(label="📥 Download Excel voor RailCube", data=output.getvalue(), file_name="RTB_RailCube_Import.xlsx")
    else:
        st.error("❌ Geen gegevens gevonden. Controleer of de PDF de juiste indeling heeft.")
