"""
Search Pricebook
Quick lookup of UPCs and products in client pricebooks
"""

import streamlit as st
import pandas as pd
import os
from io import StringIO

st.set_page_config(page_title="Search Pricebook", page_icon="🔍", layout="wide")

PRICEBOOKS_FOLDER = "pricebooks"

# ============================================================================
# SESSION STATE
# ============================================================================

if 'search_csv_data' not in st.session_state:
    st.session_state.search_csv_data = None
if 'search_client' not in st.session_state:
    st.session_state.search_client = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# ============================================================================
# FUNCTIONS
# ============================================================================

def get_available_pricebooks():
    """Get list of available pricebook files"""
    if not os.path.exists(PRICEBOOKS_FOLDER):
        return []
    
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

def load_csv_from_path(file_path):
    """Load pipe-delimited CSV"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = [line for line in content.split('\n') if line.strip()]
    if not lines:
        return None
    
    headers = lines[0].split('|')
    data = [line.split('|') for line in lines[1:] if len(line.split('|')) == len(headers)]
    
    return pd.DataFrame(data, columns=headers)

def search_pricebook(df, search_term):
    """Search across all fields in pricebook"""
    if not search_term or df is None:
        return df
    
    search_lower = search_term.lower()
    
    # Search in all text columns
    mask = (
        df['UPC/ PLU'].str.lower().str.contains(search_lower, na=False) |
        df['Product Name'].str.lower().str.contains(search_lower, na=False) |
        df['Category Code'].str.lower().str.contains(search_lower, na=False) |
        df['Category Name'].str.lower().str.contains(search_lower, na=False)
    )
    
    return df[mask]

# ============================================================================
# UI
# ============================================================================

st.title("🔍 Search Pricebook")

st.markdown("Quick lookup tool to find UPCs and products in client pricebooks.")

# Step 1: Select Client
st.header("Step 1: Select Client Pricebook")

pricebooks = get_available_pricebooks()

if not pricebooks:
    st.warning("⚠️ No pricebooks found! Please add CSV files to the 'pricebooks' folder.")
    st.info(f"📁 Expected folder: `{os.path.abspath(PRICEBOOKS_FOLDER)}`")
    st.stop()

col1, col2 = st.columns([3, 1])

with col1:
    client_options = [pb['name'] for pb in pricebooks]
    default_idx = 0
    if st.session_state.search_client in client_options:
        default_idx = client_options.index(st.session_state.search_client)
    
    selected_client = st.selectbox("Select Client:", options=client_options, index=default_idx)

with col2:
    if st.button("📂 Load Pricebook", type="primary"):
        selected_pb = next((pb for pb in pricebooks if pb['name'] == selected_client), None)
        
        if selected_pb:
            st.session_state.search_csv_data = load_csv_from_path(selected_pb['path'])
            st.session_state.search_client = selected_client
            st.session_state.search_results = None
            st.success(f"✓ Loaded {len(st.session_state.search_csv_data)} records")
            st.rerun()

# Show loaded pricebook info
if st.session_state.search_csv_data is not None and st.session_state.search_client:
    st.info(f"📋 Loaded: **{st.session_state.search_client}** ({len(st.session_state.search_csv_data)} records)")

# Step 2: Search
if st.session_state.search_csv_data is not None:
    st.header("Step 2: Search")
    
    search_term = st.text_input(
        "🔍 Search by UPC, Product Name, or Category",
        placeholder="e.g., 88939200134, CELSIUS, Energy Drinks, 707",
        help="Search works across all fields - partial matches accepted"
    )
    
    if search_term:
        results = search_pricebook(st.session_state.search_csv_data, search_term)
        st.session_state.search_results = results
        
        # Results summary
        st.subheader(f"Results ({len(results)} found)")
        
        if len(results) == 0:
            st.warning("No matches found. Try a different search term.")
        else:
            # Display results
            for idx, row in results.iterrows():
                with st.expander(f"UPC: {row['UPC/ PLU']} - {row['Product Name']}", expanded=(idx < 3)):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.text_input("UPC/PLU", value=row['UPC/ PLU'], key=f"r_upc_{idx}", disabled=True)
                        st.text_input("Category Code", value=row['Category Code'], key=f"r_cat_code_{idx}", disabled=True)
                    
                    with col2:
                        st.text_input("Product Name", value=row['Product Name'], key=f"r_prod_{idx}", disabled=True)
                        st.text_input("Category Name", value=row['Category Name'], key=f"r_cat_name_{idx}", disabled=True)
                    
                    with col3:
                        st.text_input("Package Size", value=row['Package Size'], key=f"r_pkg_{idx}", disabled=True)
                        st.text_input("Unit Size", value=row['Unit Size'], key=f"r_unit_{idx}", disabled=True)
            
            # Export button
            st.markdown("---")
            
            output = StringIO()
            results.to_csv(output, sep='|', index=False, lineterminator='\n')
            csv_string = output.getvalue()
            
            st.download_button(
                label=f"📥 Export {len(results)} Results to CSV",
                data=csv_string,
                file_name=f"{st.session_state.search_client.lower().replace(' ', '_')}_search_results.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Enter search term to find products")

# Quick stats
if st.session_state.search_csv_data is not None:
    st.markdown("---")
    st.subheader("📊 Pricebook Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Products", len(st.session_state.search_csv_data))
    
    with col2:
        unique_categories = st.session_state.search_csv_data['Category Code'].nunique()
        st.metric("Unique Categories", unique_categories)
    
    with col3:
        if st.session_state.search_results is not None:
            st.metric("Search Results", len(st.session_state.search_results))
