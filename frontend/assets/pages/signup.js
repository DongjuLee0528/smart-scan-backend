// Initialize page components
smartscanCommon.initLucideIcons();
smartscanCommon.initDarkModeToggle();

const form = document.getElementById('signup-form');
const submitBtn = document.getElementById('signup-submit');
const errorBox = document.getElementById('signup-error');
const successBox = document.getElementById('signup-success');

function showError(msg) {
  smartscanCommon.clearSuccess('signup-success');
  smartscanCommon.showError('signup-error', msg);
}
function showSuccess(msg) {
  smartscanCommon.clearError('signup-error');
  smartscanCommon.showSuccess('signup-success', msg);
}
function clearBanners() {
  smartscanCommon.clearError('signup-error');
  smartscanCommon.clearSuccess('signup-success');
}

// Handle signup form submission
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearBanners();

  const name = document.getElementById('name').value.trim();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const passwordConfirm = document.getElementById('password-confirm').value;
  const phoneRaw = document.getElementById('phone').value.trim();
  const ageRaw = document.getElementById('age').value.trim();
  const terms = document.getElementById('terms').checked;

  if (!name || !email || !password) {
    showError('Name, email, and password are required fields.');
    return;
  }
  if (password.length < 8) {
    showError('Password must be at least 8 characters long.');
    return;
  }
  if (password !== passwordConfirm) {
    showError('Passwords do not match.');
    return;
  }
  if (!terms) {
    showError('Please agree to the terms of service and privacy policy.');
    return;
  }

  const phone = phoneRaw || null;
  const age = ageRaw ? parseInt(ageRaw, 10) : null;

  smartscanCommon.setButtonLoading('signup-submit', true, 'Signing up...');

  try {
    await smartscanApi.register({
      name,
      email,
      password,
      phone,
      age,
    });
    showSuccess('Registration completed successfully. Redirecting to login page...');
    setTimeout(() => location.replace('login.html'), 1200);
  } catch (err) {
    const msg = (err && err.message) ? err.message : 'An error occurred during registration.';
    showError(msg);
    smartscanCommon.setButtonLoading('signup-submit', false);
  }
});