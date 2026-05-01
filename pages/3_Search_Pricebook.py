"""
Search Pricebook
Quick lookup of UPCs and products in client pricebooks
"""

import streamlit as st
import pandas as pd
import os
from io import StringIO
from difflib import SequenceMatcher

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
    """Search with fuzzy matching - handles typos and partial matches"""
    if not search_term or df is None:
        return df
    
    search_lower = search_term.lower().strip()
    results = []
    
    for idx, row in df.iterrows():
        # Combine searchable fields
        upc_text = str(row['UPC/ PLU']).lower()
        product_text = str(row['Product Name']).lower()
        cat_code = str(row['Category Code']).lower()
        cat_name = str(row['Category Name']).lower()
        
        # Exact or partial match in UPC/Category Code (no fuzzy needed)
        if search_lower in upc_text or search_lower in cat_code:
            results.append(idx)
            continue
        
        # Fuzzy match in Product Name (handles typos)
        product_similarity = SequenceMatcher(None, search_lower, product_text).ratio()
        
        # Also check if search term appears as substring with minor differences
        # Split into words and check each
        search_words = search_lower.split()
        product_words = product_text.split()
        
        word_matches = 0
        for search_word in search_words:
            for product_word in product_words:
                # Check similarity between individual words
                word_similarity = SequenceMatcher(None, search_word, product_word).ratio()
                if word_similarity >= 0.8:  # 80% similar
                    word_matches += 1
                    break
        
        # Match if enough words are similar OR overall similarity is high
        if word_matches >= len(search_words) * 0.7 or product_similarity >= 0.6:
            results.append(idx)
            continue
        
        # Fuzzy match in Category Name
        cat_similarity = SequenceMatcher(None, search_lower, cat_name).ratio()
        if cat_similarity >= 0.7:
            results.append(idx)
    
    return df.loc[results] if results else pd.DataFrame(columns=df.columns)

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
