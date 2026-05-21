# --- MOTOR 3: LINEAS CONVERTER (NIEUW & GECORRIGEERD!) ---
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
                
                un_nr = ""
                lading = 0.0
                remgewicht = 0
                
                if "1202" in line:
                    un_nr = "1202"
                
                # Haal alle gewichten en getallen uit de regel
                weights = re.findall(r'\b\d+\.\d+\b|\b\d{2}\b', line)
                # Kuis de UN-codes en gevaarslabels eruit zodat we puur gewichten overhouden
                clean_weights = [w for w in weights if w not in ["12", "30"]]
                
                for w in clean_weights:
                    if "." in w:
                        # Als er een punt in zit (bijv. 0.0), is het ALTIJD de lading!
                        lading = float(w)
                    else:
                        # Als het een heel getal is (bijv. 28) én geen wagenvolgnummer 15 of 20, is het de rem!
                        if w not in ["15", "20"]:
                            remgewicht = int(w)

                wagons.append({
                    "Volgorde": volgorde,
                    "Kenteken": wagon_nr,
                    "Netto": lading,       # Dit komt nu netjes op 0.0
                    "RemP": remgewicht,    # Dit komt nu netjes op 28
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
            headers[0]: w['Type'],
            headers[1]: w['Volgorde'],
            headers[3]: w['Kenteken'],
            headers[4]: w['Netto'],    # Mapt nu correct naar 'Netto Gewicht'
            headers[14]: w['RemP'],    # Mapt nu correct naar 'Geremd gewicht beladen'
            headers[19]: w['UN']
        }
        df_result = pd.concat([df_result, pd.DataFrame([row])], ignore_index=True)
        
    df_result = df_result.fillna("")
    return df_result
