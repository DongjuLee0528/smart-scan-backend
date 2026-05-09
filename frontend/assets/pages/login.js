// Initialize page components
smartscanCommon.initLucideIcons();
smartscanCommon.initDarkModeToggle();

const form = document.getElementById('login-form');
const submitBtn = document.getElementById('login-submit');
const errorBox = document.getElementById('login-error');

function showError(msg) {
  smartscanCommon.showError('login-error', msg);
}
function clearError() {
  smartscanCommon.clearError('login-error');
}

// Redirect if already logged in
if (smartscanApi.isLoggedIn()) {
  location.replace(smartscanCommon.getRedirectTarget());
}

// Handle login form submission
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  if (!email || !password) {
    showError('Please enter email and password.');
    return;
  }

  smartscanCommon.setButtonLoading('login-submit', true, 'Logging in...');

  try {
    await smartscanApi.login(email, password);
    location.replace(smartscanCommon.getRedirectTarget());
  } catch (err) {
    const msg =
      (err && err.status === 401) ? 'Email or password is incorrect.' :
      (err && err.message) ? err.message :
      'An error occurred during login.';
    showError(msg);
    smartscanCommon.setButtonLoading('login-submit', false);
  }
});