# Troubleshooting: "Cannot read properties of null (reading 'useContext')"

## Issue
Getting runtime error: `Cannot read properties of null (reading 'useContext')` when starting the app.

## Root Cause
This error typically occurs when:
1. React context is being accessed before the provider is mounted
2. Hot module reloading causes context to become stale
3. Multiple versions of React are loaded

## Solutions

### Solution 1: Clear Cache and Restart (Recommended)

```powershell
# Stop the dev server (Ctrl+C)

# Clear node modules cache
cd frontend
npm cache clean --force

# Delete and reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm install

# Restart
npm start
```

### Solution 2: Hard Browser Refresh

1. Open the app in browser
2. Press `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
3. Or open DevTools (F12) → Right-click refresh button → "Empty Cache and Hard Reload"

### Solution 3: Check React Version

```powershell
cd frontend
npm ls react react-dom
```

Ensure only ONE version of React is installed. If you see multiple, fix with:

```powershell
npm dedupe
npm install
```

### Solution 4: Clean Build

```powershell
cd frontend

# Delete build artifacts
Remove-Item -Recurse -Force build
Remove-Item -Recurse -Force node_modules/.cache

# Restart dev server
npm start
```

### Solution 5: Check for Circular Dependencies

The error can also occur if there's a circular import. Our code structure is:
- `App.tsx` wraps everything in `<AuthProvider>`
- `Home.tsx` uses `useAuth()` hook
- `OnboardingManager.tsx` receives `userId` as prop (no hook usage)

This should work correctly. If it doesn't, check for:
- Circular imports between files
- Multiple React instances in node_modules

### Solution 6: Verify App.tsx Structure

Make sure `App.tsx` looks like this:

```tsx
import { AuthProvider } from './utils/AuthContext';

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={
              <PrivateRoute>
                <Home />
              </PrivateRoute>
            } />
            {/* ... other routes */}
          </Routes>
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}
```

### Solution 7: Disable Fast Refresh Temporarily

Add to `package.json`:

```json
{
  "scripts": {
    "start": "FAST_REFRESH=false craco start"
  }
}
```

Or in PowerShell:

```powershell
$env:FAST_REFRESH="false"
npm start
```

## Prevention

To avoid this issue in the future:

1. **Always clear cache after installing new packages**
   ```powershell
   npm install <package> && npm start
   ```

2. **Use consistent React versions**
   - Check `package.json` for React version consistency
   - Avoid mixing React 18 and 19

3. **Avoid circular imports**
   - Keep context providers at the top level
   - Don't import context in files that define context

4. **Test with clean state**
   ```powershell
   # Before committing changes
   Remove-Item -Recurse -Force node_modules
   npm install
   npm start
   ```

## Quick Test

After applying any solution:

1. Navigate to http://localhost:3000
2. Check browser console for errors
3. Try logging in/registering
4. Verify Home page loads
5. Check if onboarding appears

## Still Having Issues?

If none of these work:

1. Check terminal for TypeScript compilation errors
2. Look for warnings about duplicate packages
3. Try in a different browser
4. Create a new user profile in browser
5. Check if antivirus is blocking files

## Common Error Messages

| Error | Solution |
|-------|----------|
| "useContext is null" | Solution 1 (Clear cache) |
| "Cannot read properties of null" | Solution 2 (Hard refresh) |
| "Multiple versions of React" | Solution 3 (Dedupe) |
| "Module not found" | Solution 4 (Clean build) |

---

**Last Updated**: October 21, 2025
