"""
UPC Pricebook Manager - Multi-Client Tool
A streamlit app to manage and update UPC pricebooks for multiple clients
"""

import streamlit as st
import pandas as pd
import re
import os
from io import StringIO
from datetime import datetime
import subprocess 

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(page_title="UPC Pricebook Manager", page_icon="📊", layout="wide")

PRICEBOOKS_FOLDER = "pricebooks"        # Source pricebooks
UPLOAD_FOLDER = "uploaded_pricebooks"   # Where updated files go (simulates server)


REMOTE_USER = "your_username"           # SSH username
REMOTE_HOST = "your.server.com"         # Server hostname/IP
REMOTE_DIR = "/path/to/remote/directory"  # Remote directory path
# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables"""
    if 'csv_data' not in st.session_state:
        st.session_state.csv_data = None
    if 'selected_client' not in st.session_state:
        st.session_state.selected_client = None
    if 'parsed_entries' not in st.session_state:
        st.session_state.parsed_entries = []
    if 'added_entries' not in st.session_state:
        st.session_state.added_entries = []

# ============================================================================
# FILE OPERATIONS
# ============================================================================

def ensure_folders_exist():
    """Create required folders if they don't exist"""
    os.makedirs(PRICEBOOKS_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_available_pricebooks():
    """Get list of all available pricebook files"""
    ensure_folders_exist()
    
    pricebooks = []
    for file in os.listdir(PRICEBOOKS_FOLDER):
        if file.endswith('.csv'):
            client_name = file[:-4].replace('_', ' ').title()
            pricebooks.append({
                'name': client_name,
                'filename': file,
                'path': os.path.join(PRICEBOOKS_FOLDER, file)
            })
    
    return sorted(pricebooks, key=lambda x: x['name'])

def load_pipe_delimited_csv(content):
    """Parse pipe-delimited CSV content into DataFrame"""
    lines = [line for line in content.split('\n') if line.strip()]
    
    if not lines:
        return None
    
    headers = lines[0].split('|')
    data = [line.split('|') for line in lines[1:] if len(line.split('|')) == len(headers)]
    
    return pd.DataFrame(data, columns=headers)

def load_csv_from_path(file_path):
    """Load CSV from file path"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return load_pipe_delimited_csv(content)

def load_csv_from_upload(file):
    """Load CSV from uploaded file"""
    content = file.read().decode('utf-8')
    return load_pipe_delimited_csv(content)

def save_csv_to_server(dataframe, client_name):
    """
    Save updated CSV to remote server using scp command
    Also saves a local backup copy
    """
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{client_name.lower().replace(' ', '_')}_{timestamp}.csv"
    
    # Convert to pipe-delimited format
    output = StringIO()
    dataframe.to_csv(output, sep='|', index=False, lineterminator='\n')
    csv_content = output.getvalue()
    
    # Save local backup first
    ensure_folders_exist()
    local_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    # Build scp command
    remote_path = f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_DIR}/{filename}"
    
    # Build command with optional SSH key
    if SSH_KEY_PATH:
        cmd = ["scp", "-i", SSH_KEY_PATH, local_path, remote_path]
    else:
        cmd = ["scp", local_path, remote_path]
    
    # Execute scp command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return f"{REMOTE_DIR}/{filename}"
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"SCP failed: {e.stderr}")
# ============================================================================
# DATA PROCESSING
# ============================================================================

def find_category_by_product(product_name, csv_df):
    """Search CSV for similar products and extract category info"""
    if not product_name or csv_df is None:
        return '', ''
    
    keywords = [w for w in product_name.upper().split() if len(w) > 2]
    
    for keyword in keywords:
        mask = csv_df['Product Name'].str.upper().str.contains(keyword, na=False)
        matches = csv_df[mask & csv_df['Category Code'].notna() & csv_df['Category Name'].notna()]
        
        if not matches.empty:
            return matches.iloc[0]['Category Code'], matches.iloc[0]['Category Name']
    
    return '', ''

def check_duplicates(entries, csv_df):
    """Check which UPCs already exist in the CSV"""
    if csv_df is None:
        return []
    
    return [entry['UPC/ PLU'] for entry in entries 
            if entry['UPC/ PLU'] in csv_df['UPC/ PLU'].values]

def create_entry(upc, product_name, category_code, category_name):
    """Create a standardized entry dictionary"""
    return {
        'Category Code': category_code,
        'Category Name': category_name,
        'Product Name': product_name,
        'Package Size': '1',
        'Unit Size': '',
        'UPC/ PLU': upc,
        'Check Digit': '',
        'Vendor ID': '',
        'Vendor Description': ''
    }

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_excel_file(file, csv_df):
    """Parse Excel file and extract UPC entries"""
    df = pd.read_excel(file)
    entries = []
    
    # Find columns (case insensitive search)
    dept_col = next((col for col in df.columns if 'dept' in col.lower()), None)
    upc_col = next((col for col in df.columns if 'id' in col.lower() or 'upc' in col.lower()), None)
    product_col = next((col for col in df.columns if any(x in col.lower() for x in ['product', 'name', 'description'])), None)
    
    for _, row in df.iterrows():
        # Extract and clean data
        category_code = str(row[dept_col]).replace('.', '') if dept_col and pd.notna(row[dept_col]) else ''
        upc = str(row[upc_col]).strip() if upc_col and pd.notna(row[upc_col]) else ''
        product_name = str(row[product_col]).strip() if product_col and pd.notna(row[product_col]) else 'UNNAMED PRODUCT'
        
        if upc and category_code:
            # Get category name from existing CSV
            category_name = ''
            if csv_df is not None:
                matches = csv_df[csv_df['Category Code'] == category_code]
                if not matches.empty:
                    category_name = matches.iloc[0]['Category Name']
            
            entries.append(create_entry(upc, product_name, category_code, category_name))
    
    return entries

def parse_text_input(text, csv_df):
    """Parse text/copied PDF content and extract UPC entries"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    entries = []
    
    for idx, line in enumerate(lines):
        # Skip instruction/header lines
        if should_skip_line(line, idx):
            continue
        
        # Try parsing as table format first
        entry = parse_table_line(line, csv_df)
        if entry:
            entries.append(entry)
            continue
        
        # Try parsing as simple text format
        entry = parse_simple_line(line, csv_df)
        if entry:
            entries.append(entry)
    
    return entries

def should_skip_line(line, idx):
    """Check if line should be skipped during parsing"""
    skip_words = ['please', 'thank', 'add this', 'following']
    if any(word in line.lower() for word in skip_words):
        return True
    if 'UPC' in line and 'Description' in line and idx < 5:
        return True
    if 'Site:' in line or 'JUMP START' in line:
        return True
    return False

def parse_table_line(line, csv_df):
    """Parse tab/pipe separated table format"""
    parts = [p.strip() for p in re.split(r'[\t|]+', line) if p.strip()]
    
    if len(parts) < 2:
        return None
    
    # Find UPC and product name
    for i, part in enumerate(parts):
        if re.match(r'^\d{10,14}$', part):
            upc = part.lstrip('0')
            
            # Find product name in remaining parts
            for j in range(i + 1, len(parts)):
                if not re.match(r'^\d+$', parts[j]) and len(parts[j]) > 2:
                    product_name = parts[j]
                    category_code, category_name = find_category_by_product(product_name, csv_df)
                    return create_entry(upc, product_name, category_code, category_name)
    
    return None

def parse_simple_line(line, csv_df):
    """Parse simple format: UPC followed by product name"""
    match = re.match(r'(\d{10,14})\s+(.+)', line)
    
    if not match:
        return None
    
    upc = match.group(1).lstrip('0')
    product_name = match.group(2).strip()
    
    # Clean product name (remove promotion codes)
    product_name = re.sub(r'\s*(Cookies_|Buy\d+Get\d+|_\w+\d{4}).*$', '', product_name, flags=re.IGNORECASE).strip()
    
    if product_name and len(product_name) > 2:
        category_code, category_name = find_category_by_product(product_name, csv_df)
        return create_entry(upc, product_name, category_code, category_name)
    
    return None

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_client_selector():
    """Render Step 1: Client pricebook selection"""
    st.header("Step 1: Select Client Pricebook")
    
    pricebooks = get_available_pricebooks()
    
    if not pricebooks:
        render_no_pricebooks_found()
        return
    
    # Dropdown and load button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        client_options = [pb['name'] for pb in pricebooks]
        default_idx = 0
        if st.session_state.selected_client in client_options:
            default_idx = client_options.index(st.session_state.selected_client)
        
        selected_client = st.selectbox("Select Client:", options=client_options, index=default_idx)
    
    with col2:
        if st.button("📂 Load Pricebook", type="primary"):
            load_selected_pricebook(pricebooks, selected_client)
    
    # Show currently loaded info
    if st.session_state.csv_data is not None and st.session_state.selected_client:
        st.info(f"📋 Currently loaded: **{st.session_state.selected_client}** ({len(st.session_state.csv_data)} records)")

def render_no_pricebooks_found():
    """Render fallback UI when no pricebooks are found"""
    st.warning("⚠️ No pricebooks found! Please add CSV files to the 'pricebooks' folder.")
    st.info(f"📁 Expected folder location: `{os.path.abspath(PRICEBOOKS_FOLDER)}`")
    st.info("💡 Name your files like: `jumpstart.csv`, `acme_corp.csv`, etc.")
    
    # Manual upload option
    st.subheader("Or upload a pricebook manually")
    manual_upload = st.file_uploader("Upload CSV file", type=['csv'], key='manual_csv')
    
    if manual_upload:
        st.session_state.csv_data = load_csv_from_upload(manual_upload)
        st.session_state.selected_client = "Manual Upload"
        st.success(f"✓ Loaded {len(st.session_state.csv_data)} records")

def load_selected_pricebook(pricebooks, selected_client):
    """Load the selected pricebook into session state"""
    selected_pb = next((pb for pb in pricebooks if pb['name'] == selected_client), None)
    
    if selected_pb:
        st.session_state.csv_data = load_csv_from_path(selected_pb['path'])
        st.session_state.selected_client = selected_client
        st.session_state.parsed_entries = []
        st.session_state.added_entries = []
        st.success(f"✓ Loaded {len(st.session_state.csv_data)} records for {selected_client}")
        st.rerun()

def render_data_input():
    """Render Step 2: Excel/Text input"""
    st.header("Step 2: Add Client Request")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_excel_upload()
    
    with col2:
        render_text_input()

def render_excel_upload():
    """Render Excel file upload section"""
    st.subheader("📁 Upload Excel File")
    excel_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], key='excel')
    
    if excel_file and st.button("Parse Excel"):
        entries = parse_excel_file(excel_file, st.session_state.csv_data)
        st.session_state.parsed_entries = entries
        st.success(f"Found {len(entries)} entries")

