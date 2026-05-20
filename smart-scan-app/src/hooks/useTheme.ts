import { useState, useEffect } from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, ColorScheme, ThemeColors } from '../theme/colors';

const THEME_STORAGE_KEY = 'user_theme_preference';

export const useTheme = () => {
  const systemColorScheme = useColorScheme();
  const [colorScheme, setColorScheme] = useState<ColorScheme>(systemColorScheme || 'light');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadTheme = async () => {
      try {
        const storedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
        if (storedTheme) {
          setColorScheme(storedTheme as ColorScheme);
        } else {
          setColorScheme(systemColorScheme || 'light');
        }
      } catch (error) {
        setColorScheme(systemColorScheme || 'light');
      } finally {
        setIsLoading(false);
      }
    };

    loadTheme();
  }, [systemColorScheme]);

  const toggleTheme = async () => {
    const newScheme = colorScheme === 'light' ? 'dark' : 'light';
    setColorScheme(newScheme);

    try {
      await AsyncStorage.setItem(THEME_STORAGE_KEY, newScheme);
    } catch (error) {
      console.error('Failed to save theme preference:', error);
    }
  };

  const resetToSystem = async () => {
    try {
      await AsyncStorage.removeItem(THEME_STORAGE_KEY);
      setColorScheme(systemColorScheme || 'light');
    } catch (error) {
      console.error('Failed to reset theme preference:', error);
    }
  };

  const themeColors: ThemeColors = colors[colorScheme];

  return {
    colorScheme,
    colors: themeColors,
    brandColor: colors.brand,
    toggleTheme,
    resetToSystem,
    isLoading,
  };
};