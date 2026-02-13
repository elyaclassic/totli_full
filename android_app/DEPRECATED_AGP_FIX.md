# Deprecated AGP ogohlantirishlarini olib tashlash

Bu 7 ta ogohlantirish **build ni buzmaydi**, lekin ularni yo'qotish uchun quyidagilarni bajaring.

## Usul 1: PowerShell skripti (global sozlamalar bo'lsa)

Loyiha papkasida (android_app) terminal oching va:

```powershell
.\fix-deprecated-agp-warnings.ps1
```

Keyin **Android Studio** ni yopib qayta oching va **File → Sync Project with Gradle Files**.

---

## Usul 2: Android Studio cache tozalash

Ogohlantirishlar IDE cache dan kelayotgan bo'lishi mumkin:

1. **File** → **Invalidate Caches / Restart**
2. **Invalidate and Restart** ni bosing
3. Studio qayta ochilgach: **File** → **Sync Project with Gradle Files**

---

## Usul 3: Global gradle.properties ni qo'lda tuzatish

Agar sizda `C:\Users\ELYOR\.gradle\gradle.properties` fayli bo'lsa, uni oching va quyidagi qatorlarni **o'chiring** (yoki `#` bilan comment qiling):

```
android.usesSdkInManifest.disallowed=false
android.sdk.defaultTargetSdkToCompileSdkIfUnset=false
android.enableAppCompileTimeRClass=false
android.builtInKotlin=false
android.newDsl=false
android.r8.optimizedResourceShrinking=false
android.defaults.buildfeatures.resvalues=true
```

Faylni saqlang va Android Studio ni qayta ishga tushiring.

---

## Eslatma

- Bu faqat **ogohlantirishlar**; APK build bo'ladi.
- AGP 10.0 da bu sozlamalar butunlay olib tashlanadi.
- Agar skript "File not found" deb yozsa, **Usul 2** (Invalidate Caches) ni qo'llang.
