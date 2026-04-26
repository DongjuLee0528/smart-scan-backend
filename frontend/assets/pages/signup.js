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
    showError('이름, 이메일, 비밀번호는 필수 입력 항목입니다.');
    return;
  }
  if (password.length < 8) {
    showError('비밀번호는 8자 이상이어야 합니다.');
    return;
  }
  if (password !== passwordConfirm) {
    showError('비밀번호가 일치하지 않습니다.');
    return;
  }
  if (!terms) {
    showError('이용약관 및 개인정보처리방침에 동의해주세요.');
    return;
  }

  const phone = phoneRaw || null;
  const age = ageRaw ? parseInt(ageRaw, 10) : null;

  smartscanCommon.setButtonLoading('signup-submit', true, '가입 중...');

  try {
    await smartscanApi.register({
      name,
      email,
      password,
      phone,
      age,
    });
    showSuccess('회원가입이 완료되었습니다. 로그인 페이지로 이동합니다...');
    setTimeout(() => location.replace('login.html'), 1200);
  } catch (err) {
    const msg = (err && err.message) ? err.message : '회원가입 중 오류가 발생했습니다.';
    showError(msg);
    smartscanCommon.setButtonLoading('signup-submit', false);
  }
});