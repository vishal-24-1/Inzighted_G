import React, { useState, useEffect } from 'react';
import { documentsAPI } from '../utils/api';
import { X, Trash2 } from 'lucide-react';

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
  onUpload?: () => void;
  startingSession?: boolean;
  preselectDocumentId?: string;
}

const DocumentSelector: React.FC<DocumentSelectorProps> = ({ onDocumentSelect, onCancel, onUpload, startingSession = false, preselectDocumentId }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

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

  // If the caller provided a preselectDocumentId, initialize selection with it
  // after documents are loaded and the id exists in the list.
  useEffect(() => {
    if (!preselectDocumentId) return;
    if (documents.length === 0) return;
    const exists = documents.some(d => d.id === preselectDocumentId);
    if (exists) {
      setSelectedIds(new Set([preselectDocumentId]));
    }
  }, [preselectDocumentId, documents]);

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDeleteClick = (e: React.MouseEvent, documentId: string) => {
    e.stopPropagation(); // Prevent document selection
    setDeleteConfirmId(documentId);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmId) return;
    
    setDeletingId(deleteConfirmId);
    setError(null);
    
    try {
      await documentsAPI.delete(deleteConfirmId);
      
      // Remove from documents list
      setDocuments(prev => prev.filter(doc => doc.id !== deleteConfirmId));
      
      // Remove from selection if selected
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(deleteConfirmId);
        return next;
      });
      
      setDeleteConfirmId(null);
    } catch (error: any) {
      console.error('Error deleting document:', error);
      setError(error.response?.data?.message || 'Failed to delete document. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  if (loading) {
    return (
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-0"
        role="status"
        aria-live="polite"
      >
        <div className="bg-white rounded-none sm:rounded-lg p-6 shadow-lg w-full h-full sm:max-h-[60vh] sm:max-w-md flex flex-col items-center overflow-auto">
          <div className="animate-spin h-8 w-8 border-4 border-gray-200 border-t-blue-600 rounded-full" aria-hidden="true" />
          <p className="mt-3 text-gray-700">Loading your documents...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 bg-black/50" role="dialog" aria-modal="true">
      <div className="relative bg-white rounded-none sm:rounded-lg shadow-lg w-full h-full sm:mx-4 sm:max-w-2xl sm:max-h-[80vh] overflow-auto">
        {startingSession && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center rounded-lg">
            <div className="flex flex-col items-center">
              <div className="animate-spin h-8 w-8 border-4 border-gray-200 border-t-blue-600 rounded-full" aria-hidden="true" />
              <p className="mt-3 text-gray-700">Starting tutoring session...</p>
            </div>
          </div>
        )}

        <div className="pl-6 pt-4 pr-4 pb-28">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold">Library</h2>
              <p className="text-sm text-gray-600">Select one or more documents from your library to include in the test.</p>
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
              <div className="flex flex-col items-center text-center py-12 px-4 mt-10">
                <div className="text-5xl mb-2">📄</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Empty</h3>
                <p className="text-sm text-gray-600 mb-4 max-w-sm leading-relaxed">Upload your notes or documents to start personalized test sessions.</p>
                <button
                  className="bg-blue-500 text-white py-3 px-6 rounded-xl font-medium shadow-lg hover:bg-blue-700 transition-colors"
                  onClick={onUpload}
                >
                  Upload Document
                </button>
              </div>
            )}

            {(completedDocuments.length > 0 || processingDocuments.length > 0) && (
              <>
                {completedDocuments.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium mb-2">Ready for Tutoring</h3>
                    <div className="flex flex-col gap-2">
                      {completedDocuments.map((doc) => (
                        <div
                          key={doc.id}
                          className={`relative flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 ${selectedIds.has(doc.id) ? 'bg-blue-50' : ''}`}
                        >
                          <button
                            onClick={() => toggleSelection(doc.id)}
                            className="flex items-center gap-3 flex-1 text-left"
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
                          <button
                            onClick={(e) => handleDeleteClick(e, doc.id)}
                            disabled={deletingId === doc.id}
                            className="p-2 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                            aria-label={`Delete ${doc.filename}`}
                            title="Delete document"
                          >
                            {deletingId === doc.id ? (
                              <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-red-500 rounded-full" />
                            ) : (
                              <Trash2 size={16} className="text-gray-400 hover:text-red-500" />
                            )}
                          </button>
                        </div>
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
        {/* Fixed footer with primary action at the bottom of the viewport */}
        <div className="fixed left-0 right-0 bottom-0 z-60 bg-white p-4">
          <div className="max-w-2xl mx-auto flex justify-end">
            <button
              className={`w-full md:w-48 px-4 py-4 rounded-xl text-sm font-medium ${selectedIds.size === 0 || startingSession ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white'}`}
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
        
        {/* Delete Confirmation Modal */}
        {deleteConfirmId && (
          <div className="absolute inset-0 bg-black/70 flex items-center justify-center rounded-lg z-50">
            <div className="bg-white rounded-lg p-6 max-w-sm mx-4 shadow-xl">
              <h3 className="text-lg font-bold mb-2">Delete Document?</h3>
              <p className="text-sm text-gray-600 mb-4">
                This will permanently delete the document and its data. Existing sessions and insights will be preserved.
              </p>
              <div className="text-sm text-gray-500 mb-6">
                <strong>Document:</strong> {documents.find(d => d.id === deleteConfirmId)?.filename}
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={handleDeleteCancel}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={deletingId === deleteConfirmId}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deletingId === deleteConfirmId ? (
                    <span className="flex items-center gap-2">
                      <div className="animate-spin h-4 w-4 border-2 border-white/60 border-t-white rounded-full" />
                      Deleting...
                    </span>
                  ) : (
                    'Delete'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentSelector;