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

if (smartscanApi.isLoggedIn()) {
  location.replace(smartscanCommon.getRedirectTarget());
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  if (!email || !password) {
    showError('이메일과 비밀번호를 입력해주세요.');
    return;
  }

  smartscanCommon.setButtonLoading('login-submit', true, '로그인 중...');

  try {
    await smartscanApi.login(email, password);
    location.replace(smartscanCommon.getRedirectTarget());
  } catch (err) {
    const msg =
      (err && err.status === 401) ? '이메일 또는 비밀번호가 올바르지 않습니다.' :
      (err && err.message) ? err.message :
      '로그인 중 오류가 발생했습니다.';
    showError(msg);
    smartscanCommon.setButtonLoading('login-submit', false);
  }
});