import React, { useState, useEffect } from 'react';
import { Upload, FileText, Plus, AlertCircle, CheckCircle, Download, FileSpreadsheet } from 'lucide-react';
import * as XLSX from 'xlsx';

export default function UPCManager() {
  const [csvData, setCsvData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [clientData, setClientData] = useState('');
  const [parsedEntries, setParsedEntries] = useState([]);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [addedEntries, setAddedEntries] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  // Debug: Log when csvData changes
  useEffect(() => {
    console.log('csvData updated! New length:', csvData.length);
  }, [csvData]);

  // Load existing CSV
  const handleCSVUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter(line => line.trim());
      
      if (lines.length > 0) {
        const headerLine = lines[0].split('|');
        setHeaders(headerLine);
        
        const data = lines.slice(1).map(line => {
          const values = line.split('|');
          return {
            categoryCode: values[0] || '',
            categoryName: values[1] || '',
            productName: values[2] || '',
            packageSize: values[3] || '',
            unitSize: values[4] || '',
            upc: values[5] || '',
            checkDigit: values[6] || '',
            vendorId: values[7] || '',
            vendorDescription: values[8] || ''
          };
        });
        setCsvData(data);
        setMessage({ text: `Loaded ${data.length} records from pricebook`, type:         'success' });
      }
    };
    reader.readAsText(file);
  };

  // Get category name from CSV by category code
  const getCategoryName = (categoryCode) => {
    const found = csvData.find(row => row.categoryCode === categoryCode);
    return found ? found.categoryName : '';
  };

  // Handle Excel upload
  const handleExcelUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: '', raw: false });
        
        console.log('Excel columns found:', Object.keys(jsonData[0] || {}));
        console.log('First row sample:', jsonData[0]);
        
        // Parse Excel data into entries
        const entries = [];
        
        jsonData.forEach((row, idx) => {
          // Get all possible column values
          const rowKeys = Object.keys(row);
          
          // Try to find dept column (case insensitive)
          let categoryCode = '';
          const deptKey = rowKeys.find(k => k.toLowerCase().includes('dept'));
          if (deptKey) {
            categoryCode = String(row[deptKey]).replace(/\./g, '').trim();
          }
          
          // Try to find UPC/ID column
          let upc = '';
          const upcKey = rowKeys.find(k => {
            const lower = k.toLowerCase();
            return lower.includes('upc') || lower.includes('id') || lower === 'upc' || lower === 'id';
          });
          if (upcKey) {
            upc = String(row[upcKey]).trim();
          }
          
          // Try to find product name column
          let productName = '';
          const nameKey = rowKeys.find(k => {
            const lower = k.toLowerCase();
            return lower.includes('product') || lower.includes('name') || lower.includes('description');
          });
          if (nameKey) {
            productName = String(row[nameKey]).trim();
          }
          
          console.log(`Row ${idx}: dept=${categoryCode}, upc=${upc}, name=${productName}`);
          
          if (upc && categoryCode) {
            const entry = {
              categoryCode: categoryCode,
              categoryName: getCategoryName(categoryCode),
              productName: productName || 'UNNAMED PRODUCT',
              packageSize: '1',
              unitSize: '',
              upc: upc,
              checkDigit: '',
              vendorId: '',
              vendorDescription: ''
            };
            entries.push(entry);
          }
        });
        
        if (entries.length > 0) {
          setParsedEntries(entries);
          setMessage({ text: `Parsed ${entries.length} entries from Excel`, type: 'success' });
        } else {
          setMessage({ text: 'No valid entries found in Excel file. Check console for details.', type: 'error' });
        }
      } catch (err) {
        setMessage({ text: `Error reading Excel: ${err.message}`, type: 'error' });
      }
    };
    reader.readAsArrayBuffer(file);
  };

  // Smart category finder - searches CSV for similar products
  const findCategoryByProduct = (productName) => {
    if (!productName) return { code: '', name: '' };
    
    // Extract key words from product name
    const keywords = productName.toUpperCase().split(/\s+/).filter(w => w.length > 2);
    
    // Search CSV for products containing these keywords
    for (const keyword of keywords) {
      const match = csvData.find(row => 
        row.productName.toUpperCase().includes(keyword) && 
        row.categoryCode && 
        row.categoryName
      );
      
      if (match) {
        console.log(`Found category match for "${keyword}": ${match.categoryCode} - ${match.categoryName}`);
        return { code: match.categoryCode, name: match.categoryName };
      }
    }
    
    console.log(`No category match found for: ${productName}`);
    return { code: '', name: '' };
  };



  // Parse client data - handles text and copied PDF tables
  const parseClientData = () => {
    if (!clientData.trim()) {
      setMessage({ text: 'No data to parse', type: 'error' });
      return;
    }

    const lines = clientData.split('\n').filter(line => line.trim());
    const entries = [];

    console.log('=== PARSING CLIENT DATA ===');
    console.log('Total lines:', lines.length);

    lines.forEach((line, idx) => {
      // Skip obvious header/instruction lines
      if (line.includes('UPC') && line.includes('Description') && idx < 5) return;
      if (line.includes('Site:') || line.includes('JUMP START')) return;
      if (line.toLowerCase().includes('please') || line.toLowerCase().includes('thank')) return;
      if (line.toLowerCase().includes('add this') || line.toLowerCase().includes('following')) return;
      
      // Method 1: Tab-separated or pipe-separated (copied PDF table)
      const parts = line.split(/[\t|]+/).map(p => p.trim()).filter(p => p);
      
      if (parts.length >= 2) {
        let upc = '';
        let productName = '';
        
        // Look for UPC in parts
        for (let i = 0; i < parts.length; i++) {
          const part = parts[i];
          
          // Check if this looks like a UPC (10-14 digits)
          if (/^\d{10,14}$/.test(part)) {
            upc = part.replace(/^0+/, ''); // Remove leading zeros
            
            // Next non-numeric part is likely the product name
            for (let j = i + 1; j < parts.length; j++) {
              if (!/^\d+$/.test(parts[j]) && parts[j].length > 2) {
                productName = parts[j];
                break;
              }
            }
            break;
          }
        }
        
        if (upc && productName) {
          const category = findCategoryByProduct(productName);
          
          const entry = {
            categoryCode: category.code,
            categoryName: category.name,
            productName: productName,
            packageSize: '1',
            unitSize: '',
            upc: upc,
            checkDigit: '',
            vendorId: '',
            vendorDescription: ''
          };
          
          console.log(`Parsed: UPC=${upc}, Product=${productName}, Cat=${category.code}`);
          entries.push(entry);
          return;
        }
      }
      
      // Method 2: Simple text format - UPC followed by product name on same line
      const match = line.match(/(\d{10,14})\s+(.+)/);
      
      if (match) {
        const upc = match[1].replace(/^0+/, ''); // Remove leading zeros
        let productName = match[2].trim();
        
        // Clean up product name - remove common suffixes
        productName = productName.replace(/\s*(Cookies_|Buy\d+Get\d+|_\w+\d{4}).*$/i, '').trim();
        
        if (productName && productName.length > 2) {
          const category = findCategoryByProduct(productName);
          
          const entry = {
            categoryCode: category.code,
            categoryName: category.name,
            productName: productName,
            packageSize: '1',
            unitSize: '',
            upc: upc,
            checkDigit: '',
            vendorId: '',
            vendorDescription: ''
          };
          
          console.log(`Parsed: UPC=${upc}, Product=${productName}, Cat=${category.code}`);
          entries.push(entry);
        }
      }
    });

    if (entries.length === 0) {
      setMessage({ text: 'No UPCs found. Check console for details.', type: 'error' });
    } else {
      setParsedEntries(entries);
      setMessage({ text: `Found ${entries.length} entries`, type: 'success' });
    }
  };

  // Check if UPC already exists
  const checkDuplicate = (upc) => {
    return csvData.some(row => row.upc === upc);
  };

  // Add parsed entries to CSV
  const addParsedEntries = () => {
    if (parsedEntries.length === 0) {
      setMessage({ text: 'No entries to add', type: 'error' });
      return;
    }

    const newEntries = [];
    const duplicates = [];

    console.log('=== ADDING ENTRIES ===');
    console.log('Total parsed entries:', parsedEntries.length);
    console.log('Current CSV size:', csvData.length);

    parsedEntries.forEach(entry => {
      const isDup = checkDuplicate(entry.upc);
      console.log(`UPC ${entry.upc}: ${isDup ? 'DUPLICATE' : 'NEW'} - ${entry.productName}`);
      
      if (isDup) {
        duplicates.push(entry.upc);
      } else {
        newEntries.push(entry);
      }
    });

    console.log('New entries to add:', newEntries.length);
    console.log('Duplicate entries skipped:', duplicates.length);

    if (newEntries.length > 0) {
      const updatedCsvData = [...csvData, ...newEntries];
      console.log('Updated CSV size:', updatedCsvData.length);
      
      setCsvData(updatedCsvData);
      setAddedEntries(newEntries);
      setMessage({ 
        text: `Added ${newEntries.length} new entries${duplicates.length > 0 ? `, skipped ${duplicates.length} duplicates` : ''}`, 
        type: 'success' 
      });
      setParsedEntries([]);
      setClientData('');
    } else {
      setMessage({ text: 'All entries are duplicates!', type: 'error' });
    }
  };

  // Update individual parsed entry
  const updateParsedEntry = (index, field, value) => {
    const updated = [...parsedEntries];
    updated[index][field] = value;
    setParsedEntries(updated);
  };

  // Download updated CSV
  const downloadCSV = () => {
    console.log('=== DOWNLOADING CSV ===');
    console.log('Total records in csvData:', csvData.length);
    console.log('First 3 records:', csvData.slice(0, 3));
    console.log('Last 3 records:', csvData.slice(-3));
    
    const header = headers.join('|');
    const rows = csvData.map(row => 
      `${row.categoryCode}|${row.categoryName}|${row.productName}|${row.packageSize}|${row.unitSize}|${row.upc}|${row.checkDigit}|${row.vendorId}|${row.vendorDescription}`
    );
    
    console.log('Total rows being downloaded:', rows.length);
    console.log('Last row:', rows[rows.length - 1]);
    
    const csvContent = [header, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'js_pricebook_updated.csv';
    
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
    
    setMessage({ text: `CSV file downloaded with ${csvData.length} records`, type: 'success' });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">UPC Pricebook Manager</h1>

        {/* Step 1: Upload Existing CSV */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Step 1: Upload Existing Pricebook CSV</h2>
          <label className="flex items-center gap-2 cursor-pointer bg-blue-50 p-3 rounded border-2 border-dashed border-blue-300 hover:border-blue-400">
            <Upload className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-blue-700">Choose CSV File</span>
            <input 
              type="file" 
              accept=".csv" 
              onChange={handleCSVUpload}
              className="hidden"
            />
          </label>
          {csvData.length > 0 && (
            <p className="mt-2 text-sm text-green-700 font-medium">
              ✓ {csvData.length} records loaded
            </p>
          )}
        </div>

        {/* Step 2: Add Client Request */}
        {csvData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-3">Step 2: Add Client Request</h2>
            
            <div className="grid grid-cols-2 gap-3 mb-4">
              <label className="flex items-center gap-2 cursor-pointer bg-green-50 p-3 rounded border-2 border-dashed border-green-300 hover:border-green-400">
                <FileSpreadsheet className="w-5 h-5 text-green-600" />
                <span className="font-medium text-green-700">Upload Excel File</span>
                <input 
                  type="file" 
                  accept=".xlsx,.xls" 
                  onChange={handleExcelUpload}
                  className="hidden"
                />
              </label>

              <div className="bg-purple-50 p-3 rounded border-2 border-dashed border-purple-300 flex items-center justify-center">
                <FileText className="w-5 h-5 text-purple-600 mr-2" />
                <span className="font-medium text-purple-700">Or paste text/PDF below</span>
              </div>
            </div>

            <div className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Paste Client Text/Email/Copied PDF:
              </label>
              <textarea
                value={clientData}
                onChange={(e) => setClientData(e.target.value)}
                className="w-full h-40 px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                placeholder="Example:&#10;03202092872 Cookie Monster 2oz&#10;&#10;Or copy/paste table from PDF..."
              />
              <p className="text-xs text-gray-500 mt-1">
                💡 For PDFs: Select table in PDF → Copy → Paste here
              </p>
            </div>

            <button
              onClick={parseClientData}
              className="mt-2 bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
            >
              Parse Data
            </button>
          </div>
        )}

        {/* Message Display */}
        {message.text && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
            message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            {message.type === 'success' ? 
              <CheckCircle className="w-5 h-5" /> : 
              <AlertCircle className="w-5 h-5" />
            }
            {message.text}
          </div>
        )}

        {/* Step 3: Review Parsed Entries */}
        {parsedEntries.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-3">Step 3: Review & Edit Entries</h2>
            
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {parsedEntries.map((entry, idx) => (
                <div key={idx} className="border rounded p-4 bg-gray-50">
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">UPC</label>
                      <input
                        type="text"
                        value={entry.upc}
                        onChange={(e) => updateParsedEntry(idx, 'upc', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-sm font-mono"
                      />
                      {checkDuplicate(entry.upc) && (
                        <p className="text-xs text-red-600 mt-1">⚠️ Duplicate!</p>
                      )}
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Product Name</label>
                      <input
                        type="text"
                        value={entry.productName}
                        onChange={(e) => updateParsedEntry(idx, 'productName', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Category Code</label>
                      <input
                        type="text"
                        value={entry.categoryCode}
                        onChange={(e) => updateParsedEntry(idx, 'categoryCode', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Category Name</label>
                      <input
                        type="text"
                        value={entry.categoryName}
                        onChange={(e) => updateParsedEntry(idx, 'categoryName', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addParsedEntries}
              className="mt-4 bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add {parsedEntries.length} Entries to CSV
            </button>
          </div>
        )}

        {/* Recently Added Entries */}
        {addedEntries.length > 0 && (
          <div className="bg-green-50 rounded-lg border-2 border-green-300 p-6 mb-6">
            <h2 className="text-lg font-semibold text-green-800 mb-3">
              ✓ Recently Added {addedEntries.length} Entries
            </h2>
            <div className="space-y-2">
              {addedEntries.map((entry, idx) => (
                <div key={idx} className="bg-white p-3 rounded border border-green-200">
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="font-medium">UPC:</span> <span className="font-mono">{entry.upc}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="font-medium">Product:</span> {entry.productName}
                    </div>
                    <div>
                      <span className="font-medium">Category:</span> {entry.categoryCode}
                    </div>
                    <div className="col-span-2">
                      {entry.categoryName}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Download */}
        {csvData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-3">Step 4: Download Updated CSV</h2>
            <p className="text-sm text-gray-600 mb-3">
              Current total: <span className="font-bold text-blue-600">{csvData.length}</span> records
            </p>
            <button
              onClick={downloadCSV}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download js_pricebook_updated.csv ({csvData.length} records)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}