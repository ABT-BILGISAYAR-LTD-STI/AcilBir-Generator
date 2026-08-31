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
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    new_content = re.sub(pattern, replacement, content, count=count)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[patch_branding] Updated: {path}")
        return True
    return False

def replace_exact(path, old_str, new_str):
    if not os.path.exists(path):
        return False
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    if old_str in content:
        new_content = content.replace(old_str, new_str)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[patch_branding] Replaced '{old_str}' -> '{new_str}' in {path}")
        return True
    return False

def main():
    raw_ver = os.environ.get("VERSION", "").strip()
    clean_ver = re.sub(r'^[vV]', '', raw_ver).strip()
    if not clean_ver or clean_ver in ("master", "nightly"):
        clean_ver = "1.4.10"

    appname = os.environ.get("appname", "").strip()
    if not appname:
        appname = "AcilBir"

    compname = os.environ.get("compname", "").strip()
    if not compname:
        compname = "ABT Bilgisayar"

    url_link = os.environ.get("urlLink", "").strip()
    if not url_link:
        url_link = "https://acilbir.com"

    clean_id = sanitize_identifier(appname)
    bundle_id = f"com.{clean_id}.app"

    print(f"[patch_branding] Starting branding patch:")
    print(f"  Version: {clean_ver}")
    print(f"  App Name: {appname}")
    print(f"  Company Name: {compname}")
    print(f"  Bundle ID: {bundle_id}")
    print(f"  URL: {url_link}")

    # 1. Update Version in Cargo.toml (top-level package version)
    replace_in_file("Cargo.toml", r'(?m)^version\s*=\s*"[^"]+"', f'version = "{clean_ver}"', count=1)
    replace_in_file("Cargo.toml", r'identifier\s*=\s*"[^"]+"', f'identifier = "{bundle_id}"')

    # 2. Update Version in Cargo.lock for rustdesk package
    replace_in_file("Cargo.lock", r'(?m)(name\s*=\s*"rustdesk"\s*\nversion\s*=\s*)"[^"]+"', rf'\g<1>"{clean_ver}"', count=1)

    # 3. Update Version and Name in flutter/pubspec.yaml
    replace_in_file("flutter/pubspec.yaml", r'(?m)^version:\s*.*', f'version: {clean_ver}+1')

    # 4. macOS Xcode project.pbxproj - Product Name & Bundle Identifier
    pbx = "flutter/macos/Runner.xcodeproj/project.pbxproj"
    replace_in_file(pbx, r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*[^;]+;', f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id};')
    replace_in_file(pbx, r'PRODUCT_NAME\s*=\s*"?[^";]+"?;', f'PRODUCT_NAME = "{appname}";')
    replace_exact(pbx, '/* RustDesk.app */', f'/* {appname}.app */')
    replace_exact(pbx, 'path = RustDesk.app;', f'path = {appname}.app;')

    # 5. macOS AppInfo.xcconfig
    xcconfig = "flutter/macos/Runner/Configs/AppInfo.xcconfig"
    replace_in_file(xcconfig, r'PRODUCT_NAME\s*=\s*.*', f'PRODUCT_NAME = {appname}')
    replace_in_file(xcconfig, r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*.*', f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}')
    replace_exact(xcconfig, 'Purslane Tech Pte. Ltd.', compname)
    replace_exact(xcconfig, 'Purslane Ltd.', compname)

    # 6. macOS Info.plist
    info_plist = "flutter/macos/Runner/Info.plist"
    replace_in_file(info_plist, r'(<key>CFBundleName</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{appname}\g<2>')
    replace_in_file(info_plist, r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{appname}\g<2>')
    replace_in_file(info_plist, r'(<key>CFBundleIdentifier</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{bundle_id}\g<2>')
    replace_exact(info_plist, 'com.carriez.rustdesk', bundle_id)
    replace_exact(info_plist, 'rustdesk', clean_id)

    # 7. macOS MainMenu.xib (Top Menu bar items: About, Hide, Quit, Window title)
    xib = "flutter/macos/Runner/Base.lproj/MainMenu.xib"
    replace_exact(xib, 'title="APP_NAME"', f'title="{appname}"')
    replace_exact(xib, 'title="About APP_NAME"', f'title="About {appname}"')
    replace_exact(xib, 'title="Hide APP_NAME"', f'title="Hide {appname}"')
    replace_exact(xib, 'title="Quit APP_NAME"', f'title="Quit {appname}"')
    replace_exact(xib, 'customModule="RustDesk"', f'customModule="{appname}"')

    # 8. macOS CMakeLists.txt
    cmake = "flutter/macos/CMakeLists.txt"
    replace_in_file(cmake, r'set\(BINARY_NAME\s+"[^"]+"\)', f'set(BINARY_NAME "{appname}")')

    # 9. macOS privilege scripts
    replace_exact("src/platform/privileges_scripts/agent.plist", "com.carriez.rustdesk", bundle_id)
    replace_exact("src/platform/privileges_scripts/daemon.plist", "com.carriez.rustdesk", bundle_id)

    # 10. libs/hbb_common/src/config.rs (Default macOS org domain)
    replace_exact("libs/hbb_common/src/config.rs", 'com.carriez', f'com.{clean_id}')

    # 11. Replace Company Name across Rust files & Dart files
    for f in ["Cargo.toml", "libs/portable/Cargo.toml", "src/main.rs", "flutter/lib/desktop/pages/desktop_setting_page.dart"]:
        replace_exact(f, "Purslane Tech Pte. Ltd.", compname)
        replace_exact(f, "Purslane Ltd.", compname)

    # 12. Replace Language files RustDesk mentions
    for lang_file in glob.glob("src/lang/*.rs"):
        replace_exact(lang_file, "RustDesk", appname)

    # 13. Replace URLs
    replace_exact("build.py", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/common.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/desktop/pages/desktop_setting_page.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/mobile/pages/settings_page.dart", "https://rustdesk.com", url_link)
    replace_exact("flutter/lib/desktop/pages/install_page.dart", "https://rustdesk.com", url_link)

    print("[patch_branding] Branding patch applied successfully!")

if __name__ == "__main__":
    main()
