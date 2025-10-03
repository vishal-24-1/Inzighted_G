import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, Alert } from 'react-native';
import { insightsAPI } from '../../services/api';

interface RouteProps {
  route: any;
  navigation: any;
}

const parseSwotField = (value: any): string[] | string => {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string') return [String(value)];

  const s = value.trim();
  if (s.startsWith('[') && s.endsWith(']')) {
    try {
      return JSON.parse(s);
    } catch (e) {
      try {
        const jsonLike = s.replace(/'/g, '"');
        return JSON.parse(jsonLike);
      } catch (_) {
        const inner = s.slice(1, -1);
        return inner.split(/\s*,\s*/).map(p => p.replace(/^['"]|['"]$/g, '').trim()).filter(Boolean);
      }
    }
  }

  // Not a list -> return as single-item array
  return [s];
};

const SessionInsightScreen: React.FC<RouteProps> = ({ route, navigation }) => {
  const { sessionId } = route.params || {};
  const [loading, setLoading] = useState(true);
  const [insight, setInsight] = useState<any>(null);

  useEffect(() => {
    if (!sessionId) {
      Alert.alert('Error', 'No session id provided');
      navigation.goBack();
      return;
    }

    const load = async () => {
      setLoading(true);
      try {
        const resp = await insightsAPI.getSessionInsights(sessionId);
        const data = resp.data;
        data.insights = {
          strength: parseSwotField(data.insights?.strength),
          weakness: parseSwotField(data.insights?.weakness),
          opportunity: parseSwotField(data.insights?.opportunity),
          threat: parseSwotField(data.insights?.threat),
        };
        setInsight(data);
      } catch (err: any) {
        console.error('Failed to load insights', err);
        Alert.alert('Error', err?.response?.data?.message || 'Failed to load insights');
        navigation.goBack();
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [sessionId]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0b5fff" />
      </View>
    );
  }

  if (!insight) {
    return (
      <View style={styles.center}>
        <Text>No insights available.</Text>
      </View>
    );
  }

  const renderPoints = (val: any) => {
    if (Array.isArray(val)) {
      return val.map((v, i) => (
        <Text key={i} style={styles.pointText}>• {v}</Text>
      ));
    }
    if (!val) return null;
    return <Text style={styles.pointText}>{String(val)}</Text>;
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Insights</Text>
      <Text style={styles.subtitle}>{insight.session_title || 'Session'}</Text>

      <View style={[styles.card, { borderLeftColor: '#28a745' }]}>
        <Text style={styles.cardTitle}>Strength</Text>
        {renderPoints(insight.insights.strength)}
      </View>

      <View style={[styles.card, { borderLeftColor: '#dc3545' }]}>
        <Text style={styles.cardTitle}>Weakness</Text>
        {renderPoints(insight.insights.weakness)}
      </View>

      <View style={[styles.card, { borderLeftColor: '#007bff' }]}>
        <Text style={styles.cardTitle}>Opportunity</Text>
        {renderPoints(insight.insights.opportunity)}
      </View>

      <View style={[styles.card, { borderLeftColor: '#fd7e14' }]}>
        <Text style={styles.cardTitle}>Threat</Text>
        {renderPoints(insight.insights.threat)}
      </View>

    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  content: { padding: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#666666', marginBottom: 12 },
  card: { backgroundColor: '#fff', padding: 16, borderRadius: 10, marginBottom: 12, borderLeftWidth: 6 },
  cardTitle: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
  pointText: { fontSize: 15, color: '#333', marginBottom: 6 },
});

export default SessionInsightScreen;
