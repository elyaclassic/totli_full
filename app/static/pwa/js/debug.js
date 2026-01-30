// Test script - add to dashboard.js temporarily

console.log('=== PWA DEBUG START ===');
console.log('User:', user);
console.log('Token:', token);
console.log('Navigator.geolocation:', navigator.geolocation);

// Test battery
navigator.getBattery().then(battery => {
    console.log('Battery level:', Math.round(battery.level * 100) + '%');
    console.log('Battery charging:', battery.charging);
}).catch(e => {
    console.log('Battery API error:', e);
});

// Test GPS
navigator.geolocation.getCurrentPosition(
    position => {
        console.log('GPS SUCCESS:', position.coords);
        alert('GPS ishlayapti! Lat: ' + position.coords.latitude);
    },
    error => {
        console.log('GPS ERROR:', error);
        alert('GPS xatosi: ' + error.message);
    },
    {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
    }
);

console.log('=== PWA DEBUG END ===');
