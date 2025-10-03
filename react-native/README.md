# Inzighted Mobile App

A React Native mobile application that provides AI-powered tutoring and document analysis capabilities. This mobile app replicates all features from the web application and integrates with the existing Django backend.

## Features

- **Authentication**: JWT-based login/registration with token refresh
- **Document Management**: Upload and manage PDF/Word documents
- **AI Chat**: Interactive chat with uploaded documents using RAG
- **Tutoring Sessions**: Structured tutoring sessions with AI-generated questions
- **Insights**: SWOT analysis and learning progress tracking
- **Profile Management**: User profile and account settings

## Project Structure

```
react-native/
├── android/                 # Android-specific files
├── ios/                     # iOS-specific files (if needed)
├── src/
│   ├── components/         # Reusable UI components
│   ├── context/           # React Context (Auth)
│   ├── navigation/        # Navigation configuration
│   ├── screens/          # Screen components
│   │   ├── Auth/         # Login/Register screens
│   │   ├── Chat/         # Chat functionality
│   │   ├── Documents/    # Document management
│   │   ├── Insights/     # Session insights
│   │   ├── Profile/      # User profile
│   │   └── Tutoring/     # Tutoring sessions
│   ├── services/         # API calls and utilities
│   ├── types/           # TypeScript type definitions
│   └── utils/           # Utility functions
├── App.tsx              # Main app component
├── index.js            # Entry point
└── package.json        # Dependencies and scripts
```

## Prerequisites

- Node.js 18+
- React Native CLI
- Android Studio (for Android development)
- JDK 11 or newer
- Android SDK

## Setup Instructions

### 1. Install React Native CLI

```powershell
npm install -g react-native-cli
```

### 2. Install Dependencies

```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor\react-native
npm install
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
API_BASE_URL=http://10.0.2.2:8000/api  # For Android emulator
PRODUCT_URL=http://10.0.2.2:3000

# For physical device, use your computer's IP address:
# API_BASE_URL=http://192.168.1.100:8000/api
# PRODUCT_URL=http://192.168.1.100:3000
```

### 4. Android Setup

#### Install Android Studio
1. Download and install Android Studio
2. Open Android Studio and install SDK Platform 33 (API Level 33)
3. Install Android SDK Build-Tools
4. Set up Android Virtual Device (AVD) or connect physical device

#### Configure Environment Variables (Windows)
```powershell
# Add to system environment variables
$env:ANDROID_HOME = "C:\Users\[USERNAME]\AppData\Local\Android\Sdk"
$env:PATH += ";$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\tools"
```

### 5. Install Additional Dependencies

Some native dependencies require manual linking:

```powershell
# Install pods for iOS (if building for iOS)
# cd ios && pod install && cd ..

# For Android, the dependencies should auto-link
```

## Development

### Start Metro Bundler

```powershell
npm start
```

### Run on Android

```powershell
# Start Android emulator or connect device
npm run android
```

### Run on iOS (macOS only)

```powershell
npm run ios
```

## Backend Integration

The app connects to the existing Django backend. Make sure:

1. Backend is running on `http://localhost:8000`
2. CORS settings allow mobile app origins
3. All API endpoints are accessible

### API Endpoints Used

- `POST /auth/login/` - User login
- `POST /auth/register/` - User registration
- `POST /auth/refresh/` - Token refresh
- `GET /auth/profile/` - Get user profile
- `PUT /auth/profile/` - Update profile
- `GET /documents/` - List documents
- `POST /ingest/` - Upload documents
- `POST /query/` - RAG queries
- `POST /chat/` - Chat messages
- `POST /tutoring/start/` - Start tutoring session
- `POST /tutoring/{id}/answer/` - Submit answers
- `POST /tutoring/{id}/end/` - End session
- `GET /sessions/` - List sessions
- `GET /sessions/{id}/insights/` - Get insights

## File Upload Configuration

The app uses:
- `react-native-document-picker` for PDF/Word documents
- `react-native-image-picker` for images
- FormData for multipart uploads to backend

### Permissions Required

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.CAMERA" />
```

## Testing

### Run Tests

```powershell
npm test
```

### Test Structure

```
__tests__/
├── components/
├── screens/
├── services/
└── utils/
```

### Example Test

```typescript
import { render, screen } from '@testing-library/react-native';
import LoginScreen from '../src/screens/Auth/LoginScreen';