def render_text_input():
    """Render text paste section"""
    st.subheader("📝 Or Paste Text/PDF")
    st.info("💡 For PDFs: Select table → Copy → Paste here")
    
    text_input = st.text_area(
        "Paste client text/email/copied PDF:",
        height=200,
        placeholder="Example:\n03202092872 Cookie Monster 2oz\n\nOr paste table from PDF..."
    )
    
    if st.button("Parse Text") and text_input.strip():
        entries = parse_text_input(text_input, st.session_state.csv_data)
        st.session_state.parsed_entries = entries
        if entries:
            st.success(f"Found {len(entries)} entries")
        else:
            st.error("No UPCs found in text")

def render_review_section():
    """Render Step 3: Review and edit parsed entries"""
    st.header("Step 3: Review & Edit Entries")
    
    duplicates = check_duplicates(st.session_state.parsed_entries, st.session_state.csv_data)
    
    if duplicates:
        st.warning(f"⚠️ Found {len(duplicates)} duplicate UPCs (will be skipped)")
    
    # Search and filter
    search = st.text_input("🔍 Search entries by UPC or Product Name")
    display_entries = filter_entries(st.session_state.parsed_entries, search)
    st.info(f"Showing {len(display_entries)} of {len(st.session_state.parsed_entries)} entries")
    
    # Display editable entries
    render_entry_editors(display_entries, duplicates)
    
    # Add button
    if st.button("➕ Add Entries to CSV", type="primary"):
        add_entries_to_csv(duplicates)

