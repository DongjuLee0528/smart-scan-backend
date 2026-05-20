export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('8자 이상 입력해주세요');
  }

  if (!/[a-zA-Z]/.test(password)) {
    errors.push('영문자를 1개 이상 포함해주세요');
  }

  if (!/[0-9]/.test(password)) {
    errors.push('숫자를 1개 이상 포함해주세요');
  }

  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    errors.push('특수문자를 1개 이상 포함해주세요 (!@#$%^&* 등)');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

export const validatePhone = (phone: string): boolean => {
  const phoneRegex = /^01[0-9][0-9]{8}$/;
  return phoneRegex.test(phone.replace(/-/g, ''));
};

export const formatPhoneNumber = (phone: string): string => {
  const numbers = phone.replace(/[^\d]/g, '');

  if (numbers.length <= 3) {
    return numbers;
  } else if (numbers.length <= 7) {
    return `${numbers.slice(0, 3)}-${numbers.slice(3)}`;
  } else {
    return `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7, 11)}`;
  }
};