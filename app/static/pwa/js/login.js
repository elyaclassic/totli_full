// Login Page JavaScript

let selectedUserType = 'agent';

// Check if already logged in
if (Session.isLoggedIn()) {
    window.location.href = '/static/pwa/dashboard.html';
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

        // Add active class to clicked tab
        this.classList.add('active');

        // Update selected user type
        selectedUserType = this.dataset.type;

        // Hide error
        UI.hideError();
    });
});

// Toggle password visibility
document.getElementById('togglePassword')?.addEventListener('click', function () {
    const passwordInput = document.getElementById('password');
    const icon = this.querySelector('i');

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
});

// Login form submission
document.getElementById('loginForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // Validation
    if (!username || !password) {
        UI.showError('Iltimos, barcha maydonlarni to\'ldiring');
        return;
    }

    // Show loading
    UI.showLoading();
    UI.hideError();

    try {
        // Call API
        const result = await API.login(selectedUserType, username, password);

        if (result.success) {
            // Save session
            Session.save(result.user, result.token);

            // Redirect to dashboard
            window.location.href = '/static/pwa/dashboard.html';
        } else {
            UI.hideLoading();
            UI.showError(result.error || 'Login xatosi');
        }
    } catch (error) {
        UI.hideLoading();
        UI.showError('Serverga ulanishda xatolik: ' + error.message);
        console.error('Login error:', error);
    }
});

// Auto-fill for testing (remove in production)
if (window.location.hostname === 'localhost' || window.location.hostname === '10.243.49.144') {
    document.getElementById('username').value = '+998901111111';
    document.getElementById('password').value = 'test';
}
