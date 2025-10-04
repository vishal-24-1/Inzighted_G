// Service Worker Registration with Workbox
// This file handles PWA service worker registration with graceful fallbacks

import { Workbox } from 'workbox-window';

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(
    /^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/
  )
);

type Config = {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
};

export function register(config?: Config) {
  if ('serviceWorker' in navigator) {
    const wb = new Workbox('/service-worker.js');

    wb.addEventListener('installed', event => {
      if (event.isUpdate) {
        if (config && config.onUpdate && event.sw) {
          // For update callback, we'll pass a mock registration object
          navigator.serviceWorker.ready.then(registration => {
            config.onUpdate!(registration);
          });
        }
        // Show a "New content available" notification
        console.log('New content is available; please refresh.');
      } else {
        if (config && config.onSuccess && event.sw) {
          // For success callback, we'll pass a mock registration object
          navigator.serviceWorker.ready.then(registration => {
            config.onSuccess!(registration);
          });
        }
        console.log('Content is cached for offline use.');
      }
    });

    wb.addEventListener('waiting', event => {
      console.log('A new service worker has installed, but it can\'t activate until all tabs running the current version have been unloaded.');
    });

    wb.addEventListener('controlling', event => {
      console.log('Service worker is now controlling the page.');
      window.location.reload();
    });

    wb.addEventListener('activated', event => {
      console.log('Service worker activated.');
    });

    // Register the service worker
    wb.register().catch(error => {
      console.error('Service worker registration failed:', error);
    });
  }
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then(registration => {
        registration.unregister();
      })
      .catch(error => {
        console.error(error.message);
      });
  }
}

// Check if the app can be installed
export function checkInstallPrompt() {
  let deferredPrompt: any;

  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent Chrome 67 and earlier from automatically showing the prompt
    e.preventDefault();
    // Stash the event so it can be triggered later
    deferredPrompt = e;
    
    // Show install button or banner
    console.log('App can be installed');
    
    // You can dispatch a custom event here to show install UI
    window.dispatchEvent(new CustomEvent('appinstallable'));
  });

  window.addEventListener('appinstalled', () => {
    console.log('App was installed');
    deferredPrompt = null;
  });

  return {
    showInstallPrompt: () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult: any) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the install prompt');
          } else {
            console.log('User dismissed the install prompt');
          }
          deferredPrompt = null;
        });
      }
    }
  };
}