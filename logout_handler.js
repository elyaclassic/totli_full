
// Logout button handler
document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm('Chiqishni xohlaysizmi?')) {
        Session.clear();
        window.location.href = '/static/pwa/login.html';
    }
});
