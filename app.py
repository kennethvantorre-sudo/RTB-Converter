import streamlit as st
import pandas as pd
import PyPDF2
import re
from io import BytesIO

# Pagina instellingen
st.set_page_config(page_title="Certus - RTB Import Tool", page_icon="執行", layout="wide")

# --- LOGO SECTIE ---
# Zorg dat 'logo.png' in je GitHub repository staat
try:
    st.image("logo.png", width=250)
except:
    st.title("🚂 RTB naar RailCube Converter")
    st.write("*Certus Rail Solutions - Operationele Tool*")

st.markdown("---")

def rtb_pdf_naar_railcube(pdf_file):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        # Lees alle pagina's uit de PDF
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        lines = text.split('\n')
        
        for line in lines:
            # Zoek naar de wagongegevens (Pos, Wagennummer, Type, Assen, Lengte, Gewichten, etc.)
            match = re.search(r'^(\d+)\s+(\d{2})\s+(\d{4})\s+(\d{3}-\d)\s+([A-Za-z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            
            if match:
                pos_stuk = match.group(1)
                start_nr = pos_stuk[-2:]
                positie = int(pos_stuk[:-2])
                # Maak het 12-cijferige wagennummer compleet
                wagon_nr = start_nr + match.group(2) + match.group(3) + match.group(4).replace('-', '')
                
                # UN-nummer extractie (zoekt naar UN gevolgd door 4 cijfers aan het einde van de regel)
                un_match = re.search(r'UN\s*(\d{4})', line)
                un_nummer = un_match.group(1) if un_match else ""
                
                # Gegevens omzetten naar tonnen en meters
                tarra = float(match.group(8)) / 1000.0
                lading = float(match.group(9)) / 1000.0
                bruto = float(match.group(10)) / 1000.0
                lengte = float(match.group(7)) / 10.0
                assen = int(match.group(6)) // 10
                rem_p = float(match.group(11)) / 1000.0
                
                wagons.append({
                    'Type': match.group(5),
                    'Volgorde': positie,
                    'Kenteken': wagon_nr,
                    'Netto': lading,
                    'Tarra': tarra,
                    'Bruto': bruto,
                    'Lengte': lengte,
                    'Assen': assen,
                    'RemP': rem_p,
                    'UN': un_nummer
                })
    except Exception as e:
        st.error(f"Fout bij het verwerken van de PDF: {e}")
        return pd.DataFrame()

    # De exacte koppen voor RailCube Hermes Import
    headers = [
        "Type\nType\nType", 
        "Volgorde van de wagens\nOrdre de wagons\nWagons Order",
        "Goedkeuring materiaal\nApprobation matériel\nApprouval material",
        "Kenteken wagon (12cijfers)\nImmatriculation de wagon (12 chiffres)\nvehicale registration number (12 figures)",
        "Netto Gewicht\nPoids nette\nNet Weight", 
        "Tarra Gewicht\nPoids Tare\nTare Weight",
        "Bruto Gewicht\nPoids Brut\nGross weight", 
        "Lengte\nLongueur\nLength",
        "Assen\nEssieux\nAxes", 
        "Positie handrem\nPosition du frein\nPosition handbrake",
        "Gewicht handrem\nPoids frein à main\nWeight handbrake",
        "Soort rem (manueel-autom)\nType de frein (manuel-automatique)\nType brake (manuel-autom)",
        "Geremd gewicht ledig (ton)\nPoids frein à vide (tonnes)\nBraked weight empty (ton)",
        "Omstelgewicht\nPoids pivot\nWeight divider", 
        "Geremd gewicht beladen (ton)\nPoids frein à chargé (tonnes)\nBraked weight loaded (ton)",
        "Revisiedatum op wagon\nDate de révision du wagon\nRevision date", 
        "Snelheid\nVitesse\nSpeed", 
        "C4\nC4\nC4", 
        "D4\nD4\nD4",
        "UN Nummer" # Kolom 19 (Index T)
    ]
    
    df_result = pd.DataFrame(columns=headers)
    
    for w in wagons:
        row = {
            headers[0]: w['Type'],
            headers[1]: w['Volgorde'],
            headers[3]: w['Kenteken'],
            headers[4]: w['Netto'],  # Dit wordt UN Weight en Freight Weight
            headers[5]: w['Tarra'],  # Dit wordt Wagon Weight
            headers[6]: w['Bruto'],
            headers[7]: w['Lengte'],
            headers[8]: w['Assen'],
            headers[14]: w['RemP'],
            headers[19]: w['UN']     # UN Nummer voor func GetUNIDFromString
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    
    return df_result

st.write("### 📂 Stap 1: Upload PDF")
upped = st.file_uploader("Sleep de RTB PDF-wagenlijst hierheen", type="pdf")

if upped:
    df = rtb_pdf_naar_railcube(upped)
    
    if not df.empty:
        st.success(f"✅ {len(df)} wagens succesvol geanalyseerd!")
        
        # Laat tabel zien op de site
        st.write("### 📊 Voorbeeld van data")
        st.dataframe(df, use_container_width=True)
        
        # Excel genereren
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Wagonlijst')
            
            # Styling van de Excel
            workbook  = writer.book
            worksheet = writer.sheets['Wagonlijst']
            header_format = workbook.add_