def filter_entries(entries, search_term):
    """Filter entries based on search term"""
    if not search_term:
        return entries
    
    search_lower = search_term.lower()
    return [e for e in entries if 
            search_lower in e['UPC/ PLU'].lower() or 
            search_lower in e['Product Name'].lower()]

def render_entry_editors(display_entries, duplicates):
    """Render editable fields for each entry"""
    for i, entry in enumerate(display_entries):
        with st.expander(f"UPC: {entry['UPC/ PLU']} - {entry['Product Name']}", expanded=i<3):
            if entry['UPC/ PLU'] in duplicates:
                st.error("⚠️ This UPC already exists in CSV (will be skipped)")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                entry['UPC/ PLU'] = st.text_input("UPC/PLU", value=entry['UPC/ PLU'], key=f"upc_{i}")
                entry['Category Code'] = st.text_input("Category Code", value=entry['Category Code'], key=f"cat_code_{i}")
            
            with col2:
                entry['Product Name'] = st.text_input("Product Name", value=entry['Product Name'], key=f"prod_{i}")
                entry['Category Name'] = st.text_input("Category Name", value=entry['Category Name'], key=f"cat_name_{i}")
            
            with col3:
                entry['Package Size'] = st.text_input("Package Size", value=entry['Package Size'], key=f"pkg_{i}")
                entry['Unit Size'] = st.text_input("Unit Size", value=entry['Unit Size'], key=f"unit_{i}")

