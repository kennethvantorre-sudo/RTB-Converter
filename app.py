import streamlit as st
import pandas as pd
import PyPDF2
import re
from io import BytesIO

# 🎨 1. PAGINA INSTELLINGEN
st.set_page_config(page_title="Certus - RTB Import Tool", page_icon="🚂", layout="wide")

# 🎨 2. ZIJBALK (SIDEBAR)
with st.sidebar:
    try:
        st.image("logo.png", width=180)
    except:
        st.write("🚂 **Certus Rail Solutions**")
    
    st.markdown("---")
    st.header("📌 Hoe werkt het?")
    st.write("1. **Download** de wagonlijst (PDF) van RTB.")
    st.write("2. **Upload** de PDF in het vak hiernaast.")
    st.write("3. **Controleer** de tabel.")
    st.write("4. **Download** de Excel voor RailCube.")
    st.markdown("---")
    st.caption("Operationele Tool v2.1")

# --- DE MOTOR (ONGEWIJZIGD) ---
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
            headers[7]: w['Lengte'], headers[8]: w['Assen'], headers[14]: w['RemP'], headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
    
    df_result = df_result.fillna("")
    return df_result
# --- EINDE MOTOR ---

# 🎨 3. HOOFDSCHERM INRICHTING
col_spacer1, col_main, col_spacer2 = st.columns([1, 2, 1])

with col_main:
    st.title("RTB naar RailCube Converter")
    st.info("👋 **Welkom!** Upload hieronder de RTB wagenlijst (PDF).")
    
    st.write("### 📂 Stap 1: Upload PDF")
    upped = st.file_uploader("Sleep de PDF in dit vak", type="pdf")

# 🎨 4. SFEERBEELD (Wordt getoond als er nog niets is geüpload)
if not upped:
    st.markdown("---")
    # Zorg dat je het bestand 'loco.jpg' (of .png) uploadt naar GitHub!
    # use_container_width zorgt dat de foto mooi over de breedte vult.
    try:
        # PAS OP: Als je foto een PNG is, verander .jpg dan naar .png hieronder!
        st.image("loco.jpg", caption="Certus Rail Solutions in actie", use_container_width=True)
    except:
        # Een placeholder tekstje als de foto nog niet is geüpload
        st.write("") # Leeg laten als er geen foto is

st.markdown("---")

# 🎨 5. VERWERKING & DOWNLOAD
if upped:
    df = rtb_pdf_naar_railcube(upped)
    if not df.empty:
        st.success(f"✅ Succes! Er zijn **{len(df)} wagens** klaar voor import.")
        
        st.write("### 📊 Voorbeeld van de Export")
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
            st.write("### 💾 Stap 2: Download")
            st.download_button(
                label="📥 Download Excel voor Hermes", 
                data=output.getvalue(), 
                file_name="RTB_RailCube_Import.xlsx",
                use_container_width=True
            )
    else:
        st.error("❌ Geen gegevens gevonden. Controleer of je de juiste RTB PDF hebt geüpload.")
