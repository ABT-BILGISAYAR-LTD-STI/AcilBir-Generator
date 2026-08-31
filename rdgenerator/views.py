import io
from pathlib import Path
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
import os
import secrets
import re
import requests
import base64
import json
import uuid
import pyzipper
import time
from django.conf import settings as _settings
from django.db.models import Q
from .forms import GenerateForm
from .models import GithubRun
from PIL import Image
from urllib.parse import quote


def generate_custom_client(params, full_url):
    """
    Core generation logic shared by web form and JSON API.

    Args:
        params: dict containing all configuration fields (keys match GenerateForm field names)
        full_url: the full URL of this service (protocol + host)

    Returns:
        dict with 'success' key. On success: includes 'uuid', 'filename', 'platform', 'log_url'.
        On failure: includes 'error' and optionally 'status_code'.
    """
    user_secret = params.get('sh_secret_field', '')
    selfhosted = (_settings.SH_SECRET == user_secret)
    platform = params.get('platform', 'windows')
    version = params.get('version', '1.4.10-1')
    variant = params.get('variant', 'client')
    delayFix = params.get('delayFix', True)
    xOffline = params.get('xOffline', False)
    hidecm = params.get('hidecm', False)
    removeNewVersionNotif = params.get('removeNewVersionNotif', False)
    server = params.get('serverIP', '')
    key = params.get('key', '')
    apiServer = params.get('apiServer', '')
    urlLink = params.get('urlLink', '')
    downloadLink = params.get('downloadLink', '')
    if not server:
        server = 'rs-ny.rustdesk.com' #default rustdesk server
    if not key:
        key = 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=' #default rustdesk key
    if not apiServer:
        apiServer = server+":21114"
    if not urlLink:
        urlLink = "https://acilbir.com"
    if not downloadLink:
        platform_name_map = {
            'windows': 'Windows',
            'windows-x86': 'Windows-x86',
            'linux': 'Linux',
            'android': 'Android',
            'macos': 'macOS'
        }
        p_name = platform_name_map.get(platform, 'Windows')
        if variant == 'admin':
            downloadLink = f"https://acilbir.com/api/client-downloads/download/admin-{p_name}"
        elif variant == 'beta':
            downloadLink = f"https://acilbir.com/api/client-downloads/download/beta-{p_name}"
        else:
            downloadLink = f"https://acilbir.com/api/client-downloads/download/{p_name}"
    direction = params.get('direction', 'both')
    installation = params.get('installation', 'installationY')
    settings = params.get('settings', 'settingsY')
    appname = params.get('appname', '')
    if not appname:
        appname = "AcilBir"
    filename = params.get('exename', 'AcilBir')
    compname = params.get('compname', '')
    if not compname:
        compname = "ABT Bilgisayar Programlama ve Tic.Ltd.Sti."
    androidappid = params.get('androidappid', '')
    if not androidappid:
        androidappid = "com.acilbir.app"
    compname = compname.replace("&","\\&")
    permPass = params.get('permanentPassword', '')
    theme = params.get('theme', 'system')
    themeDorO = params.get('themeDorO', 'default')
    passApproveMode = params.get('passApproveMode', 'password-click')
    denyLan = params.get('denyLan', False)
    enableDirectIP = params.get('enableDirectIP', False)
    autoClose = params.get('autoClose', False)
    permissionsDorO = params.get('permissionsDorO', 'default')
    permissionsType = params.get('permissionsType', 'custom')
    enableKeyboard = params.get('enableKeyboard', True)
    enableClipboard = params.get('enableClipboard', True)
    enableFileTransfer = params.get('enableFileTransfer', True)
    enableAudio = params.get('enableAudio', True)
    enableTCP = params.get('enableTCP', True)
    enableRemoteRestart = params.get('enableRemoteRestart', True)
    enableRecording = params.get('enableRecording', True)
    enableBlockingInput = params.get('enableBlockingInput', True)
    enableRemoteModi = params.get('enableRemoteModi', False)
    removeWallpaper = params.get('removeWallpaper', True)
    defaultManual = params.get('defaultManual', '')
    overrideManual = params.get('overrideManual', '')
    enablePrinter = params.get('enablePrinter', True)
    enableCamera = params.get('enableCamera', True)
    enableTerminal = params.get('enableTerminal', True)

    if all(char.isascii() for char in filename):
        filename = re.sub(r'[^\w\s-]', '_', filename).strip()
        filename = filename.replace(" ","_")
    else:
        filename = "AcilBir"
    if not all(char.isascii() for char in appname):
        appname = "AcilBir"
    myuuid = str(uuid.uuid4())

    try:
        iconfile = params.get('iconfile')
        if not iconfile:
            iconfile = params.get('iconbase64')
        iconlink_url, iconlink_uuid, iconlink_file = save_png(iconfile,myuuid,full_url,"icon.png")
    except Exception as e:
        print(f"failed to get icon, using default: {e}")
        iconlink_url = "false"
        iconlink_uuid = "false"
        iconlink_file = "false"
    try:
        logofile = params.get('logofile')
        if not logofile:
            logofile = params.get('logobase64')
        logolink_url, logolink_uuid, logolink_file = save_png(logofile,myuuid,full_url,"logo.png")
    except Exception as e:
        print(f"failed to get logo: {e}")
        logolink_url = "false"
        logolink_uuid = "false"
        logolink_file = "false"
    try:
        privacyfile = params.get('privacyfile')
        if not privacyfile:
            privacyfile = params.get('privacybase64')
        privacylink_url, privacylink_uuid, privacylink_file = save_png(privacyfile,myuuid,full_url,"privacy.png")
    except Exception as e:
        print(f"failed to get privacy image: {e}")
        privacylink_url = "false"
        privacylink_uuid = "false"
        privacylink_file = "false"

    ###create the custom.txt json here and send in as inputs below
    decodedCustom = {}
    if direction != "Both":
        decodedCustom['conn-type'] = direction
    if installation == "installationN":
        decodedCustom['disable-installation'] = 'Y'
    if settings == "settingsN":
        decodedCustom['disable-settings'] = 'Y'
    if appname.upper() != "rustdesk".upper() and appname != "":
        decodedCustom['app-name'] = appname
    decodedCustom['override-settings'] = {}
    decodedCustom['default-settings'] = {}
    # Enable auto-update by default — required for updater.rs check_update() to run
    decodedCustom['default-settings']['allow-auto-update'] = 'Y'
    if permPass != "":
        decodedCustom['password'] = permPass
    if theme != "system":
        if themeDorO == "default":
            if platform == "windows-x86":
                decodedCustom['default-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['default-settings']['theme'] = theme
        elif themeDorO == "override":
            if platform == "windows-x86":
                decodedCustom['override-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['override-settings']['theme'] = theme
    decodedCustom['enable-lan-discovery'] = 'N' if denyLan else 'Y'
    decodedCustom['allow-auto-disconnect'] = 'Y' if autoClose else 'N'
    if permissionsDorO == "default":
        decodedCustom['default-settings']['access-mode'] = permissionsType
        decodedCustom['default-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['default-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['default-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['default-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['default-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['default-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['default-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['default-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['default-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['default-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['default-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['default-settings']['approve-mode'] = passApproveMode
        decodedCustom['default-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['default-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['default-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['default-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['default-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        decodedCustom['default-settings']['allow-always-relay'] = 'Y'
        decodedCustom['default-settings']['force-always-relay'] = 'N'
        decodedCustom['default-settings']['stop-service'] = 'N'
    else:
        decodedCustom['override-settings']['access-mode'] = permissionsType
        decodedCustom['override-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['override-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['override-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['override-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['override-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['override-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['override-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['override-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['override-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['override-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['override-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['override-settings']['approve-mode'] = passApproveMode
        decodedCustom['override-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['override-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['override-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['override-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['override-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        decodedCustom['override-settings']['allow-always-relay'] = 'Y'
        decodedCustom['override-settings']['force-always-relay'] = 'N'
        decodedCustom['override-settings']['stop-service'] = 'N'

    if defaultManual:
        for line in defaultManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['default-settings'][k.strip()] = value.strip()

    if overrideManual:
        for line in overrideManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['override-settings'][k.strip()] = value.strip()
    
    decodedCustomJson = json.dumps(decodedCustom)

    string_bytes = decodedCustomJson.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    encodedCustom = base64_bytes.decode("ascii")

    ####from here run the github action, we need user, repo, access token.
    if platform == 'windows':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'
    elif platform == 'windows-x86':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows-x86.yml/dispatches'
    elif platform == 'linux':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-linux.yml/dispatches'
    elif platform == 'android':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-android.yml/dispatches'
    elif platform == 'macos':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-macos.yml/dispatches'
    else:
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'

    inputs_raw = {
        "server": server,
        "key": key,
        "apiServer": apiServer,
        "custom": encodedCustom,
        "uuid": myuuid,
        "iconlink_url": iconlink_url,
        "iconlink_uuid": iconlink_uuid,
        "iconlink_file": iconlink_file,
        "logolink_url": logolink_url,
        "logolink_uuid": logolink_uuid,
        "logolink_file": logolink_file,
        "privacylink_url": privacylink_url,
        "privacylink_uuid": privacylink_uuid,
        "privacylink_file": privacylink_file,
        "appname": appname,
        "genurl": f"{_settings.PROTOCOL}://{_settings.GENURL}" if _settings.GENURL else f"{_settings.PROTOCOL}://{full_url}",
        "urlLink": urlLink,
        "downloadLink": downloadLink,
        "delayFix": 'true' if delayFix else 'false',
        "rdgen": 'true',
        "xOffline": 'true' if xOffline else 'false',
        "removeNewVersionNotif": 'true' if removeNewVersionNotif else 'false',
        "compname": compname,
        "androidappid": androidappid,
        "filename": filename,
        "token": _settings.GHBEARER,
        "variant": variant if variant else 'client'
    }

    temp_json_path = f"data_{uuid.uuid4()}.json"
    zip_filename = f"secrets_{uuid.uuid4()}.zip"
    zip_path = "temp_zips/%s" % (zip_filename)
    Path("temp_zips").mkdir(parents=True, exist_ok=True)

    with open(temp_json_path, "w") as f:
        json.dump(inputs_raw, f)

    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(_settings.ZIP_PASSWORD.encode())
        zf.write(temp_json_path, arcname="secrets.json")

    if os.path.exists(temp_json_path):
        os.remove(temp_json_path)

    zipJson = {}
    zipJson['url'] = full_url
    zipJson['file'] = zip_filename

    zip_url = json.dumps(zipJson)

    data = {
        "ref": _settings.GHBRANCH,
        "inputs": {
            "version": version,
            "zip_url": zip_url
        },
        "return_run_details": True
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2022-11-28'
    }
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait"
    )
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 204 or response.status_code == 200:
            github_data = response.json() if response.status_code == 200 else {}
            run_id = github_data.get('workflow_run_id', 0)
            log_url = github_data.get('html_url', '')
            if run_id == 0:
                time.sleep(3)  # Give GitHub a moment to register the run
                try:
                    runs_url = f"https://api.github.com/repos/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs?per_page=5&event=workflow_dispatch"
                    runs_resp = requests.get(runs_url, headers=headers)
                    if runs_resp.status_code == 200:
                        runs_data = runs_resp.json()
                        for run in runs_data.get('workflow_runs', []):
                            if run.get('status') in ('queued', 'in_progress', 'waiting'):
                                run_id = run['id']
                                log_url = run.get('html_url', '')
                                break
                except Exception as e:
                    print(f"Could not find run ID: {e}")
            new_github_run.github_run_id = run_id
            new_github_run.status = "in_progress"
            new_github_run.save()

            return {
                "success": True,
                "uuid": myuuid,
                "filename": filename,
                "platform": platform,
                "log_url": log_url,
                "version": version
            }
        else:
            return {
                "success": False,
                "error": f"GitHub rejected the start request. Status: {response.status_code}, Msg: {response.text}",
                "status_code": 500
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "status_code": 500
        }


def _get_run_status(uuid_val):
    """
    Core status-check logic shared by web form and JSON API.

    Args:
        uuid_val: the UUID string of the generation run

    Returns:
        dict with 'found', 'status', 'github_log_url', and optionally 'gh_run'.
        If not found, 'found' is False.
    """
    try:
        gh_run = GithubRun.objects.get(uuid=uuid_val)
    except GithubRun.DoesNotExist:
        return {"found": False}

    github_log_url = f"https://github.com/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"

    if gh_run.status not in ['success', 'failure', 'cancelled', 'timed_out', 'skipped']:
        headers = {
            "Authorization": f"Bearer {_settings.GHBEARER}",
            "Accept": "application/vnd.github+json"
        }
        api_url = f"https://api.github.com/repos/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"
        
        try:
            gh_response = requests.get(api_url, headers=headers)
            if gh_response.status_code == 200:
                gh_data = gh_response.json()
                
                if gh_data.get('status') == 'completed':
                    gh_run.status = gh_data.get('conclusion', gh_run.status)
                    gh_run.save()
        except Exception as e:
            print(f"Error checking GitHub: {e}")

    return {
        "found": True,
        "status": gh_run.status,
        "github_log_url": github_log_url,
        "gh_run": gh_run
    }


def generator_view(request):
    if request.method == 'POST':
        form = GenerateForm(request.POST, request.FILES)
        if form.is_valid():
            params = form.cleaned_data
            full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"
            result = generate_custom_client(params, full_url)
            if result['success']:
                return render(request, 'waiting.html', {
                    'filename': result['filename'],
                    'uuid': result['uuid'],
                    'status': "Starting generator...please wait",
                    'platform': result['platform'],
                    'log_url': result['log_url'],
                    'version': result.get('version', '1.4.10-1')
                })
            else:
                return JsonResponse({"error": result['error']}, status=result.get('status_code', 500))
    else:
        form = GenerateForm()
    return render(request, 'generator.html', {'form': form})


def check_for_file(request):
    filename = request.GET.get('filename')
    uuid_val = request.GET.get('uuid')
    platform = request.GET.get('platform')
    version = request.GET.get('version', '1.4.10-1')

    result = _get_run_status(uuid_val)
    if not result['found']:
        from django.http import Http404
        raise Http404("Run not found")

    gh_run = result['gh_run']
    github_log_url = result['github_log_url']

    if gh_run.status == "success":
        return render(request, 'generated.html', {
            'filename': filename, 
            'uuid': uuid_val, 
            'platform': platform,
            'version': version
        })
        
    elif gh_run.status in ['failure', 'cancelled', 'timed_out', 'skipped', 'action_required']:
        return render(request, 'failure.html', {
            'log_url': github_log_url, 
            'filename': filename, 
            'uuid': uuid_val, 
            'platform': platform,
            'status': gh_run.status,
            'version': version
        })
        
    else:
        return render(request, 'waiting.html', {
            'filename': filename, 
            'uuid': uuid_val, 
            'status': gh_run.status, 
            'platform': platform, 
            'log_url': github_log_url,
            'version': version
        })


def download(request):
    filename = request.GET.get('filename')
    uuid_val = request.GET.get('uuid')
    client_version = request.GET.get('version', '1.4.10-1')
    
    from django.shortcuts import redirect
    
    # Try to construct GitHub Release URL
    try:
        gh_user = _settings.GHUSER
        gh_repo = _settings.REPONAME
        
        tag_candidates = [f"v{client_version}"]
        if uuid_val:
            tag_candidates.append(f"v{client_version}-{uuid_val}")
        
        for tag_name in tag_candidates:
            github_url = f"https://github.com/{gh_user}/{gh_repo}/releases/download/{tag_name}/{filename}"
            
            try:
                head_resp = requests.head(github_url, allow_redirects=True, timeout=10)
                if head_resp.status_code == 200:
                    return redirect(github_url)
            except Exception:
                pass
            
            try:
                headers = {
                    "Authorization": f"Bearer {_settings.GHBEARER}",
                    "Accept": "application/vnd.github+json"
                }
                api_url = f"https://api.github.com/repos/{gh_user}/{gh_repo}/releases/tags/{tag_name}"
                api_resp = requests.get(api_url, headers=headers, timeout=10)
                if api_resp.status_code == 200:
                    release_data = api_resp.json()
                    for asset in release_data.get('assets', []):
                        if asset.get('name') == filename:
                            return redirect(asset['browser_download_url'])
                    for asset in release_data.get('assets', []):
                        asset_name = asset.get('name', '')
                        base_filename = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        if base_filename in asset_name:
                            return redirect(asset['browser_download_url'])
            except Exception as e:
                print(f"Error querying GitHub API for tag {tag_name}: {e}")
        
    except Exception as e:
        print(f"Error constructing github url: {e}")

    # Fallback to local file if it exists
    if uuid_val and filename:
        file_path = os.path.join('exe', uuid_val, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                content = file.read()
            response = HttpResponse(content, headers={
                'Content-Type': 'application/vnd.microsoft.portable-executable',
                'Content-Disposition': f'attachment; filename="{filename}"'
            })
            return response
        
    return HttpResponse("File not found or not uploaded yet.", status=404)


def get_png(request):
    filename = os.path.basename(request.GET['filename'])
    uuid_val = os.path.basename(request.GET['uuid'])
    file_path = os.path.join('png', uuid_val, filename)
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response


def create_github_run(myuuid):
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait"
    )
    new_github_run.save()


def update_github_run(request):
    data = json.loads(request.body)
    myuuid = data.get('uuid')
    mystatus = data.get('status')
    GithubRun.objects.filter(Q(uuid=myuuid)).update(status=mystatus)
    return HttpResponse('')


def resize_and_encode_icon(imagefile):
    maxWidth = 200
    try:
        with io.BytesIO() as image_buffer:
            for chunk in imagefile.chunks():
                image_buffer.write(chunk)
            image_buffer.seek(0)

            img = Image.open(image_buffer)
            imgcopy = img.copy()
    except (IOError, OSError):
        raise ValueError("Uploaded file is not a valid image format.")

    if img.size[0] <= maxWidth:
        with io.BytesIO() as image_buffer:
            imgcopy.save(image_buffer, format=imagefile.content_type.split('/')[1])
            image_buffer.seek(0)
            return_image = ContentFile(image_buffer.read(), name=imagefile.name)
        return base64.b64encode(return_image.read())

    wpercent = (maxWidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))

    imgcopy = imgcopy.resize((maxWidth, hsize), Image.Resampling.LANCZOS)

    with io.BytesIO() as resized_image_buffer:
        imgcopy.save(resized_image_buffer, format=imagefile.content_type.split('/')[1])
        resized_image_buffer.seek(0)

        resized_imagefile = ContentFile(resized_image_buffer.read(), name=imagefile.name)

    resized64 = base64.b64encode(resized_imagefile.read())
    return resized64


def startgh(request):
    data_ = json.loads(request.body)
    url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-'+data_.get('platform')+'.yml/dispatches'  
    data = {
        "ref": _settings.GHBRANCH,
        "inputs":{
            "server":data_.get('server'),
            "key":data_.get('key'),
            "apiServer":data_.get('apiServer'),
            "custom":data_.get('custom'),
            "uuid":data_.get('uuid'),
            "iconlink":data_.get('iconlink'),
            "logolink":data_.get('logolink'),
            "appname":data_.get('appname'),
            "extras":data_.get('extras'),
            "filename":data_.get('filename')
        }
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2022-11-28'
    }
    response = requests.post(url, json=data, headers=headers)
    print(response)
    return HttpResponse(status=204)


def save_png(file, uuid, domain, name):
    file_save_path = "png/%s/%s" % (uuid, name)
    Path("png/%s" % uuid).mkdir(parents=True, exist_ok=True)

    if isinstance(file, str):
        try:
            header, encoded = file.split(';base64,')
            decoded_img = base64.b64decode(encoded)
            file = ContentFile(decoded_img, name=name)
        except ValueError:
            print("Invalid base64 data")
            return None
        except Exception as e:
            print(f"Error decoding base64: {e}")
            return None
        
    with open(file_save_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    return domain, uuid, name


def save_custom_client(request):
    """GitHub Actions workflow callback.

    Bu endpoint sadece iki iş yapar:
    1. GithubRun status'unu "success" olarak günceller (build tracking UI için)
    2. Dosya upload fallback'i (opsiyonel)

    client_downloads tablosuna yazma işi Go API tarafından yapılır
    (hem callback hem de cron sync ile).
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        if token != _settings.GHBEARER:
            return HttpResponse("Unauthorized", status=401)
    elif not request.FILES:
        return HttpResponse("Unauthorized", status=401)

    myuuid = request.POST.get('uuid')
    filename = request.POST.get('filename')

    if myuuid:
        try:
            gh_run = GithubRun.objects.filter(uuid=myuuid).first()
            if gh_run:
                gh_run.status = "success"
                gh_run.save()
        except Exception as e:
            print(f"Error updating GithubRun status: {e}")

    if 'file' in request.FILES:
        try:
            file = request.FILES['file']
            file_save_path = f"exe/{myuuid}/{file.name}"
            Path(f"exe/{myuuid}").mkdir(parents=True, exist_ok=True)
            with open(file_save_path, "wb+") as f:
                for chunk in file.chunks():
                    f.write(chunk)
            if not filename:
                filename = file.name
        except Exception as e:
            print(f"Error saving uploaded file: {e}")

    return HttpResponse("OK")


def cleanup_secrets(request):
    data = json.loads(request.body)
    my_uuid = data.get('uuid')
    
    if not my_uuid:
        return HttpResponse("Missing UUID", status=400)

    temp_dir = os.path.join('temp_zips')
    
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            if my_uuid in filename and filename.endswith('.zip'):
                file_path = os.path.join(temp_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"Successfully deleted {file_path}")
                except OSError as e:
                    print(f"Error deleting file: {e}")

    return HttpResponse("Cleanup successful", status=200)


def get_zip(request):
    filename = request.GET['filename']
    base_dir = os.path.abspath('temp_zips')
    file_path = os.path.abspath(os.path.join(base_dir, filename))
    if not file_path.startswith(base_dir + os.sep):
        return HttpResponseForbidden("Invalid filename")
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/zip',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response

def health_check(request):
    return JsonResponse({"status": "ok", "service": "acilbir-generator"})
