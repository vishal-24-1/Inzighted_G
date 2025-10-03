import DocumentPicker, { DocumentPickerResponse } from 'react-native-document-picker';
import { launchImageLibrary, ImagePickerResponse } from 'react-native-image-picker';
import { documentsAPI } from './api';

export interface FileUploadResult {
  success: boolean;
  document?: any;
  error?: string;
}

export const pickAndUploadDocument = async (): Promise<FileUploadResult> => {
  try {
    // Pick document
    const result = await DocumentPicker.pickSingle({
      type: [DocumentPicker.types.pdf, DocumentPicker.types.docx, DocumentPicker.types.doc],
      copyTo: 'cachesDirectory',
    });

    if (!result) {
      return { success: false, error: 'No document selected' };
    }

    // Create FormData
    const formData = new FormData();
    formData.append('file', {
      uri: result.fileCopyUri || result.uri,
      type: result.type || 'application/octet-stream',
      name: result.name || 'document',
    } as any);

    // Upload to backend
    const response = await documentsAPI.upload(formData);
    
    return {
      success: true,
      document: response.data.document,
    };
  } catch (error: any) {
    console.error('Document upload failed:', error);
    
    if (DocumentPicker.isCancel(error)) {
      return { success: false, error: 'Upload cancelled' };
    }
    
    return {
      success: false,
      error: error.response?.data?.error || error.message || 'Upload failed',
    };
  }
};

export const pickAndUploadImage = async (): Promise<FileUploadResult> => {
  return new Promise((resolve) => {
    launchImageLibrary(
      {
        mediaType: 'photo',
        quality: 0.8,
        includeBase64: false,
      },
      async (response: ImagePickerResponse) => {
        try {
          if (response.didCancel) {
            resolve({ success: false, error: 'Upload cancelled' });
            return;
          }

          if (response.errorMessage) {
            resolve({ success: false, error: response.errorMessage });
            return;
          }

          if (!response.assets || response.assets.length === 0) {
            resolve({ success: false, error: 'No image selected' });
            return;
          }

          const asset = response.assets[0];
          
          // Create FormData
          const formData = new FormData();
          formData.append('file', {
            uri: asset.uri,
            type: asset.type || 'image/jpeg',
            name: asset.fileName || 'image.jpg',
          } as any);

          // Upload to backend
          const uploadResponse = await documentsAPI.upload(formData);
          
          resolve({
            success: true,
            document: uploadResponse.data.document,
          });
        } catch (error: any) {
          console.error('Image upload failed:', error);
          resolve({
            success: false,
            error: error.response?.data?.error || error.message || 'Upload failed',
          });
        }
      }
    );
  });
};

export const getFileIcon = (filename: string): string => {
  const extension = filename.toLowerCase().split('.').pop();
  
  switch (extension) {
    case 'pdf':
      return 'file-pdf-o';
    case 'doc':
    case 'docx':
      return 'file-word-o';
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return 'file-image-o';
    case 'txt':
      return 'file-text-o';
    default:
      return 'file-o';
  }
};