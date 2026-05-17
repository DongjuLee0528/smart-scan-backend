/**
 * Kakao account linking page functionality
 *
 * Handles magic link token verification and Kakao account linking process.
 * Processes JWT tokens for secure account association between web and KakaoTalk.
 */

// Initialize page components
smartscanCommon.initLucideIcons();
smartscanCommon.initDarkModeToggle();

const loading = document.getElementById('state-loading');
const success = document.getElementById('state-success');
const errorEl = document.getElementById('state-error');
const errorMsg = document.getElementById('error-message');

// Show specific state element while hiding others
function show(el) {
  [loading, success, errorEl].forEach(e => e.classList.add('hidden'));
  el.classList.remove('hidden');
  el.classList.add('flex');
}

function showError(msg) {
  if (msg) errorMsg.textContent = msg;
  show(errorEl);
}

// Main execution function to handle Kakao linking process
(async function run() {
  const params = new URLSearchParams(location.search);
  const token = params.get('token');

  if (!token) {
    showError('Link token not found. Please access via the link received from KakaoTalk.');
    return;
  }

  // Redirect to login if not authenticated
  if (!smartscanApi.isLoggedIn()) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    location.replace(`login.html?redirect=${redirect}`);
    return;
  }

  try {
    await smartscanApi.linkKakao(token);
    show(success);
  } catch (err) {
    let msg = 'Link has expired or is invalid.';
    if (err) {
      if (err.status === 401) {
        smartscanApi.clearTokens();
        const redirect = encodeURIComponent(location.pathname + location.search);
        location.replace(`login.html?redirect=${redirect}`);
        return;
      }
      if (err.message) msg = err.message;
    }
    showError(msg);
  }
})();