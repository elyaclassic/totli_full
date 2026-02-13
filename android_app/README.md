# TOTLI HOLVA Agent - Android APK Yasash Qo'llanmasi

## 📋 TALABLAR:
- Android Studio (https://developer.android.com/studio)
- JDK 11 yoki yuqori
- Android SDK

---

## 🚀 QADAMLAR:

### 1. ANDROID STUDIO OCHISH

1. Android Studio'ni oching
2. "New Project" → "Empty Views Activity" tanlang
3. Quyidagi ma'lumotlarni kiriting:
   - **Name:** TOTLI HOLVA Agent
   - **Package name:** uz.totliholva.agent
   - **Save location:** F:\TOTLI_HOLVA\business_system\android_app
   - **Language:** Kotlin (yoki Java)
   - **Minimum SDK:** API 24 (Android 7.0)
4. "Finish" bosing

---

### 2. MANIFEST.XML SOZLASH

**app/src/main/AndroidManifest.xml** faylini oching va quyidagilarni qo'shing:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="uz.totliholva.agent">

    <!-- Permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="TOTLI HOLVA Agent"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar"
        android:usesCleartextTraffic="true">
        
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

---

### 3. MAINACTIVITY.KT YARATISH

**app/src/main/java/uz/totliholva/agent/MainActivity.kt** faylini yarating:

```kotlin
package uz.totliholva.agent

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.GeolocationPermissions
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    
    private lateinit var webView: WebView
    private val LOCATION_PERMISSION_CODE = 100
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        webView = WebView(this)
        setContentView(webView)
        
        setupWebView()
        checkLocationPermission()
        
        // Load URL (ZeroTier IP yoki server manzili)
        webView.loadUrl("http://10.243.49.144/static/pwa/login.html")
    }
    
    private fun setupWebView() {
        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.setGeolocationEnabled(true)
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = object : WebChromeClient() {
            override fun onGeolocationPermissionsShowPrompt(
                origin: String,
                callback: GeolocationPermissions.Callback
            ) {
                callback.invoke(origin, true, false)
            }
        }
    }
    
    private fun checkLocationPermission() {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                ),
                LOCATION_PERMISSION_CODE
            )
        }
    }
    
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
```

---

### 4. BUILD.GRADLE SOZLASH

**app/build.gradle** faylini oching va quyidagilarni qo'shing:

```gradle
android {
    compileSdk 34
    
    defaultConfig {
        applicationId "uz.totliholva.agent"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }
    
    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.core:core-ktx:1.12.0'
}
```

---

### 5. APK BUILD QILISH

1. **Build** → **Build Bundle(s) / APK(s)** → **Build APK(s)**
2. **Build** tugaguncha kuting (5-10 daqiqa)
3. **APK fayli** quyida joylashadi:
   ```
   F:\TOTLI_HOLVA\business_system\android_app\app\build\outputs\apk\debug\app-debug.apk
   ```

---

### 6. TELEFONGA O'RNATISH

1. **APK faylini** telefonga ko'chiring
2. **Fayl menejer** orqali oching
3. **O'rnatish** ruxsatini bering
4. **O'rnating**!

---

## 🎉 TAYYOR!

Endi sizda **to'liq Android app** bor:
- ✅ Haqiqiy GPS tracking
- ✅ Offline ishlash
- ✅ Background tracking
- ✅ Native app sifatida

---

## 📝 ESLATMA:

**PRODUCTION** uchun:
1. **Server URL**ni o'zgartiring (ZeroTier IP: 10.243.49.144 yoki haqiqiy domain)
2. **Release APK** yasang (signed)
3. **Google Play**ga yuklang (opsional)

---

## 🆘 YORDAM:

Agar muammo bo'lsa:
1. **Android Studio** loglarini tekshiring
2. **Gradle sync** qiling
3. **Clean Project** → **Rebuild Project**
