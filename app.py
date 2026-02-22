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
    st.title("🚂 RTB naar RailCube Converter")

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
            # We zoeken de rij die begint met de positie (Pos)
            match = re.search(r'^(\d+)\s+(\d{2})\s+(\d{4})\s+(\d{3}-\d)\s+([A-Za-z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            
            if match:
                pos_stuk = match.group(1)
                start_nr = pos_stuk[-2:]
                positie = int(pos_stuk[:-2])
                wagon_nr = start_nr + match.group(2) + match.group(3) + match.group(4).replace('-', '')
                
                # UN-nummer extractie
                un_match = re.search(r'UN\s*(\d{4})', line)
                un_nummer = un_match.group(1) if un_match else ""
                
                # GEWICHTEN FIX: We pakken exact de juiste groepen uit de PDF
                # Groep 8 = Tara, Groep 9 = Lading, Groep 10 = Totaal (Bruto)
                tarra_kg = float(match.group(8))
                lading_kg = float(match.group(9))
                bruto_kg = float(match.group(10))
                
                # Omrekenen naar tonnen (delen door 1000)
                tarra_ton = tarra_kg / 1000.0
                lading_ton = lading_kg / 1000.0
                bruto_ton = bruto_kg / 1000.0
                
                wagons.append({
                    'Type': match.group(5),
                    'Volgorde': positie,
                    'Kenteken': wagon_nr,
                    'Netto': lading_ton,   # Dit is nu 0 bij een lege trein!
                    'Tarra': tarra_ton,   # Dit is de 22.28
                    'Bruto': bruto_ton,   # Totaal gewicht
                    'Lengte': float(match.group(7)) / 10.0,
                    'Assen': int(match.group(6)) // 10,
                    'RemP': float(match.group(11)) / 1000.0,
                    'UN': un_nummer
                })
    except Exception as e:
        st.error(f"Fout: {e}")
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
        st.success("Wagens correct geanalyseerd!")
        st.dataframe(df, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Wagonlijst')
            workbook  = writer.book
            worksheet = writer.sheets['Wagonlijst']
            header_format = workbook.add_format({
                'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1
            })
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 20)

        st.download_button(label="📥 Download Excel voor RailCube", data=output.getvalue(), file_name="RTB_RailCube_Import.xlsx")
