import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { tutoringAPI } from '../../services/api';
import { ChatMessage, TutoringQuestion } from '../../types';

interface TutoringSessionScreenProps {
  navigation: any;
  route: any;
}

const TutoringSessionScreen: React.FC<TutoringSessionScreenProps> = ({ 
  navigation, 
  route 
}) => {
  const { sessionId, firstQuestion } = route.params;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionFinished, setSessionFinished] = useState(false);
  const flatListRef = useRef<FlatList<ChatMessage> | null>(null);

  useEffect(() => {
    // Add the first question to messages
    if (firstQuestion) {
      const questionMessage: ChatMessage = {
        id: firstQuestion.id,
        content: firstQuestion.text,
        is_user_message: false,
        created_at: firstQuestion.created_at,
      };
      setMessages([questionMessage]);
    }

    // Set up header
    navigation.setOptions({
      title: 'Tutoring Session',
      headerRight: () => (
        <TouchableOpacity onPress={endSession} style={{ marginRight: 16 }}>
          <Text style={{ color: '#ef4444', fontWeight: '600' }}>End</Text>
        </TouchableOpacity>
      ),
    });
  }, [firstQuestion, navigation]);

  const submitAnswer = async () => {
    if (!inputText.trim() || loading || sessionFinished) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputText.trim(),
      is_user_message: true,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);

    try {
      const response = await tutoringAPI.submitAnswer(sessionId, inputText.trim());
      
      if (response.data.finished) {
        // Session is complete
        setSessionFinished(true);
        
        const completionMessage: ChatMessage = {
          id: Date.now().toString(),
          content: response.data.message,
          is_user_message: false,
          created_at: new Date().toISOString(),
        };
        
        setMessages(prev => [...prev, completionMessage]);
        
        Alert.alert(
          'Session Complete',
          'Congratulations! You have completed this tutoring session.',
          [
            {
              text: 'View Insights',
              onPress: () => {
                navigation.navigate('Insights', { 
                  screen: 'SessionInsight',
                  params: { sessionId }
                });
              }
            },
            {
              text: 'New Session',
              onPress: () => {
                navigation.navigate('TutoringStart');
              }
            }
          ]
        );
      } else if (response.data.next_question) {
        // Continue with next question
        const questionMessage: ChatMessage = {
          id: response.data.next_question.id,
          content: response.data.next_question.text,
          is_user_message: false,
          created_at: response.data.next_question.created_at,
        };
        
        setMessages(prev => [...prev, questionMessage]);
      }

      // Scroll to bottom
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);

    } catch (error: any) {
      console.error('Failed to submit answer:', error);
      Alert.alert('Error', 'Failed to submit answer. Please try again.');
      
      // Remove the user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const endSession = () => {
    Alert.alert(
      'End Session',
      'Are you sure you want to end this tutoring session?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'End Session', 
          style: 'destructive',
          onPress: async () => {
            try {
              await tutoringAPI.endSession(sessionId);
              navigation.navigate('TutoringStart');
            } catch (error) {
              console.error('Failed to end session:', error);
              navigation.navigate('TutoringStart');
            }
          }
        }
      ]
    );
  };

  const renderMessage = ({ item }: { item: ChatMessage }) => (
    <View style={[
      styles.messageContainer,
      item.is_user_message ? styles.userMessage : styles.botMessage
    ]}>
      <Text style={[
        styles.messageText,
        item.is_user_message ? styles.userMessageText : styles.botMessageText
      ]}>
        {item.content}
      </Text>
      <Text style={styles.messageTime}>
        {new Date(item.created_at).toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        })}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <KeyboardAvoidingView 
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <FlatList<ChatMessage>
          ref={flatListRef}
          data={messages}
          keyExtractor={(item: ChatMessage) => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.messagesList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />

        {!sessionFinished && (
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.textInput}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Type your answer..."
              multiline
              maxLength={1000}
              editable={!loading}
            />
            <TouchableOpacity
              style={[styles.submitButton, (!inputText.trim() || loading) && styles.disabledButton]}
              onPress={submitAnswer}
              disabled={!inputText.trim() || loading}
            >
              {loading ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.submitButtonText}>Submit</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {sessionFinished && (
          <View style={styles.finishedContainer}>
            <Text style={styles.finishedText}>Session Complete!</Text>
            <TouchableOpacity
              style={styles.newSessionButton}
              onPress={() => navigation.navigate('TutoringStart')}
            >
              <Text style={styles.newSessionButtonText}>Start New Session</Text>
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  chatContainer: {
    flex: 1,
  },
  messagesList: {
    padding: 16,
    paddingBottom: 80,
  },
  messageContainer: {
    marginBottom: 16,
    maxWidth: '85%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#0b5fff',
    borderRadius: 18,
    borderBottomRightRadius: 4,
  },
  botMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#ffffff',
    borderRadius: 18,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
    padding: 12,
  },
  userMessageText: {
    color: '#ffffff',
  },
  botMessageText: {
    color: '#1a1a1a',
  },
  messageTime: {
    fontSize: 11,
    color: '#999999',
    paddingHorizontal: 12,
    paddingBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'flex-end',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    maxHeight: 100,
    marginRight: 8,
  },
  submitButton: {
    backgroundColor: '#10b981',
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  submitButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  finishedContainer: {
    padding: 24,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'center',
  },
  finishedText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#10b981',
    marginBottom: 16,
  },
  newSessionButton: {
    backgroundColor: '#0b5fff',
    borderRadius: 8,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  newSessionButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default TutoringSessionScreen;