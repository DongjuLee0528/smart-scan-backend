import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import { StackNavigationProp } from '@react-navigation/stack';
import { login } from '../api/auth';
import { validateEmail } from '../utils/validation';

type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
};

type LoginScreenNavigationProp = StackNavigationProp<AuthStackParamList, 'Login'>;

interface Props {
  navigation: LoginScreenNavigationProp;
}

export const LoginScreen: React.FC<Props> = ({ navigation }) => {
  const { colors, brandColor } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = useCallback(async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('오류', '이메일과 비밀번호를 모두 입력해주세요.');
      return;
    }

    if (!validateEmail(email.trim())) {
      Alert.alert('오류', '유효한 이메일 형식을 입력해주세요.');
      return;
    }

    if (password.length < 8) {
      Alert.alert('오류', '비밀번호는 8자 이상이어야 합니다.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await login(email.trim(), password);
      console.log('로그인 성공:', response.user.name);
    } catch (error: any) {
      let message = '로그인에 실패했습니다.';

      if (error.code === 'NETWORK_ERROR' || !error.response) {
        message = '네트워크 연결을 확인해주세요.';
      } else if (error.response?.status === 401) {
        message = '이메일 또는 비밀번호가 올바르지 않습니다.';
      } else if (error.response?.status >= 500) {
        message = '서버에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else if (error.response?.data?.detail) {
        message = error.response.data.detail;
      }

      Alert.alert('로그인 실패', message);
    } finally {
      setIsLoading(false);
    }
  }, [email, password]);

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    scrollView: {
      flexGrow: 1,
    },
    content: {
      flex: 1,
      paddingHorizontal: 24,
      paddingVertical: 40,
    },
    logoContainer: {
      backgroundColor: brandColor,
      borderRadius: 16,
      padding: 24,
      alignItems: 'center',
      marginBottom: 32,
    },
    logoText: {
      color: '#FFFFFF',
      fontSize: 24,
      fontWeight: 'bold',
      marginTop: 8,
    },
    logoSubtitle: {
      color: '#FFFFFF',
      fontSize: 14,
      opacity: 0.9,
      marginTop: 4,
    },
    card: {
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: 24,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    inputContainer: {
      marginBottom: 16,
    },
    inputWrapper: {
      flexDirection: 'row',
      alignItems: 'center',
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 8,
      paddingHorizontal: 12,
      paddingVertical: 12,
    },
    inputIcon: {
      marginRight: 12,
    },
    input: {
      flex: 1,
      fontSize: 16,
      color: colors.text,
    },
    passwordContainer: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 16,
    },
    forgotPassword: {
      color: brandColor,
      fontSize: 14,
    },
    checkboxContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 24,
    },
    checkbox: {
      width: 20,
      height: 20,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 4,
      marginRight: 8,
      alignItems: 'center',
      justifyContent: 'center',
    },
    checkboxChecked: {
      backgroundColor: brandColor,
      borderColor: brandColor,
    },
    checkboxText: {
      color: colors.text,
      fontSize: 14,
    },
    loginButton: {
      backgroundColor: brandColor,
      borderRadius: 8,
      paddingVertical: 16,
      alignItems: 'center',
      marginBottom: 24,
      opacity: isLoading ? 0.7 : 1,
    },
    loginButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: 'bold',
    },
    signupContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      marginBottom: 24,
    },
    signupText: {
      color: colors.subtext,
      fontSize: 14,
    },
    signupLink: {
      color: brandColor,
      fontSize: 14,
      fontWeight: 'bold',
    },
    footer: {
      flexDirection: 'row',
      justifyContent: 'center',
      flexWrap: 'wrap',
    },
    footerText: {
      color: colors.subtext,
      fontSize: 12,
      marginHorizontal: 8,
    },
    footerLink: {
      color: brandColor,
      fontSize: 12,
    },
  });

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <ScrollView contentContainerStyle={styles.scrollView}>
          <View style={styles.content}>
            <View style={styles.logoContainer}>
              <Ionicons name="scan" size={32} color="#FFFFFF" />
              <Text style={styles.logoText}>SmartScan</Text>
              <Text style={styles.logoSubtitle}>스마트 스캔 솔루션</Text>
            </View>

            <View style={styles.card}>
              <View style={styles.inputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons
                    name="mail-outline"
                    size={20}
                    color={colors.subtext}
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="이메일 주소"
                    placeholderTextColor={colors.subtext}
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons
                    name="lock-closed-outline"
                    size={20}
                    color={colors.subtext}
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="비밀번호"
                    placeholderTextColor={colors.subtext}
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry={true}
                  />
                </View>
                <View style={styles.passwordContainer}>
                  <View />
                  <TouchableOpacity>
                    <Text style={styles.forgotPassword}>비밀번호 찾기</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <TouchableOpacity
                style={styles.checkboxContainer}
                onPress={() => setRememberMe(!rememberMe)}
              >
                <View style={[styles.checkbox, rememberMe && styles.checkboxChecked]}>
                  {rememberMe && (
                    <Ionicons name="checkmark" size={14} color="#FFFFFF" />
                  )}
                </View>
                <Text style={styles.checkboxText}>로그인 상태 유지</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.loginButton}
                onPress={handleLogin}
                disabled={isLoading}
              >
                {isLoading ? (
                  <ActivityIndicator color="#FFFFFF" size="small" />
                ) : (
                  <Text style={styles.loginButtonText}>로그인</Text>
                )}
              </TouchableOpacity>

              <View style={styles.signupContainer}>
                <Text style={styles.signupText}>계정이 없으신가요? </Text>
                <TouchableOpacity onPress={() => navigation.navigate('Signup')}>
                  <Text style={styles.signupLink}>회원가입</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.footer}>
              <TouchableOpacity>
                <Text style={styles.footerLink}>이용약관</Text>
              </TouchableOpacity>
              <Text style={styles.footerText}>•</Text>
              <TouchableOpacity>
                <Text style={styles.footerLink}>개인정보처리방침</Text>
              </TouchableOpacity>
              <Text style={styles.footerText}>•</Text>
              <TouchableOpacity>
                <Text style={styles.footerLink}>고객지원</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};