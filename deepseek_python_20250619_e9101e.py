import streamlit as st
import pandas as pd
from pdfminer.high_level import extract_text
import re
from datetime import datetime
import io
import base64
from typing import Tuple, List, Dict, Optional

# Configure page
st.set_page_config(page_title="PDF Matcher Pro", layout="wide")
st.title("PDF Matching Application")
st.write("Upload three PDFs to match dates, amounts, and account information")

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from PDF with error handling"""
    try:
        text = extract_text(pdf_file)
        if not text.strip():
            st.warning(f"PDF appears to be empty or could not be read: {pdf_file.name}")
        return text
    except Exception as e:
        st.error(f"Failed to extract text from {pdf_file.name}: {str(e)}")
        return ""

def extract_table_from_pdf(pdf_file) -> List[str]:
    """Extract table-like data from PDF"""
    text = extract_text_from_pdf(pdf_file)
    if not text:
        return []
    
    # Improved line splitting that handles various whitespace scenarios
    lines = []
    for line in text.split('\n'):
        clean_line = ' '.join(line.strip().split())  # Normalize whitespace
        if clean_line:
            lines.append(clean_line)
    return lines

def parse_date(text: str) -> Optional[datetime.date]:
    """Robust date parsing with multiple formats"""
    date_formats = [
        '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', 
        '%d-%m-%Y', '%m-%d-%Y', '%d %b %Y', 
        '%d %B %Y', '%b %d, %Y', '%B %d, %Y'
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    
    # Try more flexible parsing if strict formats fail
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or MM/DD/YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',     # YYYY/MM/DD
        r'\b\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\b',   # 01 Jan 2023
        r'\b[A-Za-z]{3}\s+\d{1,2},\s+\d{4}\b'   # Jan 01, 2023
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
    
    return None

def extract_amount(text: str) -> Optional[float]:
    """Extract numeric amounts from text"""
    # Match numbers with optional commas, decimals, and currency symbols
    amount_pattern = r'[£$€]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+\.\d{2}'
    matches = re.findall(amount_pattern, text)
    
    for match in matches:
        try:
            # Remove currency symbols and commas
            clean_num = re.sub(r'[£$€,\s]', '', match)
            return float(clean_num)
        except ValueError:
            continue
    
    return None

def extract_account_number(text: str) -> Optional[str]:
    """Extract likely account numbers from text"""
    # Match 8-12 digit numbers not part of dates
    patterns = [
        r'\b\d{8,12}\b',                # Standard account numbers
        r'\b[A-Z]{2}\d{6,10}\b',        # Alphanumeric accounts
        r'\b\d{4}[ -]?\d{4}[ -]?\d{4}\b'  # Formatted numbers
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Skip if this looks like a date
            if not parse_date(match):
                return match
    return None

def process_pdfs(pdf1_file, pdf2_file, pdf3_file) -> Tuple[pd.DataFrame, str]:
    """Main processing function with comprehensive error handling"""
    results = []
    debug_info = []
    
    try:
        # Process PDF1 (Date source)
        pdf1_data = extract_table_from_pdf(pdf1_file)
        debug_info.append(f"PDF1 lines: {len(pdf1_data)}")
        
        dates_in_pdf1 = []
        for i, line in enumerate(pdf1_data, 1):
            try:
                parts = re.split(r'\s{2,}', line)  # Split on multiple spaces
                if parts:
                    date = parse_date(parts[0])
                    if date:
                        dates_in_pdf1.append((date, line))
                        debug_info.append(f"PDF1 Line {i}: Found date {date}")
                    else:
                        debug_info.append(f"PDF1 Line {i}: No date found in '{parts[0]}'")
            except Exception as e:
                debug_info.append(f"PDF1 Line {i} error: {str(e)}")
        
        debug_info.append(f"Found {len(dates_in_pdf1)} valid dates in PDF1")
        
        # Process PDF2 (Amount/Account source)
        pdf2_data = extract_table_from_pdf(pdf2_file)
        debug_info.append(f"PDF2 lines: {len(pdf2_data)}")
        
        pdf2_records = []
        for i, line in enumerate(pdf2_data, 1):
            try:
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 2:
                    date = parse_date(parts[0])
                    if date:
                        amount = extract_amount(line)
                        account_num = extract_account_number(line)
                        
                        if amount is not None:
                            pdf2_records.append({
                                'date': date,
                                'amount': amount,
                                'account_num': account_num,
                                'raw_line': line
                            })
                            debug_info.append(f"PDF2 Line {i}: Found amount {amount} and account {account_num}")
                        else:
                            debug_info.append(f"PDF2 Line {i}: No amount found")
            except Exception as e:
                debug_info.append(f"PDF2 Line {i} error: {str(e)}")
        
        debug_info.append(f"Found {len(pdf2_records)} valid records in PDF2")
        
        # Process PDF3 (Account/Name source)
        pdf3_data = extract_table_from_pdf(pdf3_file)
        debug_info.append(f"PDF3 lines: {len(pdf3_data)}")
        
        pdf3_accounts = {}
        for i, line in enumerate(pdf3_data, 1):
            try:
                account_num = extract_account_number(line)
                if account_num:
                    # Extract name - take the longest non-numeric, non-date string
                    potential_names = [p for p in re.split(r'\s{2,}', line) 
                                      if p != account_num and not extract_amount(p) and not parse_date(p)]
                    if potential_names:
                        name = max(potential_names, key=len)
                        pdf3_accounts[account_num] = name
                        debug_info.append(f"PDF3 Line {i}: Found account {account_num} -> {name}")
            except Exception as e:
                debug_info.append(f"PDF3 Line {i} error: {str(e)}")
        
        debug_info.append(f"Found {len(pdf3_accounts)} account mappings in PDF3")
        
        # Perform matching
        matched_count = 0
        for date, pdf1_line in dates_in_pdf1:
            pdf2_matches = [r for r in pdf2_records if r['date'] == date]
            
            for match in pdf2_matches:
                if match['account_num'] and match['account_num'] in pdf3_accounts:
                    name = pdf3_accounts[match['account_num']]
                    results.append({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Original_Line_PDF1': pdf1_line,
                        'Amount': match['amount'],
                        'Account_Number': match['account_num'],
                        'Customer_Name': name,
                        'Matching_Line_PDF2': match['raw_line']
                    })
                    matched_count += 1
        
        debug_info.append(f"Found {matched_count} matching records across all PDFs")
        
        df = pd.DataFrame(results)
        debug_log = "\n".join(debug_info)
        
        return df, debug_log
    
    except Exception as e:
        st.error(f"Critical processing error: {str(e)}")
        debug_info.append(f"Processing failed: {str(e)}")
        return pd.DataFrame(), "\n".join(debug_info)

def get_download_link(df: pd.DataFrame, filename: str) -> str:
    """Generate download link for DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'

