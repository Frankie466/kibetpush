const CACHE_NAME = 'starlink-pwa-v1.0';
const OFFLINE_URL = '/offline/';

// Critical assets to cache (app shell)
const urlsToCache = [
    '/',
    OFFLINE_URL,
    '/manifest.json',
    // Essential icons
    '/static/icons/icon-72x72.png',
    '/static/icons/icon-96x96.png',
    '/static/icons/icon-128x128.png',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
];

// Install event
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing Starlink PWA...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[Service Worker] Caching app shell');
                return cache.addAll(urlsToCache);
            })
            .then(() => {
                console.log('[Service Worker] Install completed');
                return self.skipWaiting();
            })
    );
});

// Activate event
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        })
        .then(() => {
            console.log('[Service Worker] Activation completed');
            return self.clients.claim();
        })
    );
});

// Fetch event
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip browser extensions
    if (event.request.url.startsWith('chrome-extension://') || 
        event.request.url.startsWith('moz-extension://')) return;
    
    // ⭐ IMPORTANT: Skip M-Pesa API calls from caching
    // Your M-Pesa endpoints are:
    // - /mpesa/stk_push/
    // - /mpesa/callback/
    if (event.request.url.includes('/mpesa/stk_push/') || 
        event.request.url.includes('/mpesa/callback/')) {
        event.respondWith(
            fetch(event.request)
                .catch(error => {
                    console.log('[Service Worker] M-Pesa API fetch failed:', error);
                    return new Response(
                        JSON.stringify({ 
                            status: 'error', 
                            message: 'Network error. Please check your connection.' 
                        }),
                        { 
                            status: 503,
                            headers: { 'Content-Type': 'application/json' }
                        }
                    );
                })
        );
        return;
    }
    
    // For HTML navigation requests
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    // Show offline page when network fails
                    return caches.match(OFFLINE_URL);
                })
        );
        return;
    }
    
    // For static assets (CSS, JS, images, etc.)
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if found
                if (response) {
                    return response;
                }
                
                // Otherwise fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache if response is invalid
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response for caching
                        const responseToCache = response.clone();
                        
                        // Cache for future use
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(error => {
                        console.log('[Service Worker] Fetch failed for:', event.request.url, error);
                        
                        // Return placeholder for missing images
                        if (event.request.destination === 'image') {
                            return caches.match('/static/icons/icon-192x192.png');
                        }
                        
                        // For other failed requests, let them fail normally
                        throw error;
                    });
            })
    );
});

// ========================================
// Optional: Push Notifications for Payment Reminders
// ========================================
self.addEventListener('push', event => {
    let notificationData = {
        title: 'Starlink Kenya',
        body: 'New update available',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            url: '/',
            timestamp: Date.now()
        }
    };
    
    // Try to parse push data
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
        } catch (e) {
            notificationData.body = event.data.text() || notificationData.body;
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            vibrate: notificationData.vibrate,
            data: notificationData.data,
            actions: [
                {
                    action: 'view',
                    title: 'View'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ]
        })
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('[Service Worker] Notification click:', event.action);
    
    event.notification.close();
    
    // Handle different actions
    if (event.action === 'view' || event.action === '') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
    // For dismiss action, just close the notification
});

// Handle push subscription changes
self.addEventListener('pushsubscriptionchange', event => {
    console.log('[Service Worker] Push subscription changed');
    
    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array('YOUR_PUBLIC_VAPID_KEY_HERE') // Add if using VAPID
        })
        .then(newSubscription => {
            // Send new subscription to your server
            return fetch('/api/push-subscription/', {
                method: 'POST',
                body: JSON.stringify(newSubscription),
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        })
    );
});

// Helper function for VAPID keys (optional)
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// ========================================
// Background Sync (optional - for offline payments)
// ========================================
self.addEventListener('sync', event => {
    console.log('[Service Worker] Background sync:', event.tag);
    
    if (event.tag === 'sync-payments') {
        event.waitUntil(
            // Implement your payment sync logic here
            syncPendingPayments()
        );
    }
});

async function syncPendingPayments() {
    // This would sync pending payments when connection is restored
    console.log('[Service Worker] Syncing pending payments...');
    // Implementation depends on your app's architecture
}