brew --version

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

python3 --version

brew install python3

cd "Pricebook automation"

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

source venv/bin/activate

streamlit run Home.py

## Quick Setup - Windows

### Prerequisites

- Windows 10 or later
- Internet connection

### Step 1: Install Python

1. Download Python from: https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT:** Check "Add Python to PATH" during installation
4. Click "Install Now"
5. Verify installation:
   - Open Command Prompt
   - Type: `python --version`
   - Should show Python 3.8 or higher

### Step 2: Install Tesseract OCR

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer
3. Install to default location: `C:\Program Files\Tesseract-OCR`
4. **IMPORTANT:** During installation, select "Add to PATH"
5. Verify installation:
   - Open Command Prompt
   - Type: `tesseract --version`

**If tesseract not found, manually add to PATH:**
1. Right-click "This PC" → Properties
2. Advanced System Settings → Environment Variables
3. Under "System variables", find "Path" → Edit
4. Click "New" → Add: `C:\Program Files\Tesseract-OCR`
5. Click OK, restart Command Prompt

### Step 3: Setup Project

```cmd
# Navigate to project folder (replace with your actual path)
cd "C:\Users\YourName\Pricebook automation"

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) at the start of your command line

# Install dependencies
pip install -r requirements.txt

# Generate NACS category mapping (one-time only)
python setup_nacs.py
```

### Step 4: Run the App

```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Run Streamlit
streamlit run Home.py

# Browser opens automatically at http://localhost:8501