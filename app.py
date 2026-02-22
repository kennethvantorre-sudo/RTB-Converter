import streamlit as st
import pandas as pd
import PyPDF2
import re
from io import BytesIO

st.set_page_config(page_title="RTB RailCube Converter", page_icon="🚂", layout="wide")

def rtb_pdf_naar_railcube(pdf_file):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = reader.pages[0].extract_text()
        lines = text.split('\n')
        
        for line in lines:
            # Verbeterde zoekfunctie voor de RTB PDF structuur
            match = re.search(r'^(\d+)\s+(\d{2})\s+(\d{4})\s+(\d{3}-\d)\s+([A-Za-z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            if match:
                pos_stuk = match.group(1)
                start_nr = pos_stuk[-2:]
                positie = pos_stuk[:-2]
                wagon_nr = start_nr + match.group(2) + match.group(3) + match.group(4).replace('-', '')
                
                wagons.append({
                    'Type': match.group(5),
                    'Volgorde': int(positie),
                    'Kenteken': wagon_nr,
                    'Netto': float(match.group(9)) / 1000.0,
                    'Tarra': float(match.group(8)) / 1000.0,
                    'Bruto': float(match.group(10)) / 1000.0,
                    'Lengte': float(match.group(7)) / 10.0,
                    'Assen': int(match.group(6)) // 10,
                    'RemP': float(match.group(11)) / 1000.0
                })
    except Exception as e:
        st.error(f"Fout bij het lezen van PDF: {e}")
        return pd.DataFrame()

    headers = [
        'Type\nType\nType', 'Volgorde van de wagens\nOrdre de wagons\nWagons Order', 
        'Goedkeuring materiaal\nApprobation matériel\nApprouval material', 
        'Kenteken wagon (12cijfers)\nImmatriculation de wagon (12 chiffres)\nvehicale registration number (12 figures)', 
        'Netto Gewicht\nPoids nette\nNet Weight', 'Tarra Gewicht\nPoids Tare\nTare Weight', 
        'Bruto Gewicht\nPoids Brut\nGross weight', 'Lengte\nLongueur\nLength', 
        'Assen\nEssieux\nAxes', 'Positie handrem\nPosition du frein\nPosition handbrake', 
        'Gewicht handrem\nPoids frein à main\nWeight handbrake', 
        'Soort rem (manueel-autom)\nType de frein (manuel-automatique)\nType brake (manuel-autom)', 
        'Geremd gewicht ledig (ton)\nPoids frein à vide (tonnes)\nBraked weight empty (ton)', 
        'Omstelgewicht\nPoids pivot\nWeight divider', 
        'Geremd gewicht beladen (ton)\nPoids frein à chargé (tonnes)\nBraked weight loaded (ton)', 
        'Revisiedatum op wagon\nDate de révision du wagon\nRevision date', 
        'Snelheid\nVitesse\nSpeed', 'C4\nC4\nC4', 'D4\nD4\nD4'
    ]
    
    df_result = pd.DataFrame(columns=headers)
    for w in wagons:
        row = {
            headers[0]: w['Type'], headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
            headers[4]: w['Netto'], headers[5]: w['Tarra'], headers[6]: w['Bruto'],
            headers[7]: w['Lengte'], headers[8]: w['Assen'], headers[14]: w['RemP']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    return df_result

st.title("🚂 RTB naar RailCube Converter")
st.write("Upload de RTB PDF en download de Excel voor de RailCube-import.")

upped = st.file_uploader("Sleep de RTB PDF hierheen", type="pdf")

if upped:
    df = rtb_pdf_naar_railcube(upped)
    if not df.empty:
        st.success(f"{len(df)} wagens succesvol verwerkt!")
        st.dataframe(df)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel voor RailCube",
            data=output.getvalue(),
            file_name="RailCube_Import.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Geen wagondata gevonden in dit bestand. Controleer of het een RTB wagenlijst is.")