def add_entries_to_csv(duplicates):
    """Add non-duplicate entries to CSV data"""
    new_entries = [e for e in st.session_state.parsed_entries if e['UPC/ PLU'] not in duplicates]
    skipped = len(st.session_state.parsed_entries) - len(new_entries)
    
    if new_entries:
        new_df = pd.DataFrame(new_entries)
        st.session_state.csv_data = pd.concat([st.session_state.csv_data, new_df], ignore_index=True)
        st.session_state.added_entries = new_entries
        st.session_state.parsed_entries = []
        
        st.success(f"✓ Added {len(new_entries)} entries{f', skipped {skipped} duplicates' if skipped > 0 else ''}")
        st.rerun()
    else:
        st.error("All entries are duplicates!")

def render_recently_added():
    """Show recently added entries"""
    if not st.session_state.added_entries:
        return
    
    st.header("✓ Recently Added Entries")
    
    for entry in st.session_state.added_entries:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.text(f"UPC: {entry['UPC/ PLU']}")
        with col2:
            st.text(f"Product: {entry['Product Name']}")
        with col3:
            st.text(f"Category: {entry['Category Code']}")

def render_download_section():
    """Render Step 4: Download and upload buttons"""
    st.header("Step 4: Download or Upload Updated CSV")
    
    st.info(f"Current total: **{len(st.session_state.csv_data)}** records")
    
    # Generate filename and CSV content
    filename = generate_filename(st.session_state.selected_client)
    csv_string = dataframe_to_csv_string(st.session_state.csv_data)
    
    # Buttons side by side
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label=f"⬇️ Download {filename}",
            data=csv_string,
            file_name=filename,
            mime="text/csv",
            type="primary"
        )
    
    with col2:
        if st.button("📤 Upload to Server", type="secondary"):
            upload_to_server()

def generate_filename(client_name):
    """Generate appropriate filename for download"""
    if client_name:
        return f"{client_name.lower().replace(' ', '_')}_updated.csv"
    return "pricebook_updated.csv"

def dataframe_to_csv_string(dataframe):
    """Convert dataframe to pipe-delimited CSV string"""
    output = StringIO()
    dataframe.to_csv(output, sep='|', index=False, lineterminator='\n')
    return output.getvalue()

def upload_to_server():
    """Upload updated CSV to server (currently local folder)"""
    try:
        filepath = save_csv_to_server(st.session_state.csv_data, st.session_state.selected_client)
        st.success(f"✅ Successfully uploaded to server!")
        st.info(f"📁 Saved to: `{filepath}`")
    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    init_session_state()
    
    st.title("📊 UPC Pricebook Manager - Multi-Client")
    
    # Step 1: Select client pricebook
    render_client_selector()
    
    # Only show remaining steps if CSV is loaded
    if st.session_state.csv_data is None:
        return
    
    # Step 2: Add client data
    render_data_input()
    
    # Step 3: Review parsed entries
    if st.session_state.parsed_entries:
        render_review_section()
    
    # Show recently added
    render_recently_added()
    
    # Step 4: Download/Upload
    render_download_section()

if __name__ == "__main__":
    main()