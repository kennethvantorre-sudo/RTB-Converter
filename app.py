import streamlit as st
import pandas as pd
from io import BytesIO
import PyPDF2
import re

# 🎨 1. PAGINA INSTELLINGEN
st.set_page_config(page_title="Certus - PDF & Excel Import Tool", page_icon="🚂", layout="wide")

# 🎨 2. ZIJBALK (SIDEBAR)
with st.sidebar:
    st.write("🚂 **Certus Rail Solutions**")
    st.markdown("---")
    st.header("📌 Hoe werkt het?")
    st.write("1. **Kies** de juiste bron/partij in het menu.")
    st.write("2. **Upload** de PDF (of Excel voor Strabag).")
    st.write("3. **Controleer** de tabel in de preview.")
    st.write("4. **Download** de afgewerkte Hermes Excel voor RailCube.")
    st.markdown("---")
    st.caption("Operationele Tool v4.2 - Strabag Fix")

# --- DE HERMES HEADERS ---
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

# --- MOTOR 1: RTB CONVERTER ---
def rtb_pdf_naar_railcube(pdf_file):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        lines = text.split('\n')
        for line in lines:
            match = re.search(r'^\s*(\d+?)\s*(\d{2})\s*(\d{2})\s*(\d{4})\s*(\d{3}-\d)\s+([A-Za-z]+)\s+(.*)', line)
            if match:
                pos = int(match.group(1))
                w_nr = match.group(2) + match.group(3) + match.group(4) + match.group(5).replace('-', '')
                w_type = match.group(6)
                rest_van_regel = match.group(7)

                un_match = re.search(r'UN\s*(\d{4})', line)
                un_nr = un_match.group(1) if un_match else ""

                nums = re.findall(r'\d+', rest_van_regel)
                idx_lengte = -1
                for i, n in enumerate(nums):
                    if float(n) >= 100:
                        idx_lengte = i
                        break
                        
                if idx_lengte != -1 and len(nums) >= idx_lengte + 4:
                    lengte_dm = float(nums[idx_lengte])
                    tara_val = float(nums[idx_lengte+1])
                    val2 = float(nums[idx_lengte+2])
                    val3 = float(nums[idx_lengte+3])
                    
                    if abs((tara_val + val2) - val3) <= 10:
                        tarra_kg = tara_val
                        lading_kg = val2
                        bruto_kg = val3
                        rem_p_kg = float(nums[idx_lengte+4]) if len(nums) > idx_lengte + 4 else 0.0
                    else:
                        tarra_kg = tara_val
                        bruto_kg = val2
                        lading_kg = bruto_kg - tarra_kg 
                        rem_p_kg = val3
                    
                    assen_str = str(nums[idx_lengte-1]) if idx_lengte > 0 else "4"
                    assen = int(assen_str[-1]) 
                    
                    wagons.append({
                        'Type': w_type, 'Volgorde': pos, 'Kenteken': w_nr,
                        'Netto': lading_kg / 1000.0, 'Tarra': tarra_kg / 1000.0, 'Bruto': bruto_kg / 1000.0,
                        'Lengte': lengte_dm / 10.0, 'Assen': assen, 'RemP': rem_p_kg / 1000.0, 'UN': un_nr
                    })
    except Exception as e:
        st.error(f"Fout bij verwerking RTB: {e}")
        return pd.DataFrame()

    if not wagons:
        return pd.DataFrame()
    
    df_result = pd.DataFrame(columns=headers)
    for w in wagons:
        row = {
            headers[0]: w['Type'], headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
            headers[4]: w['Netto'], headers[5]: w['Tarra'], headers[6]: w['Bruto'],
            headers[7]: w['Lengte'], headers[8]: w['Assen'], headers[14]: w['RemP'], headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    
    return df_result.fillna("")

# --- MOTOR 2: DOUGLAS CONVERTER ---
def douglas_pdf_naar_railcube(pdf_file, un_code):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        volgorde = 1
        for line in text.split('\n'):
            match = re.search(r'(\d{2}\s*\d{2}\s*\d{4}\s*\d{3}-\d)\s+([A-Za-z])\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', line)
            
            if match:
                wagon_raw = match.group(1)
                loaded_kg_raw = match.group(4)
                wagon_clean = re.sub(r'[\s-]', '', wagon_raw) 
                loaded_tonnes = float(loaded_kg_raw.replace('.', '')) / 1000.0
                
                wagons.append({
                    "Volgorde": volgorde,
                    "Kenteken": wagon_clean,
                    "Netto": loaded_tonnes,
                    "UN": un_code 
                })
                volgorde += 1
                
    except Exception as e:
        st.error(f"Fout bij verwerking Douglas: {e}")
        return pd.DataFrame()

    if not wagons:
        return pd.DataFrame()
    
    df_result = pd.DataFrame(columns=headers)
    for w in wagons:
        row = {
            headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
            headers[4]: w['Netto'], headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    
    return df_result.fillna("")

# --- MOTOR 3: LINEAS CONVERTER ---
def lineas_pdf_naar_railcube(pdf_file):
    wagons = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        wagon_pattern = re.compile(r'\d{4}\s\d{4}\s\d{3}-\d')
        volgorde = 1
        
        for line in text.split('\n'):
            wagon_match = wagon_pattern.search(line)
            if wagon_match:
                wagon_nr = wagon_match.group(0).replace(" ", "").replace("-", "")
                un_nr = "1202" if "1202" in line else ""
                lading = 0.0
                
                if "28" in line:
                    remgewicht = 28
                else:
                    rem_match = re.findall(r'\b\d{2}\b', line)
                    clean_rem = [r for r in rem_match if r not in ["12", "30", str(volgorde)]]
                    remgewicht = int(clean_rem[0]) if clean_rem else 0

                wagons.append({
                    "Volgorde": volgorde,
                    "Kenteken": wagon_nr,
                    "Netto": lading,
                    "RemP": remgewicht,
                    "UN": un_nr,
                    "Type": "Ketelwagen"
                })
                volgorde += 1
                
    except Exception as e:
        st.error(f"Fout bij verwerking Lineas: {e}")
        return pd.DataFrame()

    if not wagons:
        return pd.DataFrame()

    df_result = pd.DataFrame(columns=headers)
    for w in wagons:
        row = {
            headers[0]: w['Type'], headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
            headers[4]: w['Netto'], headers[14]: w['RemP'], headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
        
    return df_result.fillna("")

# --- MOTOR 4: STRABAG EXCEL CONVERTER ---
def strabag_excel_naar_railcube(excel_file):
    try:
        # We lezen specifiek de 'Wagenliste' sheet in van de Strabag Excel
        df_raw = pd.read_excel(excel_file, sheet_name="Wagenliste", header=None, skiprows=6)
        wagons = []
        volgorde = 1
        
        for idx, row in df_raw.iterrows():
            # Als de rij volledig leeg is, spring naar de volgende rij
            if pd.isna(row[0]) and pd.isna(row[1]) and pd.isna(row[2]):
                continue
                
            val_col_5 = str(row[5]).strip()
            val_col_0 = str(row[0]).strip()
            
            # Stop zodra we bij de locomotieven of de totalen komen onderaan de lijst
            if "92 80" in val_col_0 or "93 80" in val_col_0 or "Lok" in val_col_5 or "Totaal" in val_col_0 or "Gesamt" in val_col_0:
                break
                
            try:
                # Plak de stukjes van het wagennummer proper aan elkaar zonder komma's of punten
                d1 = str(row[0]).split('.')[0].strip().zfill(2)
                d2 = str(row[1]).split('.')[0].strip().zfill(2)
                d3 = str(row[2]).split('.')[0].strip().zfill(4)
                d4 = str(row[3]).split('.')[0].strip().zfill(3)
                d5 = str(row[4]).split('.')[0].strip()
                wagon_nr = f"{d1}{d2}{d3}{d4}{d5}"
                
                # Check of het wel een geldig wagennummer is (moet puur uit cijfers bestaan)
                if not wagon_nr.isdigit():
                    continue
                    
                wagon_type = str(row[5]).strip()
                assen = int(row[6]) if pd.notna(row[6]) else 4
                
                # Gewichten en lengte inlezen
                lengte = float(str(row[7]).replace(',', '.').strip()) if pd.notna(row[7]) else 0.0
                tarra = float(str(row[8]).replace(',', '.').strip()) if pd.notna(row[8]) else 0.0
                remgewicht = float(str(row[9]).replace(',', '.').strip()) if pd.notna(row[9]) else 0.0
                
                wagons.append({
                    "Type": wagon_type, "Volgorde": volgorde, "Kenteken": wagon_nr,
                    "Netto": 0.0, "Tarra": tarra, "Bruto": tarra,
                    "Lengte": lengte, "Assen": assen, "RemP": remgewicht
                })
                volgorde += 1
            except:
                # Als er een rij tussen staat die we niet kunnen parsen (bijv. een extra hoofding), sla deze over
                continue
            
        if not wagons:
            return pd.DataFrame()
            
        df_result = pd.DataFrame(columns=headers)
        for w in wagons:
            row_dict = {
                headers[0]: w['Type'], headers[1]: w['Volgorde'], headers[3]: w['Kenteken'],
                headers[4]: w['Netto'], headers[5]: w['Tarra'], headers[6]: w['Bruto'],
                headers[7]: w['Lengte'], headers[8]: w['Assen'], headers[14]: w['RemP']
            }
            df_result = pd.concat([df_result, pd.DataFrame([row_dict])], ignore_index=True)
            
        return df_result
    except Exception as e:
        st.error(f"Fout bij verwerking Strabag Excel: {e}")
        return pd.DataFrame()

# 🎨 3. HOOFDSCHERM INRICHTING
col_spacer1, col_main, col_spacer2 = st.columns([1, 2, 1])

with col_main:
    st.title("RailCube PDF & Excel Converter")
    st.info("👋 **Welkom Kenneth!** Kies de bron en upload het bestand.")
    
    st.write("### 🏭 Stap 1: Kies het Type / De Bron")
    keuze_bron = st.selectbox("Van welke partij of locatie is het bestand?", ["RTB", "Douglas Terminal", "Lineas", "Strabag (Excel)"])
    
    un_keuze = ""
    if keuze_bron == "Douglas Terminal":
        st.write("### 🏷️ Stap 1b: Kies het UN-nummer")
        gekozen_optie = st.radio("Welk product?", ["UN 1202 (Diesel/Gasoil)", "UN 1863 (Jet Fuel)"], horizontal=True)
        un_keuze = gekozen_optie.split(" ")[1] 
    
    file_type = ["xlsx", "xls"] if "Strabag" in keuze_bron else ["pdf"]
    label_text = "Sleep de Strabag EXCEL (*Kirchmöser...*) in dit vak" if "Strabag" in keuze_bron else f"Sleep de {keuze_bron} PDF in dit vak"
    
    st.write(f"### 📂 Stap 2: Upload het bestand")
    upped = st.file_uploader(label_text, type=file_type)

st.markdown("---")

# 🎨 4. VERWERKING & DOWNLOAD
if upped:
    if keuze_bron == "RTB":
        df = rtb_pdf_naar_railcube(upped)
    elif keuze_bron == "Douglas Terminal":
        df = douglas_pdf_naar_railcube(upped, un_keuze)
    elif keuze_bron == "Lineas":
        df = lineas_pdf_naar_railcube(upped)
    elif "Strabag" in keuze_bron:
        df = strabag_excel_naar_railcube(upped)

    if not df.empty:
        st.success(f"✅ Succes! Er zijn **{len(df)} wagens** verwerkt en klaargezet in Hermes-formaat.")
        st.write("### 📊 Voorbeeld van de Export (Hermes Formaat)")
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

        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            st.write("### 💾 Stap 3: Download")
            bestandsnaam = f"{keuze_bron.replace(' ', '_')}_Hermes_RailCube.xlsx"
            
            st.download_button(
                label="📥 Download Excel voor RailCube", 
                data=output.getvalue(), 
                file_name=bestandsnaam,
                use_container_width=True
            )
    else:
        st.error(f"❌ Geen gegevens gevonden of fout in bestand. Controleer uw upload.")
