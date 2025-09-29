import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { documentsAPI } from '../utils/api';
import './Home.css';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  status: string;
}

const Home: React.FC = () => {
  const { user, logout } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [uploading, setUploading] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentsAPI.list();
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await documentsAPI.upload(file);
      await loadDocuments(); // Reload documents
      // Reset file input
      event.target.value = '';
    } catch (error: any) {
      alert('Upload failed: ' + (error.response?.data?.error || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setQuerying(true);
    try {
      const result = await documentsAPI.query(query);
      setResponse(result.data.response);
    } catch (error: any) {
      setResponse('Query failed: ' + (error.response?.data?.error || 'Unknown error'));
    } finally {
      setQuerying(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="home-container">
      <header className="home-header">
        <h1>Hello Tutor</h1>
        <div className="user-info">
          <span>Welcome, {user?.name}</span>
          <button onClick={logout} className="logout-button">Logout</button>
        </div>
      </header>

      <main className="home-main">
        <section className="upload-section">
          <h2>Upload Documents</h2>
          <div className="upload-area">
            <input
              type="file"
              id="file-upload"
              accept=".pdf,.docx,.txt"
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className={`upload-button ${uploading ? 'uploading' : ''}`}>
              {uploading ? 'Uploading...' : 'Choose File to Upload'}
            </label>
            <p className="upload-hint">Supported formats: PDF, DOCX, TXT</p>
          </div>
        </section>

        <section className="documents-section">
          <h2>Your Documents</h2>
          {loading ? (
            <p>Loading documents...</p>
          ) : documents.length === 0 ? (
            <p className="no-documents">No documents uploaded yet.</p>
          ) : (
            <div className="documents-list">
              {documents.map((doc) => (
                <div key={doc.id} className="document-item">
                  <div className="document-info">
                    <h3>{doc.filename}</h3>
                    <p>Size: {formatFileSize(doc.file_size)}</p>
                    <p>Uploaded: {formatDate(doc.upload_date)}</p>
                  </div>
                  <div className={`document-status status-${doc.status}`}>
                    {doc.status}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="query-section">
          <h2>Ask Questions</h2>
          <form onSubmit={handleQuery} className="query-form">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your uploaded documents..."
              rows={3}
              disabled={querying}
            />
            <button type="submit" disabled={querying || !query.trim()}>
              {querying ? 'Searching...' : 'Ask Question'}
            </button>
          </form>

          {response && (
            <div className="response-area">
              <h3>Response:</h3>
              <div className="response-content">
                <pre>{response}</pre>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default Home;