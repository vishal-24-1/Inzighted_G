// Temporary module declarations to satisfy TypeScript in the editor
// These are safe fallbacks while proper @react-navigation packages/types are installed.

declare module '@react-navigation/native' {
  import { ComponentType } from 'react';
  export const NavigationContainer: ComponentType<any>;
  export function useNavigation(): any;
  export function useRoute(): any;
  export function useFocusEffect(cb: any): any;
  export * from 'react';
}

declare module '@react-navigation/native-stack' {
  import { ComponentType } from 'react';
  export const createNativeStackNavigator: any;
  export const NativeStackNavigator: ComponentType<any>;
}

declare module '@react-navigation/bottom-tabs' {
  import { ComponentType } from 'react';
  export const createBottomTabNavigator: any;
  export const BottomTabBar: ComponentType<any>;
}

// Fallback for any other react-navigation submodules that might appear
declare module '@react-navigation/*';

// Temporary declarations for react-native and react to silence editor errors
declare module 'react-native' {
  import * as React from 'react';
  export * from 'react';
  export const View: any;
  export const Text: any;
  export const ScrollView: any;
  export const Platform: any;
  export const RefreshControl: any;
  export const StyleSheet: any;
  export const ActivityIndicator: any;
  export const Alert: any;
  export const TouchableOpacity: any;
  export const FlatList: any;
  // Allow using FlatList as a type (e.g. FlatList<ItemType>) in TS files
  export type FlatList<T = any> = any;
  export const TextInput: any;
  export const KeyboardAvoidingView: any;
  export default React;
}

// Do not declare 'react' here; rely on @types/react when installed.
