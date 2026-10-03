@echo off
setlocal
echo ========================================================
echo   Building Jev AI Corporate Actions Mobile App
echo ========================================================

set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "ANDROID_HOME=C:\Users\%USERNAME%\AppData\Local\Android\Sdk"

echo [1/4] Building web distribution assets...
cd mobile
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Web build failed.
    cd ..
    exit /b %errorlevel%
)

echo [2/4] Syncing assets with Capacitor...
call npx cap sync android
if %errorlevel% neq 0 (
    echo [ERROR] Capacitor sync failed.
    cd ..
    exit /b %errorlevel%
)

echo [3/4] Building Android Debug APK...
cd android
call gradlew.bat assembleDebug
if %errorlevel% neq 0 (
    echo [ERROR] assembleDebug failed.
    cd ..\..
    exit /b %errorlevel%
)

echo [4/4] Building Signed Android Release App Bundle (.aab)...
call gradlew.bat bundleRelease
if %errorlevel% neq 0 (
    echo [ERROR] bundleRelease failed.
    cd ..\..
    exit /b %errorlevel%
)

cd ..\..

if not exist releases mkdir releases
copy /y "mobile\android\app\build\outputs\apk\debug\app-debug.apk" "releases\jev-ai-flow-v1.0.0-debug.apk"
copy /y "mobile\android\app\build\outputs\bundle\release\app-release.aab" "releases\jev-ai-flow-v1.0.0-release.aab"

echo.
echo ========================================================
echo   SUCCESS! Binaries generated in .\releases\
echo   - Debug APK: releases\jev-ai-flow-v1.0.0-debug.apk
echo   - Signed AAB: releases\jev-ai-flow-v1.0.0-release.aab
echo ========================================================
pause
