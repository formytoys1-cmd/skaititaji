import React, { useRef, useState, useCallback } from 'react';
import {
  SafeAreaView, StyleSheet, ActivityIndicator, View, Text,
  TouchableOpacity, RefreshControl, ScrollView, BackHandler, Platform,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { StatusBar } from 'expo-status-bar';
import Constants from 'expo-constants';

// URL боевого сайта (PWA). Меняется в app.json → expo.extra.siteUrl.
const SITE_URL =
  (Constants.expoConfig &&
    Constants.expoConfig.extra &&
    Constants.expoConfig.extra.siteUrl) ||
  'https://skaititaji.onrender.com';

const BRAND = '#0369a1';

/**
 * Экран-обёртка PWA в WebView.
 *
 * Это самый быстрый путь опубликовать приложение в App Store / Google Play:
 * нативная оболочка загружает уже готовый адаптивный сайт (PWA). Даёт нативную
 * иконку, splash, аппаратную кнопку «назад» (Android), pull-to-refresh и
 * обработку офлайна. Дальше отдельные экраны можно переносить на нативный UI,
 * дергая тот же backend (JSON API уже есть: /agent/api, /api/*).
 */
export default function App() {
  const webRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [canGoBack, setCanGoBack] = useState(false);

  // Аппаратная кнопка «назад» на Android управляет историей WebView.
  React.useEffect(() => {
    if (Platform.OS !== 'android') return;
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (canGoBack && webRef.current) {
        webRef.current.goBack();
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [canGoBack]);

  const reload = useCallback(() => {
    setFailed(false);
    setLoading(true);
    webRef.current && webRef.current.reload();
  }, []);

  if (failed) {
    return (
      <SafeAreaView style={styles.center}>
        <StatusBar style="light" backgroundColor={BRAND} />
        <Text style={styles.errIcon}>📴</Text>
        <Text style={styles.errTitle}>Nav savienojuma</Text>
        <Text style={styles.errBody}>
          Pārbaudiet interneta savienojumu un mēģiniet vēlreiz.
        </Text>
        <TouchableOpacity style={styles.btn} onPress={reload}>
          <Text style={styles.btnText}>Mēģināt vēlreiz</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.flex}>
      <StatusBar style="light" backgroundColor={BRAND} />
      <WebView
        ref={webRef}
        source={{ uri: SITE_URL }}
        onLoadStart={() => setLoading(true)}
        onLoadEnd={() => setLoading(false)}
        onError={() => { setFailed(true); setLoading(false); }}
        onHttpError={() => setLoading(false)}
        onNavigationStateChange={(s) => setCanGoBack(s.canGoBack)}
        startInLoadingState
        allowsBackForwardNavigationGestures
        pullToRefreshEnabled
        decelerationRate="normal"
        // Разрешаем только наш origin в WebView; внешние ссылки — в системный браузер.
        originWhitelist={['https://skaititaji.onrender.com/*', 'https://*.onrender.com/*']}
      />
      {loading && (
        <View style={styles.loader} pointerEvents="none">
          <ActivityIndicator size="large" color={BRAND} />
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#fff' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: '#f8fafc' },
  loader: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.6)',
  },
  errIcon: { fontSize: 48, marginBottom: 12 },
  errTitle: { fontSize: 22, fontWeight: '700', color: '#0f172a' },
  errBody: { fontSize: 14, color: '#475569', textAlign: 'center', marginTop: 8 },
  btn: { marginTop: 20, backgroundColor: BRAND, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 12 },
  btnText: { color: '#fff', fontWeight: '600' },
});
