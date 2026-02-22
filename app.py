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
            # We zoeken het begin van de regel.
            # \d+? (lazy) zorgt ervoor dat als PDF '1' en '37' samenvoegt tot '137', hij dit netjes splitst in '1' en '37'.
            match = re.search(r'^\s*(\d+?)\s*(\d{2})\s*(\d{2})\s*(\d{4})\s*(\d{3}-\d)\s+([A-Za-z]+)\s+(.*)', line)
            
            if match:
                pos = int(match.group(1)) # Dit is nu weer netjes 1, 2, 3...
                w_nr = match.group(2) + match.group(3) + match.group(4) + match.group(5).replace('-', '')
                w_type = match.group(6)
                rest_van_regel = match.group(7)

                # UN-nummer veilig apart zoeken
                un_match = re.search(r'UN\s*(\d{4})', line)
                un_nr = un_match.group(1) if un_match else ""

                # Haal alle overgebleven getallen uit de rest van de regel
                nums = re.findall(r'\d+', rest_van_regel)
                
                # Zoek de lengte (dit is bij RTB altijd het eerste getal in deze reeks boven de 100, bijv 167)
                idx_lengte = -1
                for i, n in enumerate(nums):
                    if float(n) >= 100:
                        idx_lengte = i
                        break
                        
                # Als we de lengte hebben gevonden, staan de gewichten daar altijd exact achter
                if idx_lengte != -1 and len(nums) >= idx_lengte + 5:
                    lengte_dm = float(nums[idx_lengte])
                    tarra_kg = float(nums[idx_lengte+1])
                    lading_kg = float(nums[idx_lengte+2])
                    bruto_kg = float(nums[idx_lengte+3])
                    rem_p_kg = float(nums[idx_lengte+4])
                    
                    # Het aantal assen staat net vóór de lengte
                    assen_str = str(nums[idx_lengte-1]) if idx_lengte > 0 else "4"
                    assen = int(assen_str[-1]) # Pakt de '4' uit '4' of samengevoegde '04'
                    
                    wagons.append({
                        'Type': w_type,
                        'Volgorde': pos,
                        'Kenteken': w_nr,
                        'Netto': lading_kg / 1000.0,
                        'Tarra': tarra_kg / 1000.0,
                        'Bruto': bruto_kg / 1000.0,
                        'Lengte': lengte_dm / 10.0,
                        'Assen': assen,
                        'RemP': rem_p_kg / 1000.0,
                        'UN': un_nr
                    })
    except Exception as e:
        st.error(f"Fout bij verwerking van PDF: {e}")
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
    
    # Vervang NaN door lege strings voor een nettere weergave
    df_result = df_result.fillna("")
    return df_result

st.write("### 📂 Stap 1: Upload PDF")
upped = st.file_uploader("Sleep de RTB PDF hierheen", type="pdf")

if upped:
    df = rtb_pdf_naar_railcube(upped)
    if not df.empty:
        st.success(f"✅ {len(df)} wagens gevonden en perfect uitgelijnd!")
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
        st.download_button(label="📥 Download Excel voor RailCube Hermes", data=output.getvalue(), file_name="RTB_RailCube_Import.xlsx")
    else:
        st.error("❌ Geen gegevens gevonden. Controleer de indeling van de PDF.")
