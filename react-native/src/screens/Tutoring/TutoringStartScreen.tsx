import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { documentsAPI, tutoringAPI } from '../../services/api';
import { Document } from '../../types';

interface TutoringStartScreenProps {
  navigation: any;
}

const TutoringStartScreen: React.FC<TutoringStartScreenProps> = ({ navigation }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingSession, setStartingSession] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentsAPI.list();
      // Only show completed documents
      const completedDocs = response.data.filter((doc: Document) => doc.status === 'completed');
      setDocuments(completedDocs);
    } catch (error) {
      console.error('Failed to load documents:', error);
      Alert.alert('Error', 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const startTutoringSession = async (documentId?: string) => {
    setStartingSession(true);
    try {
      const response = await tutoringAPI.startSession(documentId);
      
      navigation.navigate('TutoringSession', {
        sessionId: response.data.session_id,
        firstQuestion: response.data.first_question,
      });
    } catch (error: any) {
      console.error('Failed to start tutoring session:', error);
      Alert.alert(
        'Failed to Start Session',
        error.response?.data?.error || 'Please try again later'
      );
    } finally {
      setStartingSession(false);
    }
  };

  const startGeneralTutoring = () => {
    Alert.alert(
      'General Tutoring',
      'Start a general tutoring session without a specific document?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Start', onPress: () => startTutoringSession() }
      ]
    );
  };

  const startDocumentTutoring = (document: Document) => {
    Alert.alert(
      'Document Tutoring',
      `Start tutoring session for "${document.filename}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Start', onPress: () => startTutoringSession(document.id) }
      ]
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const renderDocument = ({ item }: { item: Document }) => (
    <TouchableOpacity 
      style={styles.documentCard}
      onPress={() => startDocumentTutoring(item)}
      disabled={startingSession}
    >
      <Text style={styles.documentName} numberOfLines={2}>
        {item.filename}
      </Text>
      <View style={styles.documentMeta}>
        <Text style={styles.metaText}>Size: {formatFileSize(item.file_size)}</Text>
        <Text style={styles.metaText}>Uploaded: {formatDate(item.upload_date)}</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#0b5fff" />
        <Text style={styles.loadingText}>Loading documents...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Start Tutoring</Text>
        <Text style={styles.subtitle}>Choose a document or start general tutoring</Text>
      </View>

      <View style={styles.content}>
        <TouchableOpacity
          style={[styles.generalButton, startingSession && styles.disabledButton]}
          onPress={startGeneralTutoring}
          disabled={startingSession}
        >
          {startingSession ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <>
              <Text style={styles.generalButtonTitle}>General Tutoring</Text>
              <Text style={styles.generalButtonSubtitle}>
                Get help with any topic or question
              </Text>
            </>
          )}
        </TouchableOpacity>

        {documents.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Or choose a document:</Text>
                <FlatList<Document>
                  data={documents}
                  keyExtractor={(item: Document) => item.id}
                  renderItem={renderDocument}
                  contentContainerStyle={styles.documentsList}
                  showsVerticalScrollIndicator={false}
                />
          </>
        )}

        {documents.length === 0 && (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No documents available</Text>
            <Text style={styles.emptySubtitle}>
              Upload documents to start document-specific tutoring sessions
            </Text>
            <TouchableOpacity
              style={styles.uploadButton}
              onPress={() => navigation.navigate('Documents')}
            >
              <Text style={styles.uploadButtonText}>Upload Documents</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666666',
  },
  header: {
    padding: 24,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  generalButton: {
    backgroundColor: '#0b5fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  generalButtonTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  generalButtonSubtitle: {
    fontSize: 14,
    color: '#e6f2ff',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: 16,
  },
  documentsList: {
    paddingBottom: 16,
  },
  documentCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  documentName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  documentMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metaText: {
    fontSize: 12,
    color: '#666666',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 24,
  },
  uploadButton: {
    backgroundColor: '#10b981',
    borderRadius: 8,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  uploadButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default TutoringStartScreen;