test('renders login form', () => {
  render(<LoginScreen />);
  expect(screen.getByPlaceholderText('Email')).toBeTruthy();
  expect(screen.getByPlaceholderText('Password')).toBeTruthy();
});
```

## Building for Production

### Debug Build

```powershell
npm run build:android
```

### Release Build (Signed)

1. Generate signing key:
```powershell
keytool -genkeypair -v -keystore my-upload-key.keystore -alias my-key-alias -keyalg RSA -keysize 2048 -validity 10000
```

2. Configure `android/gradle.properties`:
```properties
MYAPP_UPLOAD_STORE_FILE=my-upload-key.keystore
MYAPP_UPLOAD_KEY_ALIAS=my-key-alias
MYAPP_UPLOAD_STORE_PASSWORD=*****
MYAPP_UPLOAD_KEY_PASSWORD=*****
```

3. Update `android/app/build.gradle`:
```gradle
android {
    ...
    signingConfigs {
        release {
            if (project.hasProperty('MYAPP_UPLOAD_STORE_FILE')) {
                storeFile file(MYAPP_UPLOAD_STORE_FILE)
                storePassword MYAPP_UPLOAD_STORE_PASSWORD
                keyAlias MYAPP_UPLOAD_KEY_ALIAS
                keyPassword MYAPP_UPLOAD_KEY_PASSWORD
            }
        }
    }
    buildTypes {
        release {
            ...
            signingConfig signingConfigs.release
        }
    }
}
```

4. Build signed APK:
```powershell
cd android
.\gradlew assembleRelease
```

5. Build signed AAB (recommended for Play Store):
```powershell
cd android
.\gradlew bundleRelease
```

### Generated Files

- APK: `android/app/build/outputs/apk/release/app-release.apk`
- AAB: `android/app/build/outputs/bundle/release/app-release.aab`

## Play Store Deployment

### Prepare for Release

1. **App Icon**: Place app icons in `android/app/src/main/res/mipmap-*/`
2. **Splash Screen**: Configure splash screen assets
3. **Version**: Update `versionCode` and `versionName` in `android/app/build.gradle`
4. **Permissions**: Review and minimize requested permissions
5. **Privacy Policy**: Required for apps handling user data

### Upload to Play Console

1. Create Google Play Console account
2. Create new application
3. Upload AAB file
4. Complete store listing (description, screenshots, etc.)
5. Set content rating and pricing
6. Submit for review

### Store Listing Requirements

- **Title**: Inzighted - AI Tutoring
- **Short Description**: AI-powered tutoring and document analysis
- **Full Description**: Detailed feature list and benefits
- **Screenshots**: Multiple device screenshots showing key features
- **Feature Graphic**: 1024x500px promotional banner
- **App Icon**: 512x512px high-resolution icon

## Troubleshooting

### Common Issues

1. **Metro bundler issues**:
```powershell
npx react-native start --reset-cache
```

2. **Android build failures**:
```powershell
cd android
.\gradlew clean
cd ..
npm run android
```

3. **Network requests failing**:
   - Check API_BASE_URL configuration
   - Verify backend CORS settings
   - Test with physical device using computer's IP address

4. **File upload issues**:
   - Verify permissions in AndroidManifest.xml
   - Check backend file size limits
   - Test with smaller files first

### Debugging

1. **Enable debugging**:
```powershell
adb shell input keyevent 82  # Open dev menu on device
```

2. **View logs**:
```powershell
npx react-native log-android
```

3. **Chrome DevTools**:
   - Open Chrome
   - Navigate to `chrome://inspect`
   - Select your app from the list

## Performance Optimization

### Bundle Size Optimization

1. Enable Proguard/R8 in release builds
2. Use vector drawables for icons
3. Optimize images and assets
4. Remove unused dependencies

### Runtime Performance

1. Use FlatList for large lists
2. Implement proper key props
3. Avoid inline functions in render
4. Use React.memo for expensive components

## Security Considerations

1. **Token Storage**: Uses secure AsyncStorage
2. **API Communication**: HTTPS in production
3. **Input Validation**: Client and server-side validation
4. **File Uploads**: Size and type restrictions
5. **Error Handling**: Don't expose sensitive information

## Future Enhancements

1. **Offline Mode**: Cache documents and messages
2. **Push Notifications**: Session reminders and insights
3. **Dark Mode**: Theme switching
4. **Accessibility**: Screen reader support
5. **Biometric Auth**: Fingerprint/Face ID login
6. **Deep Linking**: Direct links to specific content

## Support

For technical support or questions:
- Check the backend API documentation
- Review React Native troubleshooting guide
- Test with the web application for comparison

## License

This project is part of the Inzighted platform and follows the same licensing terms as the main application.