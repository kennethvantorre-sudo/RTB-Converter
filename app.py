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
            # We zoeken regels die beginnen met een positie-nummer (1 t/m 30)
            if re.search(r'^\s*\d+\s+37\s+8[04]\s+', line):
                parts = line.split()
                
                # We weten dat bij RTB de gewichten en remgegevens aan het einde staan
                # We tellen vanaf het einde van de rij (negatieve index)
                # [..., Tara, Lading, Totaal, RemP, RemG]
                try:
                    rem_p = float(parts[-3]) / 1000.0
                    bruto_ton = float(parts[-4]) / 1000.0
                    lading_ton = float(parts[-5]) / 1000.0
                    tarra_ton = float(parts[-6]) / 1000.0
                    lengte_m = float(parts[-7]) / 10.0
                    assen = int(parts[-8])
                    
                    # Wagennummer samenstellen uit de losse PDF delen
                    # Meestal zijn dit parts[1], parts[2], parts[3]
                    w_nr = parts[1] + parts[2] + parts[3].replace('-', '')
                    
                    # UN-nummer zoeken in de hele regel
                    un_match = re.search(r'UN\s*(\d{4})', line)
                    un_nummer = un_match.group(1) if un_match else ""

                    wagons.append({
                        'Type': parts[4],
                        'Volgorde': int(parts[0]),
                        'Kenteken': w_nr,
                        'Netto': lading_ton,
                        'Tarra': tarra_ton,
                        'Bruto': bruto_ton,
                        'Lengte': lengte_m,
                        'Assen': assen,
                        'RemP': rem_p,
                        'UN': un_nummer
                    })
                except (ValueError, IndexError):
                    continue
                    
    except Exception as e:
        st.error(f"Fout bij verwerken: {e}")
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
