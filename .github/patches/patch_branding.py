#!/usr/bin/env python3
import os
import re
import sys
import glob

def sanitize_identifier(name):
    # alphanumeric only, lowercase
    clean = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return clean if clean else "app"

def replace_in_file(path, pattern, replacement, count=0):
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        new_content = re.sub(pattern, replacement, content, count=count)
        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[patch_branding] Updated regex in: {path}")
            return True
    except Exception as e:
        print(f"[patch_branding] Warning: Could not update {path}: {e}")
    return False

def replace_exact(path, old_str, new_str):
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if old_str in content:
            new_content = content.replace(old_str, new_str)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[patch_branding] Replaced '{old_str}' -> '{new_str}' in {path}")
            return True
    except Exception as e:
        print(f"[patch_branding] Warning: Could not replace in {path}: {e}")
    return False

def main():
    raw_ver = os.environ.get("VERSION", "").strip()
    clean_ver = re.sub(r'^[vV]', '', raw_ver).strip()
    if not clean_ver or clean_ver in ("master", "nightly"):
        clean_ver = "1.4.10-1"

    appname = os.environ.get("appname", "").strip()
    if not appname:
        appname = "AcilBir"

    compname = os.environ.get("compname", "").strip()
    if not compname:
        compname = "ABT Bilgisayar Programlama ve Tic.Ltd.Sti."

    url_link = os.environ.get("urlLink", "").strip()
    if not url_link:
        url_link = "https://acilbir.com"

    android_app_id = os.environ.get("androidappid", "").strip()
    clean_id = sanitize_identifier(appname)
    if not android_app_id or android_app_id == "com.carriez.flutter_hbb":
        android_app_id = f"com.{clean_id}.app"

    bundle_id = f"com.{clean_id}.app"

    print(f"[patch_branding] ======================================")
    print(f"[patch_branding] Applying Universal Branding Patch:")
    print(f"[patch_branding]   Version:         {clean_ver}")
    print(f"[patch_branding]   App Name:        {appname}")
    print(f"[patch_branding]   Company Name:    {compname}")
    print(f"[patch_branding]   Bundle / App ID: {bundle_id}")
    print(f"[patch_branding]   Android App ID:  {android_app_id}")
    print(f"[patch_branding]   URL Link:        {url_link}")
    print(f"[patch_branding] ======================================")

    # -------------------------------------------------------------
    # 1. CORE MANIFESTS & DYNAMIC VERSIONING
    # -------------------------------------------------------------
    replace_in_file("Cargo.toml", r'(?m)^version\s*=\s*"[^"]+"', f'version = "{clean_ver}"', count=1)
    replace_in_file("Cargo.toml", r'identifier\s*=\s*"[^"]+"', f'identifier = "{bundle_id}"')
    replace_in_file("Cargo.toml", r'name\s*=\s*"RustDesk"', f'name = "{appname}"')
    replace_in_file("Cargo.toml", r'ProductName\s*=\s*"RustDesk"', f'ProductName = "{appname}"')
    replace_in_file("Cargo.toml", r'FileDescription\s*=\s*"RustDesk Remote Desktop"', f'FileDescription = "{appname} Remote Desktop"')
    replace_in_file("Cargo.toml", r'OriginalFilename\s*=\s*"rustdesk.exe"', f'OriginalFilename = "{appname}.exe"')
    replace_in_file("Cargo.toml", r'description\s*=\s*"RustDesk Remote Desktop"', f'description = "{appname} Remote Desktop"')

    replace_in_file("libs/portable/Cargo.toml", r'ProductName\s*=\s*"RustDesk"', f'ProductName = "{appname}"')
    replace_in_file("libs/portable/Cargo.toml", r'FileDescription\s*=\s*"RustDesk Remote Desktop"', f'FileDescription = "{appname} Remote Desktop"')
    replace_in_file("libs/portable/Cargo.toml", r'OriginalFilename\s*=\s*"rustdesk.exe"', f'OriginalFilename = "{appname}.exe"')
    replace_in_file("libs/portable/Cargo.toml", r'description\s*=\s*"RustDesk Remote Desktop"', f'description = "{appname} Remote Desktop"')

    replace_in_file("Cargo.lock", r'(?m)(name\s*=\s*"rustdesk"\s*\nversion\s*=\s*)"[^"]+"', rf'\g<1>"{clean_ver}"', count=1)
    
    # Flutter pubspec.yaml version (supports suffixes like 1.4.10-1+1)
    if '+' in clean_ver:
        pubspec_ver = clean_ver
    else:
        pubspec_ver = f"{clean_ver}+1"
    replace_in_file("flutter/pubspec.yaml", r'(?m)^version:\s*.*', f'version: {pubspec_ver}')

    # -------------------------------------------------------------
    # 2. WINDOWS PLATFORM (RC, MSI, Windows Service, Registry)
    # -------------------------------------------------------------
    # Extract numeric version parts for binary RC structure (e.g. 1.4.10-1 -> 1,4,10,1)
    nums = re.findall(r'\d+', clean_ver)
    while len(nums) < 4:
        nums.append('0')
    win_ver_comma = ",".join(nums[:4])
    win_ver_dot = ".".join(nums[:4])

    rc_file = "flutter/windows/runner/Runner.rc"
    if os.path.exists(rc_file):
        replace_in_file(rc_file, r'PRODUCT_VERSION\s+[0-9,]+', f'PRODUCT_VERSION {win_ver_comma}')
        replace_in_file(rc_file, r'FILE_VERSION\s+[0-9,]+', f'FILE_VERSION {win_ver_comma}')
        replace_in_file(rc_file, r'VALUE\s+"ProductVersion",\s+"[^"]+"', f'VALUE "ProductVersion", "{clean_ver}\\0"')
        replace_in_file(rc_file, r'VALUE\s+"FileVersion",\s+"[^"]+"', f'VALUE "FileVersion", "{clean_ver}\\0"')
        replace_in_file(rc_file, r'VALUE\s+"ProductName",\s+"[^"]+"', f'VALUE "ProductName", "{appname}\\0"')
        replace_in_file(rc_file, r'VALUE\s+"FileDescription",\s+"[^"]+"', f'VALUE "FileDescription", "{appname} Remote Desktop\\0"')
        replace_in_file(rc_file, r'VALUE\s+"InternalName",\s+"[^"]+"', f'VALUE "InternalName", "{appname}\\0"')
        replace_in_file(rc_file, r'VALUE\s+"OriginalFilename",\s+"[^"]+"', f'VALUE "OriginalFilename", "{appname}.exe\\0"')
        replace_in_file(rc_file, r'VALUE\s+"CompanyName",\s+"[^"]+"', f'VALUE "CompanyName", "{compname}\\0"')
        replace_in_file(rc_file, r'VALUE\s+"LegalCopyright",\s+"[^"]+"', f'VALUE "LegalCopyright", "Copyright (C) 2026 {compname}. All rights reserved.\\0"')

    # Windows Service name & Mutex
    replace_exact("src/platform/windows.rs", 'const SERVICE_NAME: &str = "RustDesk";', f'const SERVICE_NAME: &str = "{appname}";')
    replace_exact("src/platform/windows.rs", 'const SERVICE_NAME: &str = "rustdesk";', f'const SERVICE_NAME: &str = "{clean_id}";')
    replace_exact("libs/portable/src/main.rs", 'const APP_PREFIX: &str = "rustdesk";', f'const APP_PREFIX: &str = "{appname}";')

    # MSI packaging
    replace_exact("res/msi/Package/License.rtf", "Purslane Tech Pte. Ltd.", compname)
    replace_exact("res/msi/Package/License.rtf", "Purslane Ltd", compname)
    replace_exact("res/msi/Package/License.rtf", "RustDesk", appname)
    replace_exact("res/msi/Package/License.rtf", "rustdesk.com", url_link)

    # -------------------------------------------------------------
    # 3. ANDROID PLATFORM (applicationId, Manifest, Strings, Kotlin)
    # -------------------------------------------------------------
    replace_in_file("flutter/android/app/build.gradle", r'applicationId\s+"[^"]+"', f'applicationId "{android_app_id}"')
    replace_in_file("flutter/android/app/build.gradle", r'versionName\s+"[^"]+"', f'versionName "{clean_ver}"')
    
    replace_exact("flutter/android/app/src/main/res/values/strings.xml", 'RustDesk', appname)
    replace_exact("flutter/android/app/src/main/AndroidManifest.xml", 'android:label="RustDesk"', f'android:label="{appname}"')
    replace_exact("flutter/android/app/src/main/AndroidManifest.xml", 'android:label="RustDesk Input"', f'android:label="{appname} Input"')
    
    # Android Kotlin service labels & notifications
    for kt in glob.glob("flutter/android/app/src/main/kotlin/**/*.kt", recursive=True):
        replace_exact(kt, "RustDesk is Open", f"{appname} is Open")
        replace_exact(kt, "Show Rustdesk", f"Show {appname}")
        replace_exact(kt, '"RustDesk Service"', f'"{appname} Service"')
        replace_exact(kt, '"RustDesk"', f'"{appname}"')

    # -------------------------------------------------------------
    # 4. MACOS & IOS PLATFORM (Xcode, xcconfig, Info.plist, XIB)
    # -------------------------------------------------------------
    pbx = "flutter/macos/Runner.xcodeproj/project.pbxproj"
    replace_in_file(pbx, r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*[^;]+;', f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id};')
    replace_in_file(pbx, r'PRODUCT_NAME\s*=\s*"?[^";]+"?;', f'PRODUCT_NAME = "{appname}";')
    replace_exact(pbx, '/* RustDesk.app */', f'/* {appname}.app */')
    replace_exact(pbx, 'path = RustDesk.app;', f'path = {appname}.app;')

    xcconfig = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
    replace_in_file(xcconfig, r'PRODUCT_NAME\s*=\s*.*', f'PRODUCT_NAME = {appname}')
    replace_in_file(xcconfig, r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*.*', f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}')
    replace_exact(xcconfig, 'Purslane Tech Pte. Ltd.', compname)
    replace_exact(xcconfig, 'Purslane Ltd.', compname)

    info_plist = "flutter/macos/Runner/Info.plist"
    replace_in_file(info_plist, r'(<key>CFBundleName</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{appname}\g<2>')
    replace_in_file(info_plist, r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{appname}\g<2>')
    replace_in_file(info_plist, r'(<key>CFBundleIdentifier</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{bundle_id}\g<2>')
    replace_exact(info_plist, 'com.carriez.rustdesk', bundle_id)
    replace_exact(info_plist, 'rustdesk', clean_id)

    xib = "flutter/macos/Runner/Base.lproj/MainMenu.xib"
    replace_exact(xib, 'title="APP_NAME"', f'title="{appname}"')
    replace_exact(xib, 'title="About APP_NAME"', f'title="About {appname}"')
    replace_exact(xib, 'title="Hide APP_NAME"', f'title="Hide {appname}"')
    replace_exact(xib, 'title="Quit APP_NAME"', f'title="Quit {appname}"')
    replace_exact(xib, 'customModule="RustDesk"', f'customModule="{appname}"')

    replace_in_file("flutter/macos/CMakeLists.txt", r'set\(BINARY_NAME\s+"[^"]+"\)', f'set(BINARY_NAME "{appname}")')
    replace_exact("src/platform/privileges_scripts/agent.plist", "com.carriez.rustdesk", bundle_id)
    replace_exact("src/platform/privileges_scripts/daemon.plist", "com.carriez.rustdesk", bundle_id)
    replace_exact("libs/hbb_common/src/config.rs", 'com.carriez', f'com.{clean_id}')

    # -------------------------------------------------------------
    # 5. LINUX PLATFORM (Desktop, Service, Specs, PKGBUILD)
    # -------------------------------------------------------------
    for dt in ["res/rustdesk.desktop", "res/rustdesk-link.desktop"]:
        replace_in_file(dt, r'Name\s*=.*', f'Name={appname}')
        replace_in_file(dt, r'Exec\s*=/usr/bin/rustdesk', f'Exec=/usr/bin/{clean_id}')
        replace_in_file(dt, r'Icon\s*=.*', f'Icon={clean_id}')

    replace_in_file("res/rustdesk.service", r'Description\s*=.*', f'Description={appname} Remote Desktop Service')
    replace_in_file("res/rustdesk.service", r'ExecStart\s*=/usr/bin/rustdesk\s+--service', f'ExecStart=/usr/bin/{clean_id} --service')

    replace_in_file("res/PKGBUILD", r'pkgver=.*', f'pkgver={clean_ver}')
    replace_in_file("res/rpm.spec", r'Version:\s*.*', f'Version:    {clean_ver}')
    replace_in_file("res/rpm-suse.spec", r'Version:\s*.*', f'Version:    {clean_ver}')

    # -------------------------------------------------------------
    # 6. UNIVERSAL APP STRINGS, COMPANY & LANGUAGE FILES
    # -------------------------------------------------------------
    replace_exact("src/main.rs", "Purslane Tech Pte. Ltd.", compname)
    replace_exact("src/main.rs", "Purslane Ltd.", compname)
    replace_exact("src/main.rs", "Purslane Ltd", compname)

    replace_exact("flutter/lib/main.dart", "title: 'RustDesk'", f"title: '{appname}'")
    replace_exact("flutter/lib/desktop/widgets/tabbar_widget.dart", '"RustDesk"', f'"{appname}"')
    replace_exact("flutter/lib/web/bridge.dart", "return 'RustDesk';", f"return '{appname}';")
    replace_exact("flutter/lib/desktop/pages/desktop_setting_page.dart", "Purslane Tech Pte. Ltd.", compname)
    replace_exact("flutter/lib/desktop/pages/desktop_setting_page.dart", "Purslane Ltd.", compname)

    # 50+ Languages in src/lang/*.rs
    for lang_file in glob.glob("src/lang/*.rs"):
        replace_exact(lang_file, "RustDesk", appname)

    # Replace Official URLs
    replace_exact("build.py", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/common.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/desktop/pages/desktop_setting_page.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/mobile/pages/settings_page.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/desktop/pages/install_page.dart", "https://rustdesk.com", url_link)

    print("[patch_branding] ======================================")
    print("[patch_branding] Universal Branding Patch Completed Successfully!")
    print("[patch_branding] ======================================")

if __name__ == "__main__":
    main()
