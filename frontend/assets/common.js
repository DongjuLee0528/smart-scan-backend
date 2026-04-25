/**
 * SmartScan Hub 공통 JavaScript 함수들
 */
window.smartscanCommon = {

  // 다크모드 토글 함수
  initDarkModeToggle: function() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });
  },

  // 에러 표시 함수
  showError: function(elementId, message) {
    const errorBox = document.getElementById(elementId);
    if (!errorBox) return;

    errorBox.textContent = message;
    errorBox.classList.remove('hidden');
  },

  // 에러 숨김 함수
  clearError: function(elementId) {
    const errorBox = document.getElementById(elementId);
    if (!errorBox) return;

    errorBox.textContent = '';
    errorBox.classList.add('hidden');
  },

  // 성공 메시지 표시 함수
  showSuccess: function(elementId, message) {
    const successBox = document.getElementById(elementId);
    if (!successBox) return;

    successBox.textContent = message;
    successBox.classList.remove('hidden');
  },

  // 성공 메시지 숨김 함수
  clearSuccess: function(elementId) {
    const successBox = document.getElementById(elementId);
    if (!successBox) return;

    successBox.textContent = '';
    successBox.classList.add('hidden');
  },

  // 모달 열기 함수
  openModal: function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('hidden');
  },

  // 모달 닫기 함수
  closeModal: function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('hidden');
  },

  // 버튼 로딩 상태 설정
  setButtonLoading: function(buttonId, isLoading, loadingText = '처리 중...') {
    const button = document.getElementById(buttonId);
    if (!button) return;

    if (isLoading) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = loadingText;
    } else {
      button.disabled = false;
      if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
        delete button.dataset.originalText;
      }
    }
  },

  // Lucide 아이콘 초기화
  initLucideIcons: function() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
      lucide.createIcons();
    }
  },

  // 리디렉션 타겟 안전 확인
  getRedirectTarget: function(defaultTarget = 'dashboard.html') {
    const params = new URLSearchParams(location.search);
    const redirect = params.get('redirect');
    // 같은 origin 내부 경로만 허용 (open redirect 방지)
    if (redirect && redirect.startsWith('/')) return redirect;
    return defaultTarget;
  }
};