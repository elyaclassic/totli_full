// API Configuration
const API_BASE_URL = window.location.origin;

// API Helper Functions
const API = {
    // Login
    async login(userType, username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/api/${userType}/login`, {
            method: 'POST',
            body: formData
        });

        return await response.json();
    },

    // Send Location
    async sendLocation(userType, latitude, longitude, accuracy, battery, token) {
        console.log('=== SENDING LOCATION ===');
        console.log('User Type:', userType);
        console.log('Latitude:', latitude);
        console.log('Longitude:', longitude);
        console.log('Accuracy:', accuracy);
        console.log('Battery:', battery);
        console.log('Token:', token ? token.substring(0, 20) + '...' : 'NO TOKEN');

        const formData = new FormData();
        formData.append('latitude', latitude);
        formData.append('longitude', longitude);
        formData.append('accuracy', accuracy || 0);
        formData.append('battery', battery || 100);
        formData.append('token', token);

        const url = `${API_BASE_URL}/api/${userType}/location`;
        console.log('URL:', url);

        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('Response Status:', response.status);
        console.log('Response:', result);

        return result;
    },

    // Get Orders (Agent only)
    async getOrders(token) {
        const response = await fetch(`${API_BASE_URL}/api/agent/orders?token=${encodeURIComponent(token)}`);
        return await response.json();
    },

    // Get Partners (Agent only)
    async getPartners(token) {
        const response = await fetch(`${API_BASE_URL}/api/agent/partners?token=${encodeURIComponent(token)}`);
        return await response.json();
    }
};

// Storage Helper
const Storage = {
    set(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    },

    get(key) {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : null;
    },

    remove(key) {
        localStorage.removeItem(key);
    },

    clear() {
        localStorage.clear();
    }
};

// Session Management
const Session = {
    save(userData, token) {
        Storage.set('user', userData);
        Storage.set('token', token);
        Storage.set('loginTime', new Date().toISOString());
    },

    getUser() {
        return Storage.get('user');
    },

    getToken() {
        return Storage.get('token');
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    logout() {
        Storage.clear();
        window.location.href = '/static/pwa/login.html';
    }
};

// UI Helper
const UI = {
    showLoading() {
        document.getElementById('loadingOverlay')?.classList.remove('d-none');
    },

    hideLoading() {
        document.getElementById('loadingOverlay')?.classList.add('d-none');
    },

    showError(message, elementId = 'errorMessage') {
        const errorEl = document.getElementById(elementId);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('d-none');
        }
    },

    hideError(elementId = 'errorMessage') {
        const errorEl = document.getElementById(elementId);
        if (errorEl) {
            errorEl.classList.add('d-none');
        }
    },

    showSuccess(message) {
        // Simple alert for now
        alert(message);
    }
};

// GPS Helper
const GPS = {
    watchId: null,
    lastPosition: null,

    async getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('GPS qo\'llab-quvvatlanmaydi'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                position => resolve(position),
                error => reject(error),
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    },

    startTracking(callback) {
        if (!navigator.geolocation) {
            console.error('GPS qo\'llab-quvvatlanmaydi');
            return;
        }

        this.watchId = navigator.geolocation.watchPosition(
            position => {
                this.lastPosition = position;
                if (callback) callback(position);
            },
            error => console.error('GPS xatosi:', error),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000
            }
        );
    },

    stopTracking() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
    },

    async getBatteryLevel() {
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                return Math.round(battery.level * 100);
            } catch (e) {
                return 100;
            }
        }
        return 100;
    }
};

// Export for use in other files
window.API = API;
window.Storage = Storage;
window.Session = Session;
window.UI = UI;
window.GPS = GPS;
