export const colors = {
  brand: '#034EA2',

  light: {
    background: '#F9FAFB',
    card: '#FFFFFF',
    text: '#111827',
    subtext: '#6B7280',
    border: '#D1D5DB',
  },

  dark: {
    background: '#111827',
    card: '#1F2937',
    text: '#FFFFFF',
    subtext: '#9CA3AF',
    border: '#374151',
  },
};

export type ColorScheme = 'light' | 'dark';
export type ThemeColors = typeof colors.light;