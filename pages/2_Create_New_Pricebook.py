"""
Create New Pricebook
Build pricebook from scratch for new clients
"""

import streamlit as st

st.set_page_config(page_title="Create New Pricebook", page_icon="🆕", layout="wide")

st.title("🆕 Create New Pricebook")

st.info("📋 This feature is coming soon!")

st.markdown("""
### Planned Features:
- Upload UPCs from Excel/Text/Image
- Auto-categorize using NACS standard
- Review and edit entries
- Download new pricebook CSV

### Workflow:
1. Enter client name
2. Upload UPC list
3. Auto-match categories
4. Review entries
5. Download pricebook

**Status:** Under development
""")
