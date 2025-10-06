const { GenerateSW } = require('workbox-webpack-plugin');

// Only add the service worker generation in production builds.
// Generating a service worker during webpack --watch / dev server can cause
// GenerateSW to be called multiple times and produce the warning seen in dev.
// More importantly, an active dev service worker can intercept requests
// (including favicon) and serve stale or incorrect responses from an
// inconsistent precache manifest.
const pluginsAdd = [];

if (process.env.NODE_ENV === 'production') {
  pluginsAdd.push(
    new GenerateSW({
      clientsClaim: true,
      skipWaiting: true,
      swDest: 'service-worker.js',
      exclude: [/\.map$/, /manifest$/, /\.htaccess$/, /service-worker\.js$/],
      maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
      runtimeCaching: [
        {
          urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-cache',
            expiration: {
              maxEntries: 60,
              maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
            },
          },
        },
        {
          urlPattern: ({ request }) => request.destination === 'image',
          handler: 'CacheFirst',
          options: {
            cacheName: 'images',
            expiration: {
              maxEntries: 60,
              maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
            },
          },
        },
        {
          urlPattern: ({ url }) => url.origin === 'https://fonts.googleapis.com',
          handler: 'StaleWhileRevalidate',
          options: {
            cacheName: 'google-fonts-stylesheets',
          },
        },
        {
          urlPattern: ({ url }) => url.origin === 'https://fonts.gstatic.com',
          handler: 'CacheFirst',
          options: {
            cacheName: 'google-fonts-webfonts',
            expiration: {
              maxEntries: 30,
              maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
            },
          },
        },
      ],
    })
  );
}

module.exports = {
  style: {
    // This setting tells CRACO to read the postcss.config.js file
    postcss: {
      mode: 'file',
    },
  },
  webpack: {
    plugins: {
      add: pluginsAdd,
    },
  },
};