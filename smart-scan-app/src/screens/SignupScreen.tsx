import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import { StackNavigationProp } from '@react-navigation/stack';

type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
};

type SignupScreenNavigationProp = StackNavigationProp<AuthStackParamList, 'Signup'>;

interface Props {
  navigation: SignupScreenNavigationProp;
}

export const SignupScreen: React.FC<Props> = ({ navigation }) => {
  const { colors, brandColor } = useTheme();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [age, setAge] = useState('');
  const [agreeToTerms, setAgreeToTerms] = useState(false);

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
    rowContainer: {
      flexDirection: 'row',
      justifyContent: 'space-between',
    },
    halfInput: {
      flex: 0.48,
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
    signupButton: {
      backgroundColor: brandColor,
      borderRadius: 8,
      paddingVertical: 16,
      alignItems: 'center',
      marginBottom: 24,
    },
    signupButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: 'bold',
    },
    loginContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      marginBottom: 24,
    },
    loginText: {
      color: colors.subtext,
      fontSize: 14,
    },
    loginLink: {
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
                    name="person-outline"
                    size={20}
                    color={colors.subtext}
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="이름"
                    placeholderTextColor={colors.subtext}
                    value={name}
                    onChangeText={setName}
                  />
                </View>
              </View>

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
                    placeholder="비밀번호 확인"
                    placeholderTextColor={colors.subtext}
                    value={confirmPassword}
                    onChangeText={setConfirmPassword}
                    secureTextEntry={true}
                  />
                </View>
              </View>

              <View style={[styles.inputContainer, styles.rowContainer]}>
                <View style={[styles.inputWrapper, styles.halfInput]}>
                  <Ionicons
                    name="call-outline"
                    size={20}
                    color={colors.subtext}
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="전화번호"
                    placeholderTextColor={colors.subtext}
                    value={phone}
                    onChangeText={setPhone}
                    keyboardType="phone-pad"
                  />
                </View>

                <View style={[styles.inputWrapper, styles.halfInput]}>
                  <Ionicons
                    name="calendar-outline"
                    size={20}
                    color={colors.subtext}
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="나이"
                    placeholderTextColor={colors.subtext}
                    value={age}
                    onChangeText={setAge}
                    keyboardType="number-pad"
                  />
                </View>
              </View>

              <TouchableOpacity
                style={styles.checkboxContainer}
                onPress={() => setAgreeToTerms(!agreeToTerms)}
              >
                <View style={[styles.checkbox, agreeToTerms && styles.checkboxChecked]}>
                  {agreeToTerms && (
                    <Ionicons name="checkmark" size={14} color="#FFFFFF" />
                  )}
                </View>
                <Text style={styles.checkboxText}>이용약관 및 개인정보처리방침에 동의합니다</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.signupButton}>
                <Text style={styles.signupButtonText}>회원가입</Text>
              </TouchableOpacity>

              <View style={styles.loginContainer}>
                <Text style={styles.loginText}>이미 계정이 있으신가요? </Text>
                <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                  <Text style={styles.loginLink}>로그인</Text>
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