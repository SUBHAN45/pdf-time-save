# 1. Import Libraries
import streamlit as st
import pandas as pd
from pdfminer.high_level import extract_text
import re
from datetime import datetime
import base64

# 2. App Title
st.title("📄 PDF Matcher Tool")
st.write("Upload 3 PDFs to match dates, amounts, and customer names.")

# 3. PDF Text Extraction Function
def extract_text_from_pdf(pdf_file):
    return extract_text(pdf_file)
    try:
    from pdfminer.high_level import extract_text
except ImportError:
    st.error("Please install pdfminer.six: pip install pdfminer.six")
    st.stop()

# 4. Main Processing Function
def process_pdfs(pdf1, pdf2, pdf3):
    results = []  # This will store our matched data
    
    # 1. Extract text from all PDFs
    pdf1_text = safe_extract_text(pdf1)
    pdf2_text = safe_extract_text(pdf2)
    pdf3_text = safe_extract_text(pdf3)
    
    # 2. Process PDF1 to find dates
    for line in pdf1_text.split('\n'):
        date_match = re.search(r'\d{2}/\d{2}/\d{4}', line)
        if date_match:
            date = date_match.group()
            
            # 3. Search PDF2 for this date
            for line2 in pdf2_text.split('\n'):
                if date in line2:
                    # Extract amount and account number
                    amount = re.search(r'\b\d+\b', line2).group()
                    acc_num = re.search(r'[A-Z]{2,3}\d+', line2).group()
                    
                    # 4. Search PDF3 for account number
                    for line3 in pdf3_text.split('\n'):
                        if acc_num in line3:
                            name = line3.split(acc_num)[-1].strip()
                            results.append({
                                "Date": date,
                                "Amount": amount,
                                "Account": acc_num,
                                "Name": name
                            })
    
    return pd.DataFrame(results)  # Return as DataFrame

# 5. File Upload & Processing
st.sidebar.header("📤 Upload PDF Files")
pdf1 = st.sidebar.file_uploader("PDF 1 (Dates)", type="pdf")
pdf2 = st.sidebar.file_uploader("PDF 2 (Amounts)", type="pdf")
pdf3 = st.sidebar.file_uploader("PDF 3 (Account Names)", type="pdf")

# 6. Run Processing on Button Click
if st.sidebar.button("🔍 Process PDFs") and pdf1 and pdf2 and pdf3:
    df = process_pdfs(pdf1, pdf2, pdf3)
    
    if not df.empty:
        st.success("✅ Processing Complete!")
        st.dataframe(df)
        
        # Create downloadable CSV
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.download_button(
            label="📥 Download Results (CSV)",
            data=f"data:file/csv;base64,{b64}",
            file_name="pdf_results.csv"
        )
    else:
        st.warning("⚠️ No matching records found.")
else:
    st.info("ℹ️ Please upload all 3 PDF files first.")
    if __name__ == "__main__":
    st.title("PDF Matcher")
