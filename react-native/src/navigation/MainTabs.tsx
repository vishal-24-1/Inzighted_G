import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

// Import screens
import DocumentsListScreen from '../screens/Documents/DocumentsListScreen';
import ChatScreen from '../screens/Chat/ChatScreen';
import TutoringStartScreen from '../screens/Tutoring/TutoringStartScreen';
import TutoringSessionScreen from '../screens/Tutoring/TutoringSessionScreen';
import SessionListScreen from '../screens/Insights/SessionListScreen';
import SessionInsightScreen from '../screens/Insights/SessionInsightScreen';
import ProfileScreen from '../screens/Profile/ProfileScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

// Documents Stack
const DocumentsStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="DocumentsList" 
      component={DocumentsListScreen}
      options={{ headerShown: false }}
    />
  </Stack.Navigator>
);

// Chat Stack
const ChatStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="ChatMain" 
      component={ChatScreen}
      options={{ headerShown: false }}
    />
  </Stack.Navigator>
);

// Tutoring Stack
const TutoringStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="TutoringStart" 
      component={TutoringStartScreen}
      options={{ headerShown: false }}
    />
    <Stack.Screen 
      name="TutoringSession" 
      component={TutoringSessionScreen}
      options={{
        headerShown: true,
        title: 'Tutoring Session',
        headerBackTitleVisible: false,
      }}
    />
  </Stack.Navigator>
);

// Insights Stack
const InsightsStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="SessionList" 
      component={SessionListScreen}
      options={{ headerShown: false }}
    />
    <Stack.Screen
      name="SessionInsight"
      component={SessionInsightScreen}
      options={{
        headerShown: true,
        title: 'Session Insights',
        headerBackTitleVisible: false,
      }}
    />
  </Stack.Navigator>
);

// Profile Stack
const ProfileStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="ProfileMain" 
      component={ProfileScreen}
      options={{ headerShown: false }}
    />
  </Stack.Navigator>
);

const MainTabs: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#ffffff',
          borderTopWidth: 1,
          borderTopColor: '#e0e0e0',
          paddingBottom: 4,
          paddingTop: 4,
          height: 60,
        },
        tabBarActiveTintColor: '#0b5fff',
        tabBarInactiveTintColor: '#6b7280',
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
        },
      }}
    >
      <Tab.Screen 
        name="Documents" 
        component={DocumentsStack}
        options={{
          tabBarLabel: 'Documents',
          // Note: Icons would need react-native-vector-icons
          // tabBarIcon: ({ color, size }) => (
          //   <Icon name="file-text" size={size} color={color} />
          // ),
        }}
      />
      <Tab.Screen 
        name="Chat" 
        component={ChatStack}
        options={{
          tabBarLabel: 'Chat',
          // tabBarIcon: ({ color, size }) => (
          //   <Icon name="message-circle" size={size} color={color} />
          // ),
        }}
      />
      <Tab.Screen 
        name="Tutoring" 
        component={TutoringStack}
        options={{
          tabBarLabel: 'Tutoring',
          // tabBarIcon: ({ color, size }) => (
          //   <Icon name="book" size={size} color={color} />
          // ),
        }}
      />
      <Tab.Screen 
        name="Insights" 
        component={InsightsStack}
        options={{
          tabBarLabel: 'Insights',
          // tabBarIcon: ({ color, size }) => (
          //   <Icon name="bar-chart" size={size} color={color} />
          // ),
        }}
      />
      <Tab.Screen 
        name="Profile" 
        component={ProfileStack}
        options={{
          tabBarLabel: 'Profile',
          // tabBarIcon: ({ color, size }) => (
          //   <Icon name="user" size={size} color={color} />
          // ),
        }}
      />
    </Tab.Navigator>
  );
};

export default MainTabs;