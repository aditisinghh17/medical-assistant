import React, { useState } from 'react';
import { Upload, FileText, BarChart3, Image, Mic, ThumbsUp, ThumbsDown, Loader2, AlertCircle } from 'lucide-react';

export default function App() {
  const [textInput, setTextInput] = useState('');
  const [textFile, setTextFile] = useState(null);
  const [tableFiles, setTableFiles] = useState([]);
  const [xrayFiles, setXrayFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [caseIdInput, setCaseIdInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!textInput && !textFile && tableFiles.length === 0 && xrayFiles.length === 0) {
      setError('Please provide at least one input (text, file, or image)');
      return;
    }

    const formData = new FormData();
    
    // Add text input if provided
    if (textInput.trim()) {
      formData.append('text_input', textInput.trim());
    }
    
    // Add text file if provided
    if (textFile) {
      formData.append('text_file', textFile);
    }
    
    // Add table files
    tableFiles.forEach(file => {
      formData.append('table_files', file);
    });
    
    // Add xray files
    xrayFiles.forEach(file => {
      formData.append('xray_images', file);
    });

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/generate-soap', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle error responses from backend
        throw new Error(data.error || data.details || `Server error: ${response.status}`);
      }

      setResult(data);
      setError('');
    } catch (err) {
      console.error('Submission error:', err);
      setError(err.message || 'Failed to submit case. Please check your connection and try again.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchCase = async () => {
    if (!caseIdInput.trim()) {
      setError('Please enter a case ID');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch(`http://localhost:8000/cases/${caseIdInput.trim()}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Case not found');
        } else {
          throw new Error(`Server error: ${response.status}`);
        }
      }

      const data = await response.json();
      setResult(data);
      setError('');
    } catch (err) {
      console.error('Fetch case error:', err);
      setError(err.message || 'Failed to fetch case');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTextFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['.txt', '.md', '.rtf'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        setError(`Text file must be one of: ${allowedTypes.join(', ')}`);
        return;
      }
      
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        setError('Text file must be smaller than 10MB');
        return;
      }
      
      setTextFile(file);
      setError('');
    }
  };

  const handleTableFilesChange = (e) => {
    const files = Array.from(e.target.files || []);
    const allowedTypes = ['.pdf', '.csv', '.txt', '.tsv'];
    const maxSize = 50 * 1024 * 1024; // 50MB
    
    for (const file of files) {
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        setError(`Lab files must be one of: ${allowedTypes.join(', ')}`);
        return;
      }
      
      if (file.size > maxSize) {
        setError(`File ${file.name} must be smaller than 50MB`);
        return;
      }
    }
    
    setTableFiles(files);
    setError('');
  };

  const handleXrayFilesChange = (e) => {
    const files = Array.from(e.target.files || []);
    const allowedTypes = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'];
    const maxSize = 20 * 1024 * 1024; // 20MB
    
    for (const file of files) {
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        setError(`Image files must be one of: ${allowedTypes.join(', ')}`);
        return;
      }
      
      if (file.size > maxSize) {
        setError(`Image ${file.name} must be smaller than 20MB`);
        return;
      }
    }
    
    setXrayFiles(files);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6 border border-gray-100">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Multimodal Clinical Insight Assistant</h1>
          <p className="text-gray-600">Upload case data and get AI-powered medical analysis</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-red-800 font-medium">Error</h3>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Main Form */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6 border border-gray-100">
          {/* Case Description */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Case Description
            </label>
            <textarea
              className="w-full p-4 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-gray-900 placeholder-gray-400"
              rows={5}
              placeholder="Enter detailed case description, symptoms, patient history..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
            />
          </div>

          {/* File Upload Section */}
          <div className="grid gap-6 md:grid-cols-3 mb-6">
            {/* Text File Upload */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <FileText size={16} />
                Text Documents
              </label>
              <div className="relative">
                <input
                  type="file"
                  accept=".txt,.md,.rtf"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleTextFileChange}
                />
                <div className="flex items-center justify-center px-4 py-8 border-2 border-dashed border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors">
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex justify-center">
                      <Upload size={32} className="text-gray-400" />
                    </div>
                    <div className="text-sm text-gray-600">
                      {textFile ? textFile.name : 'Upload .txt, .md, .rtf file'}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">Max 10MB</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Lab/CSV Files */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <BarChart3 size={16} />
                Lab Results
              </label>
              <div className="relative">
                <input
                  type="file"
                  multiple
                  accept=".pdf,.csv,.txt,.tsv"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleTableFilesChange}
                />
                <div className="flex items-center justify-center px-4 py-8 border-2 border-dashed border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors">
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex justify-center">
                      <Upload size={32} className="text-gray-400" />
                    </div>
                    <div className="text-sm text-gray-600">
                      {tableFiles.length > 0 ? `${tableFiles.length} files selected` : 'Upload PDF, CSV, TXT files'}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">Max 50MB each</div>
                  </div>
                </div>
              </div>
            </div>

            {/* X-ray Images */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <Image size={16} />
                Medical Images
              </label>
              <div className="relative">
                <input
                  type="file"
                  multiple
                  accept=".jpg,.jpeg,.png,.bmp,.tiff,.gif"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleXrayFilesChange}
                />
                <div className="flex items-center justify-center px-4 py-8 border-2 border-dashed border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex justify-center">
                      <Upload size={32} className="text-gray-400" />
                    </div>
                    <div className="text-sm text-gray-600">
                      {xrayFiles.length > 0 ? `${xrayFiles.length} images selected` : 'Upload X-rays, MRI, CT scans'}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">Max 20MB each</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Processing Case...
              </>
            ) : (
              'Analyze Case'
            )}
          </button>
        </div>

        {/* Case Lookup Section */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6 border border-gray-100">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Lookup Existing Case</h3>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              className="flex-1 p-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400"
              placeholder="Enter case ID (e.g., CASE-12345)"
              value={caseIdInput}
              onChange={(e) => setCaseIdInput(e.target.value)}
            />
            <button
              onClick={fetchCase}
              disabled={loading}
              className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              {loading ? <Loader2 className="animate-spin" size={16} /> : 'Fetch Case'}
            </button>
            <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-3 rounded-lg transition-colors">
              <Mic size={20} />
            </button>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="bg-white shadow-sm rounded-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Analysis Results</h2>
              <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                Complete
              </span>
            </div>
            
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-1">Case ID</div>
                <div className="text-gray-900 font-mono">{result.case_id || caseIdInput}</div>
              </div>

              {result.summary && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Medical Summary</h3>
                  <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                    <p className="text-gray-800 leading-relaxed">{result.summary}</p>
                  </div>
                </div>
              )}

              {result.api_metadata && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Processing Information</h4>
                  <div className="text-sm text-gray-600">
                    <p>Method: {result.api_metadata.processing_method}</p>
                    <p>Files processed: {result.api_metadata.files_processed.lab_files} lab files, {result.api_metadata.files_processed.xray_files} images</p>
                  </div>
                </div>
              )}

              <details className="cursor-pointer group">
                <summary className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-2">
                  <span className="transform transition-transform group-open:rotate-90">▶</span>
                  View Complete Analysis Data
                </summary>
                <div className="mt-3 bg-gray-900 p-4 rounded-lg overflow-hidden">
                  <pre className="text-xs text-gray-100 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              </details>

              {/* Feedback Section */}
              <div className="flex items-center gap-4 pt-4 border-t border-gray-200">
                <span className="text-sm font-medium text-gray-700">Rate this analysis:</span>
                <button className="flex items-center gap-2 text-green-600 hover:text-green-700 hover:bg-green-50 px-3 py-2 rounded-lg transition-colors">
                  <ThumbsUp size={16} />
                  <span className="text-sm font-medium">Helpful</span>
                </button>
                <button className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-lg transition-colors">
                  <ThumbsDown size={16} />
                  <span className="text-sm font-medium">Not Helpful</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}