# Main app interface
with st.expander("How to use this tool"):
    st.markdown("""
    1. **Upload three PDF files** using the sidebar controls
    2. Click **Process PDFs** button
    3. View results in the table below
    4. Download results as CSV
    
    **Expected PDF formats:**
    - PDF1: Contains dates in the first column
    - PDF2: Contains matching dates with amounts and account numbers
    - PDF3: Contains account numbers with customer names
    """)

col1, col2 = st.columns(2)

with col1:
    st.subheader("PDF Upload")
    pdf1 = st.file_uploader("First PDF (with dates)", type="pdf", key="pdf1")
    pdf2 = st.file_uploader("Second PDF (with amounts)", type="pdf", key="pdf2")
    pdf3 = st.file_uploader("Third PDF (with account info)", type="pdf", key="pdf3")

with col2:
    st.subheader("Processing Options")
    show_debug = st.checkbox("Show debug information", value=False)
    process_btn = st.button("Process PDFs", type="primary")

if process_btn:
    if not (pdf1 and pdf2 and pdf3):
        st.error("Please upload all three PDF files first")
    else:
        with st.spinner('Processing... This may take a few moments'):
            results_df, debug_log = process_pdfs(pdf1, pdf2, pdf3)
            
            if not results_df.empty:
                st.success("Processing completed successfully!")
                st.dataframe(results_df)
                
                # Generate download link
                st.markdown(get_download_link(results_df, "matched_results.csv"), unsafe_allow_html=True)
                
                # Debug information
                if show_debug:
                    with st.expander("Debug Information"):
                        st.text_area("Processing log", debug_log, height=300)
            else:
                st.warning("No matching records found across the PDFs")
                if show_debug:
                    with st.expander("Debug Information"):
                        st.text_area("Processing log", debug_log, height=300)