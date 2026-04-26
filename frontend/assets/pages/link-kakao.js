smartscanCommon.initLucideIcons();
smartscanCommon.initDarkModeToggle();

const loading = document.getElementById('state-loading');
const success = document.getElementById('state-success');
const errorEl = document.getElementById('state-error');
const errorMsg = document.getElementById('error-message');

function show(el) {
  [loading, success, errorEl].forEach(e => e.classList.add('hidden'));
  el.classList.remove('hidden');
  el.classList.add('flex');
}

function showError(msg) {
  if (msg) errorMsg.textContent = msg;
  show(errorEl);
}

(async function run() {
  const params = new URLSearchParams(location.search);
  const token = params.get('token');

  if (!token) {
    showError('연동 토큰이 없습니다. 카카오톡에서 전달받은 링크로 접속해주세요.');
    return;
  }

  if (!smartscanApi.isLoggedIn()) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    location.replace(`login.html?redirect=${redirect}`);
    return;
  }

  try {
    await smartscanApi.linkKakao(token);
    show(success);
  } catch (err) {
    let msg = '링크가 만료되었거나 유효하지 않습니다.';
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