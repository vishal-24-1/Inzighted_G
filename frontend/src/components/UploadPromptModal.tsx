import React from 'react';
import { X, UploadCloud, FileText } from 'lucide-react';

interface UploadPromptModalProps {
    isOpen: boolean;
    onClose: () => void;
    onUpload: () => void;
    onOpenLibrary: () => void;
    uploading?: boolean;
}

const UploadPromptModal: React.FC<UploadPromptModalProps> = ({ isOpen, onClose, onUpload, onOpenLibrary, uploading = false }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="upload-prompt-title">
            <div className="w-full max-w-md bg-white rounded-lg p-4 shadow text-left relative" onClick={(e) => e.stopPropagation()}>
                <button
                    className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100"
                    onClick={onClose}
                    aria-label="Close modal"
                >
                    <X size={16} />
                </button>

                <div className="flex items-center">
                    <div>
                        <h3 id="upload-prompt-title" className="text-base font-semibold">Upload notes</h3>
                        <p className="text-xs text-gray-500 mt-0.5 pr-5">We’ll ask questions from your notes & study materials.</p>
                    </div>
                </div>

                <div className="mt-4">
                    <div
                        role="button"
                        tabIndex={0}
                        onClick={onUpload}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onUpload(); }}
                        className="border border-gray-200 rounded-lg p-3 justify-center flex flex-col items-center gap-3 cursor-pointer hover:border-gray-300"
                        aria-describedby="upload-hint"
                    >
                        <FileText size={20} className="text-gray-400" />
                        <div className="text-xs text-gray-400" id="upload-hint">PDF • DOCX • TXT</div>
                    </div>
                </div>

                <div className="mt-4 flex gap-2">
                    <button
                        className="flex-1 bg-blue-600 text-white pb-1 pt-2 rounded-full text-sm"
                        onClick={onUpload}
                        disabled={uploading}
                        aria-disabled={uploading}
                    >
                        {uploading ? (
                            <span className="inline-flex items-center justify-center gap-2">
                                <UploadCloud size={16} className="text-white animate-pulse" />
                                Uploading…
                            </span>
                        ) : (
                            <span className="inline-flex items-center justify-center gap-2">
                                <UploadCloud size={16} className="text-white" />
                                Upload
                            </span>
                        )}
                    </button>
                    <button
                        className="flex-1 bg-white border border-gray-200 text-gray-700 py-2 rounded-full text-sm"
                        onClick={onOpenLibrary}
                    >
                        Library
                    </button>
                </div>
            </div>
        </div>
    );
};

export default UploadPromptModal;
