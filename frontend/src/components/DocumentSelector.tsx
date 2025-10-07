import React, { useState, useEffect } from 'react';
import { documentsAPI } from '../utils/api';
import { X } from 'lucide-react';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  status: string;
}

interface DocumentSelectorProps {
  onDocumentSelect: (documentIds: string[]) => void;
  onCancel: () => void;
  startingSession?: boolean;
}

const DocumentSelector: React.FC<DocumentSelectorProps> = ({ onDocumentSelect, onCancel, startingSession = false }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  // Deduplicate documents by filename (case-insensitive). If multiple documents
  // share the same filename, prefer the one with status 'completed', otherwise
  // prefer the newest by upload_date.
  const dedupeDocuments = (docs: Document[]): Document[] => {
    const map = new Map<string, Document>();
    for (const doc of docs) {
      const key = (doc.filename || '').trim().toLowerCase();
      if (!map.has(key)) {
        map.set(key, doc);
        continue;
      }
      const existing = map.get(key)!;
      // Prefer completed status
      if (doc.status === 'completed' && existing.status !== 'completed') {
        map.set(key, doc);
        continue;
      }
      if (doc.status === existing.status) {
        // Prefer the newer upload
        const docDate = new Date(doc.upload_date).getTime();
        const existingDate = new Date(existing.upload_date).getTime();
        if (!isNaN(docDate) && !isNaN(existingDate) && docDate > existingDate) {
          map.set(key, doc);
        }
      }
    }
    return Array.from(map.values());
  };

  const loadDocuments = async () => {
    try {
      const response = await documentsAPI.list();
      const docs: Document[] = response.data || [];
      setDocuments(dedupeDocuments(docs));
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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading) {
    return (
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        role="status"
        aria-live="polite"
      >
        <div className="bg-white rounded-lg p-6 shadow-lg max-w-md w-full flex flex-col items-center">
          <div className="animate-spin h-8 w-8 border-4 border-gray-200 border-t-blue-600 rounded-full" aria-hidden="true" />
          <p className="mt-3 text-gray-700">Loading your documents...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" role="dialog" aria-modal="true">
      <div className="relative bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[80vh] overflow-auto">
        {startingSession && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center rounded-lg">
            <div className="flex flex-col items-center">
              <div className="animate-spin h-8 w-8 border-4 border-gray-200 border-t-blue-600 rounded-full" aria-hidden="true" />
              <p className="mt-3 text-gray-700">Starting tutoring session...</p>
            </div>
          </div>
        )}

        <div className="p-6">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold">Start Tutoring Session</h2>
              <p className="text-sm text-gray-600">Select one or more documents to include in the test.</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                aria-label="Close"
                onClick={onCancel}
                className="p-2 rounded-md hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <div>
            {error && (
              <div className="mb-4 text-sm text-red-600">{error}</div>
            )}

            {completedDocuments.length === 0 && processingDocuments.length === 0 && (
              <div className="flex flex-col items-center text-center py-8">
                <div className="text-4xl">📄</div>
                <h3 className="mt-3 text-lg font-medium">No Documents Found</h3>
                <p className="mt-2 text-sm text-gray-600 max-w-xl">You haven't uploaded any documents yet. Upload a document first to start a personalized tutoring session.</p>
                <div className="mt-6 w-full flex gap-3">
                  <button
                    className="flex-1 bg-blue-600 text-white py-2 rounded-lg"
                    onClick={() => onDocumentSelect([])}
                  >
                    Start General Tutoring
                  </button>
                  <button
                    className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg"
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
                  <div className="mb-4">
                    <h3 className="text-sm font-medium mb-2">Ready for Tutoring</h3>
                    <div className="flex flex-col gap-2">
                      {completedDocuments.map((doc) => (
                        <button
                          key={doc.id}
                          onClick={() => toggleSelection(doc.id)}
                          className={`flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 text-left w-full ${selectedIds.has(doc.id) ? 'bg-blue-50' : ''}`}
                        >
                          <div className="text-2xl">📄</div>
                          <div className="flex-1">
                            <div className="font-medium">{doc.filename}</div>
                            <div className="text-xs text-gray-500">
                              {formatFileSize(doc.file_size)} • {formatDate(doc.upload_date)}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="text-sm font-medium" style={{ color: getStatusColor(doc.status) }}>
                              Ready
                            </div>
                            <input
                              type="checkbox"
                              checked={selectedIds.has(doc.id)}
                              onChange={() => toggleSelection(doc.id)}
                              className="w-4 h-4"
                              aria-label={`Select ${doc.filename}`}
                            />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {processingDocuments.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium mb-2">Processing</h3>
                    <div className="flex flex-col gap-2">
                      {processingDocuments.map((doc) => (
                        <div key={doc.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 opacity-80">
                          <div className="text-2xl">⏳</div>
                          <div className="flex-1">
                            <div className="font-medium">{doc.filename}</div>
                            <div className="text-xs text-gray-500">
                              {formatFileSize(doc.file_size)} • {formatDate(doc.upload_date)}
                            </div>
                          </div>
                          <div className="text-sm font-medium" style={{ color: getStatusColor(doc.status) }}>
                            Processing...
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* footer removed: primary action is now in header; keep a small hint */}
                <div className="mt-4 text-sm text-gray-500">Select documents and click "Start Test" below.</div>
              </>
            )}
          </div>
        </div>
        {/* Sticky footer with primary action */}
        <div className="sticky bottom-0 bg-white p-4 border-t">
          <div className="flex justify-end">
            <button
              className={`w-full md:w-48 px-4 py-2 rounded-md text-sm font-medium ${selectedIds.size === 0 || startingSession ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white'}`}
              onClick={() => {
                if (startingSession || selectedIds.size === 0) return;
                onDocumentSelect(Array.from(selectedIds));
              }}
              disabled={selectedIds.size === 0 || startingSession}
            >
              {startingSession ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin h-5 w-5 border-2 border-white/60 border-t-white rounded-full mx-auto" aria-hidden="true" />
                    <span className="sr-only">Starting</span>
                  </div>
                ) : (
                  'Start Test'
                )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentSelector;