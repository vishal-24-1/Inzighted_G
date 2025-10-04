import React, { useState, useEffect } from 'react';
import { documentsAPI } from '../utils/api';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  status: string;
}

interface DocumentSelectorProps {
  onDocumentSelect: (documentId: string | null) => void;
  onCancel: () => void;
}

const DocumentSelector: React.FC<DocumentSelectorProps> = ({ onDocumentSelect, onCancel }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentsAPI.list();
      setDocuments(response.data);
    } catch (error: any) {
      setError('Failed to load documents. Please try again.');
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return '#4CAF50';
      case 'processing':
        return '#FF9800';
      case 'failed':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };

  const completedDocuments = documents.filter(doc => doc.status === 'completed');
  const processingDocuments = documents.filter(doc => doc.status === 'processing');

  if (loading) {
    return (
      <div className="document-selector-overlay">
        <div className="document-selector-modal">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading your documents...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="document-selector-overlay">
      <div className="document-selector-modal">
        <div className="modal-header">
          <h2>Start Tutoring Session</h2>
          <p>Which document would you like to base this session on?</p>
        </div>

        <div className="modal-content">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {completedDocuments.length === 0 && processingDocuments.length === 0 && (
            <div className="no-documents">
              <div className="no-docs-icon">📄</div>
              <h3>No Documents Found</h3>
              <p>You haven't uploaded any documents yet. Upload a document first to start a personalized tutoring session.</p>
              <div className="modal-actions">
                <button 
                  className="btn-primary" 
                  onClick={() => onDocumentSelect(null)}
                >
                  Start General Tutoring
                </button>
                <button 
                  className="btn-secondary" 
                  onClick={onCancel}
                >
                  Upload Document First
                </button>
              </div>
            </div>
          )}

          {(completedDocuments.length > 0 || processingDocuments.length > 0) && (
            <>
              {completedDocuments.length > 0 && (
                <div className="documents-section">
                  <h3>Ready for Tutoring</h3>
                  <div className="documents-list">
                    {completedDocuments.map((doc) => (
                      <div 
                        key={doc.id} 
                        className="document-item"
                        onClick={() => onDocumentSelect(doc.id)}
                      >
                        <div className="document-icon">📄</div>
                        <div className="document-info">
                          <div className="document-name">{doc.filename}</div>
                          <div className="document-meta">
                            <span>{formatFileSize(doc.file_size)}</span>
                            <span>•</span>
                            <span>{formatDate(doc.upload_date)}</span>
                          </div>
                        </div>
                        <div 
                          className="document-status"
                          style={{ color: getStatusColor(doc.status) }}
                        >
                          Ready
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {processingDocuments.length > 0 && (
                <div className="documents-section">
                  <h3>Processing</h3>
                  <div className="documents-list">
                    {processingDocuments.map((doc) => (
                      <div 
                        key={doc.id} 
                        className="document-item disabled"
                      >
                        <div className="document-icon">⏳</div>
                        <div className="document-info">
                          <div className="document-name">{doc.filename}</div>
                          <div className="document-meta">
                            <span>{formatFileSize(doc.file_size)}</span>
                            <span>•</span>
                            <span>{formatDate(doc.upload_date)}</span>
                          </div>
                        </div>
                        <div 
                          className="document-status"
                          style={{ color: getStatusColor(doc.status) }}
                        >
                          Processing...
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="modal-actions">
                <button 
                  className="btn-secondary" 
                  onClick={() => onDocumentSelect(null)}
                >
                  Start General Tutoring
                </button>
                <button 
                  className="btn-outline" 
                  onClick={onCancel}
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentSelector;