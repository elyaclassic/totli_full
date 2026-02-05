// Dashboard JavaScript

// Check if logged in
if (!Session.isLoggedIn()) {
    window.location.href = '/static/pwa/login.html';
}

// Get user data
const user = Session.getUser();
const token = Session.getToken();

// Update UI with user info
document.getElementById('userName').textContent = user.full_name;

// Stats
let sentCount = 0;
let isTracking = false;
let trackingInterval = null;

// Initialize
async function init() {
    // Request GPS permission
    try {
        const position = await GPS.getCurrentPosition();
        updateLocationDisplay(position);

        // Start tracking
        startTracking();
    } catch (error) {
        console.error('GPS xatosi:', error);
        document.getElementById('gpsStatus').textContent = 'Test Rejim';
        document.getElementById('gpsIndicator').classList.remove('active');
        document.getElementById('gpsIndicator').classList.add('inactive');
    }

    // Update battery
    updateBattery();
}

// Update location display
function updateLocationDisplay(position) {
    const coords = position.coords;

    document.getElementById('currentLat').textContent = coords.latitude.toFixed(6);
    document.getElementById('currentLng').textContent = coords.longitude.toFixed(6);
    document.getElementById('currentAccuracy').textContent = Math.round(coords.accuracy) + 'm';
    document.getElementById('currentTime').textContent = new Date().toLocaleTimeString('uz-UZ');
}

// Update battery level
async function updateBattery() {
    const level = await GPS.getBatteryLevel();
    document.getElementById('batteryLevel').textContent = level + '%';

    // Update every minute
    setTimeout(updateBattery, 60000);
}

// Send location to server
async function sendLocation() {
    try {
        UI.showLoading();

        let position, battery;

        // Try to get real GPS
        try {
            position = await GPS.getCurrentPosition();
            battery = await GPS.getBatteryLevel();
        } catch (gpsError) {
            // GPS not available - use FAKE coordinates for testing
            console.warn('GPS mavjud emas, test koordinatalari ishlatilmoqda');

            // Fake position (Toshkent markazida)
            position = {
                coords: {
                    latitude: 41.311081 + (Math.random() - 0.5) * 0.01,
                    longitude: 69.240562 + (Math.random() - 0.5) * 0.01,
                    accuracy: 10
                }
            };
            battery = 100;

            // Show test mode indicator
            document.getElementById('gpsStatus').textContent = 'Test Rejim';
        }

        const result = await API.sendLocation(
            user.user_type,
            position.coords.latitude,
            position.coords.longitude,
            position.coords.accuracy,
            battery,
            token
        );

        UI.hideLoading();

        if (result.success) {
            sentCount++;
            document.getElementById('sentCount').textContent = sentCount;
            document.getElementById('lastSync').textContent = new Date().toLocaleTimeString('uz-UZ');

            updateLocationDisplay(position);

            console.log('Lokatsiya yuborildi:', result);
            alert('Lokatsiya muvaffaqiyatli yuborildi!');
        } else {
            console.error('Lokatsiya yuborishda xato:', result.error);
            alert('Xato: ' + (result.error || 'Noma\'lum xato'));
        }
    } catch (error) {
        UI.hideLoading();
        console.error('Xato:', error);
        console.error('Error details:', error.message, error.stack);
        alert('Xato: ' + error.message);
    }
}

// Lokatsiya yuborish intervali (millisekund) — har 5 daqiqa
const LOCATION_SEND_INTERVAL_MS = 5 * 60 * 1000;

// Start GPS tracking
function startTracking() {
    if (isTracking) return;

    isTracking = true;
    document.getElementById('trackingStatus').textContent = 'Faol (har 5 daqiqa)';
    document.getElementById('gpsIndicator').classList.add('active');
    document.getElementById('gpsIndicator').classList.remove('inactive');

    // Send immediately
    sendLocation();

    // Har 5 daqiqada avtomatik yuborish
    trackingInterval = setInterval(() => {
        sendLocation();
    }, LOCATION_SEND_INTERVAL_MS);

    // Start GPS watching
    GPS.startTracking((position) => {
        updateLocationDisplay(position);
    });
}

// Stop GPS tracking
function stopTracking() {
    if (!isTracking) return;

    isTracking = false;
    document.getElementById('trackingStatus').textContent = 'Toxtatilgan';
    document.getElementById('gpsIndicator').classList.remove('active');
    document.getElementById('gpsIndicator').classList.add('inactive');

    if (trackingInterval) {
        clearInterval(trackingInterval);
        trackingInterval = null;
    }

    GPS.stopTracking();
}

// Event Listeners

// Logout
document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm('Chiqishni xohlaysizmi?')) {
        stopTracking();
        Session.logout();
    }
});

// Manual send location
document.getElementById('sendLocationBtn').addEventListener('click', () => {
    alert('Tugma bosildi! GPS test boshlanmoqda...');
    sendLocation();
});

// Stop tracking
document.getElementById('stopTrackingBtn').addEventListener('click', () => {
    if (isTracking) {
        if (confirm('GPS trackingni toxtatishni xohlaysizmi?')) {
            stopTracking();
        }
    } else {
        startTracking();
    }
});

// View orders (Agent only)
document.getElementById('viewOrdersBtn').addEventListener('click', async () => {
    if (user.user_type !== 'agent') {
        alert('Faqat agentlar uchun');
        return;
    }

    UI.showLoading();
    try {
        const result = await API.getOrders(token);
        UI.hideLoading();

        if (result.success) {
            if (result.orders.length === 0) {
                alert('Buyurtmalar yoq');
            } else {
                let message = 'Buyurtmalar (' + result.orders.length + ' ta):\n\n';
                result.orders.slice(0, 5).forEach(order => {
                    message += order.partner_name + '\n';
                    message += 'Summa: ' + order.total + ' som\n';
                    message += 'Sana: ' + order.date + '\n\n';
                });
                alert(message);
            }
        } else {
            alert('Xato: ' + result.error);
        }
    } catch (error) {
        UI.hideLoading();
        alert('Xato: ' + error.message);
    }
});

// View partners (Agent only)
document.getElementById('viewPartnersBtn').addEventListener('click', async () => {
    if (user.user_type !== 'agent') {
        alert('Faqat agentlar uchun');
        return;
    }

    UI.showLoading();
    try {
        const result = await API.getPartners(token);
        UI.hideLoading();

        if (result.success) {
            if (result.partners.length === 0) {
                alert('Mijozlar yoq');
            } else {
                let message = 'Mijozlar (' + result.partners.length + ' ta):\n\n';
                result.partners.slice(0, 5).forEach(partner => {
                    message += partner.name + '\n';
                    message += 'Tel: ' + partner.phone + '\n';
                    message += 'Qarz: ' + partner.debt + ' som\n\n';
                });
                alert(message);
            }
        } else {
            alert('Xato: ' + result.error);
        }
    } catch (error) {
        UI.hideLoading();
        alert('Xato: ' + error.message);
    }
});

// Initialize on load
init();

// Handle page visibility
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Sahifa yashirildi');
    } else {
        console.log('Sahifa korsatildi');
        if (isTracking) {
            sendLocation();
        }
    }
});

 
 / /   L o g o u t   b u t t o n   h a n d l e r 
 
 d o c u m e n t . g e t E l e m e n t B y I d ( ' l o g o u t B t n ' ) . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( )   = >   { 
 
         i f   ( c o n f i r m ( ' C h i q i s h n i   x o h l a y s i z m i ? ' ) )   { 
 
                 S e s s i o n . c l e a r ( ) ; 
 
                 w i n d o w . l o c a t i o n . h r e f   =   ' / s t a t i c / p w a / l o g i n . h t m l ' ; 
 
         } 
 
 } ) ; 
 
 