"""
UPC Pricebook Manager - Home
Multi-client pricebook management tool
"""

import streamlit as st

st.set_page_config(
    page_title="UPC Pricebook Manager",
    page_icon="📊",
    layout="wide"
)

st.title("📊 UPC Pricebook Manager")

st.markdown("""
Welcome to the UPC Pricebook Manager - your multi-client pricebook management solution.

### Select a tool from the sidebar:

**📝 Update Existing Pricebook**
- Add new UPCs to existing client pricebooks
- Parse Excel, text, or images
- Auto-categorize using dual-source matching (CSV + NACS)
- Upload to remote server

**🆕 Create New Pricebook** *(Coming Soon)*
- Build pricebook from scratch for new clients
- Auto-categorize using NACS industry standards

---

### Quick Start:
1. Select a tool from the sidebar →
2. Follow the step-by-step workflow
3. Download or upload your updated pricebook

Need help? Contact your admin.
""")

st.info("👈 Select a page from the sidebar to get started!")
