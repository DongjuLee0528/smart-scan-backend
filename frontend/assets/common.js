/**
 * SmartScan Hub Common JavaScript Functions
 */
window.smartscanCommon = {

  // Dark mode toggle function
  initDarkModeToggle: function() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });
  },

  // Error display function
  showError: function(elementId, message) {
    const errorBox = document.getElementById(elementId);
    if (!errorBox) return;

    errorBox.textContent = message;
    errorBox.classList.remove('hidden');
  },

  // Error hide function
  clearError: function(elementId) {
    const errorBox = document.getElementById(elementId);
    if (!errorBox) return;

    errorBox.textContent = '';
    errorBox.classList.add('hidden');
  },

  // Success message display function
  showSuccess: function(elementId, message) {
    const successBox = document.getElementById(elementId);
    if (!successBox) return;

    successBox.textContent = message;
    successBox.classList.remove('hidden');
  },

  // Success message hide function
  clearSuccess: function(elementId) {
    const successBox = document.getElementById(elementId);
    if (!successBox) return;

    successBox.textContent = '';
    successBox.classList.add('hidden');
  },

  // Modal open function
  openModal: function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('hidden');
  },

  // Modal close function
  closeModal: function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('hidden');
  },

  // Set button loading state
  setButtonLoading: function(buttonId, isLoading, loadingText = 'Processing...') {
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

  // Initialize Lucide icons
  initLucideIcons: function() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
      lucide.createIcons();
    }
  },

  // Safe redirect target validation
  getRedirectTarget: function(defaultTarget = 'dashboard.html') {
    const params = new URLSearchParams(location.search);
    const redirect = params.get('redirect');
    // Allow only same-origin internal paths (prevent open redirect)
    if (redirect && redirect.startsWith('/')) return redirect;
    return defaultTarget;
  },

  // Modal state transition: show only activeId as flex, others hidden
  showModalState: function(activeId, allIds) {
    allIds.forEach(function(id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.add('hidden');
      el.classList.remove('flex');
    });
    const active = document.getElementById(activeId);
    if (active) {
      active.classList.remove('hidden');
      active.classList.add('flex');
    }
  }
};