import streamlit as st
import PyPDF2
import pandas as pd
from pdfminer.high_level import extract_text
import re
from datetime import datetime
import io
import base64

st.set_page_config(page_title="PDF Matcher", layout="wide")
st.title("PDF Matching Application")

def extract_text_from_pdf(pdf_file):
    return extract_text(pdf_file)

def extract_table_from_pdf(pdf_file):
    text = extract_text_from_pdf(pdf_file)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return lines

def parse_date(text):
    date_formats = ['%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y']
    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None

def process_pdfs(pdf1_file, pdf2_file, pdf3_file):
    with st.spinner('Processing PDFs...'):
        # Process PDF1 to get dates
        pdf1_data = extract_table_from_pdf(pdf1_file)
        dates_in_pdf1 = []
        
        for line in pdf1_data:
            parts = re.split(r'\s{2,}', line)
            if parts:
                date = parse_date(parts[0])
                if date:
                    dates_in_pdf1.append((date, line))
        
        # Process PDF2
        pdf2_data = extract_table_from_pdf(pdf2_file)
        pdf2_records = []
        
        for line in pdf2_data:
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                date = parse_date(parts[0])
                if date:
                    amount = None
                    for part in parts[1:]:
                        if re.match(r'^-?\d+(?:,\d{3})*(?:\.\d{2})?$', part.replace(',', '')):
                            amount = float(part.replace(',', ''))
                            break
                    
                    if amount is not None:
                        account_num = None
                        for part in parts:
                            if re.match(r'^\d{8,12}$', part):
                                account_num = part
                                break
                        
                        pdf2_records.append({
                            'date': date,
                            'amount': amount,
                            'account_num': account_num,
                            'raw_line': line
                        })
        
        # Process PDF3
        pdf3_data = extract_table_from_pdf(pdf3_file)
        pdf3_accounts = {}
        
        for line in pdf3_data:
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                account_num = None
                name = None
                
                for part in parts:
                    if re.match(r'^\d{8,12}$', part):
                        account_num = part
                        break
                
                if account_num:
                    for part in parts:
                        if part != account_num and not re.match(r'^\d', part):
                            name = part
                            break
                    
                    if name:
                        pdf3_accounts[account_num] = name
        
        # Perform matching
        results = []
        
        for date, pdf1_line in dates_in_pdf1:
            pdf2_matches = [r for r in pdf2_records if r['date'] == date]
            
            for match in pdf2_matches:
                if match['account_num'] in pdf3_accounts:
                    name = pdf3_accounts[match['account_num']]
                    results.append({
                        'Date': date.strftime('%d/%m/%Y'),
                        'Original_Line': pdf1_line,
                        'Amount': match['amount'],
                        'Account_Number': match['account_num'],
                        'Customer_Name': name
                    })
        
        return results

def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="results.csv">Download CSV File</a>'
    return href

# File uploaders
st.sidebar.header("Upload PDF Files")
pdf1 = st.sidebar.file_uploader("Upload First PDF (with dates)", type="pdf")
pdf2 = st.sidebar.file_uploader("Upload Second PDF (with amounts)", type="pdf")
pdf3 = st.sidebar.file_uploader("Upload Third PDF (with account info)", type="pdf")

if st.sidebar.button("Process PDFs") and pdf1 and pdf2 and pdf3:
    results = process_pdfs(pdf1, pdf2, pdf3)
    
    if results:
        df = pd.DataFrame(results)
        st.success("Processing completed successfully!")
        st.dataframe(df)
        
        # Download link
        st.markdown(get_table_download_link(df), unsafe_allow_html=True)
    else:
        st.warning("No matching records found across the PDFs.")

elif st.sidebar.button("Process PDFs"):
    st.error("Please upload all three PDF files first")