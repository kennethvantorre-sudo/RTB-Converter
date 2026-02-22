import streamlit as st
import pandas as pd
import PyPDF2
import re
from io import BytesIO

st.set_page_config(page_title="Certus - RTB Import Tool", page_icon="🚂", layout="wide")

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
            # We zoeken naar de start van een regel: Positie (1-30) gevolgd door het wagennummer
            # Patroon: Positie + Spatie + 37 80...
            match = re.search(r'^\s*(\d+)\s+(3[378]\s+\d{2}\s+\d{4}\s+\d{3}-\d)', line)
            
            if match:
                pos = match.group(1)
                full_line = line.strip()
                # We splitsen de regel op spaties
                parts = full_line.split()
                
                # Het wagennummer staat altijd op index 1, 2, 3, 4 (bijv: 37 80 7929 409-6)
                # We tellen vanaf de achterkant voor de gewichten omdat die het meest stabiel zijn
                # Index van achteren: [-1]=RemG, [-2]=RemP, [-3]=Totaal, [-4]=Lading, [-5]=Tara, [-6]=Lengte, [-7]=AssenL, [-8]=AssenB
                
                try:
                    # Zoek UN nummer in de opmerkingen aan het einde
                    un_match = re.search(r'UN\s*(\d{4})', line)
                    un_nr = un_match.group(1) if un_match else ""

                    wagons.append({
                        'Type': parts[5], # Zacns staat meestal hier
                        'Volgorde': int(pos),
                        'Kenteken': "".join(parts[1:5]).replace('-', ''),
                        'Netto': float(parts[-4]) / 1000.0, # Lading (0 bij leeg)
                        'Tarra': float(parts[-5]) / 1000.0, # Tara (bijv 22280)
                        'Bruto': float(parts[-3]) / 1000.0, # Totaal
                        'Lengte': float(parts[-6]) / 10.0,  # Lengte in dm naar m
                        'Assen': int(parts[-7]),            # Assen L
                        'RemP': float(parts[-2]) / 1000.0,  # Remgewicht P
                        'UN': un_nr
                    })
                except (ValueError, IndexError):
                    continue
                    
    except Exception as e:
        st.error(f"Fout: {e}")
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

        st.download_button(label="📥 Download Excel voor RailCube", data=output.getvalue(), file_name="RTB_RailCube_Import.xlsx")
