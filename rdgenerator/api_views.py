import json
from django.http import JsonResponse
from django.conf import settings as _settings
from .views import generate_custom_client, _get_run_status


# Field validation constraints (mirrored from GenerateForm)
PLATFORM_CHOICES = ['windows', 'windows-x86', 'linux', 'android', 'macos']
VERSION_CHOICES = ['master', 'nightly', '1.4.10-1', '1.4.10', '1.4.9', '1.4.8', '1.4.7', '1.4.6', '1.4.5', '1.4.4', '1.4.3', '1.4.2', '1.4.1', '1.4.0']
DIRECTION_CHOICES = ['incoming', 'outgoing', 'both']
INSTALLATION_CHOICES = ['installationY', 'installationN']
SETTINGS_CHOICES = ['settingsY', 'settingsN']
THEME_CHOICES = ['light', 'dark', 'system']
THEME_DORO_CHOICES = ['default', 'override']
PASS_APPROVE_MODE_CHOICES = ['password', 'click', 'password-click']
PERMISSIONS_DORO_CHOICES = ['default', 'override']
PERMISSIONS_TYPE_CHOICES = ['custom', 'full', 'view']

# Boolean fields
BOOL_FIELDS = [
    'delayFix', 'xOffline', 'hidecm', 'removeNewVersionNotif',
    'denyLan', 'enableDirectIP', 'autoClose',
    'enableKeyboard', 'enableClipboard', 'enableFileTransfer', 'enableAudio',
    'enableTCP', 'enableRemoteRestart', 'enableRecording', 'enableBlockingInput',
    'enableRemoteModi', 'removeWallpaper', 'enablePrinter', 'enableCamera', 'enableTerminal',
]

# Optional string fields (no validation needed, just accept as-is)
OPTIONAL_STR_FIELDS = [
    'sh_secret_field', 'serverIP', 'key', 'apiServer', 'urlLink', 'downloadLink',
    'appname', 'compname', 'androidappid', 'permanentPassword',
    'defaultManual', 'overrideManual',
    'iconbase64', 'logobase64', 'privacybase64', 'variant',
]


def validate_generate_params(data):
    """
    Validate JSON API parameters against the same constraints as GenerateForm.

    Returns:
        tuple: (cleaned_data dict, errors dict)
        If errors is non-empty, validation failed.
    """
    errors = {}
    cleaned = {}

    # Required string field
    exename = data.get('exename', '')
    if not exename:
        errors['exename'] = 'This field is required.'
    else:
        cleaned['exename'] = exename

    # Choice fields
    choice_validations = {
        'platform': (PLATFORM_CHOICES, 'windows'),
        'version': (VERSION_CHOICES, '1.4.10-1'),
        'direction': (DIRECTION_CHOICES, 'both'),
        'installation': (INSTALLATION_CHOICES, 'installationY'),
        'settings': (SETTINGS_CHOICES, 'settingsY'),
        'theme': (THEME_CHOICES, 'system'),
        'themeDorO': (THEME_DORO_CHOICES, 'default'),
        'passApproveMode': (PASS_APPROVE_MODE_CHOICES, 'password-click'),
        'permissionsDorO': (PERMISSIONS_DORO_CHOICES, 'default'),
        'permissionsType': (PERMISSIONS_TYPE_CHOICES, 'custom'),
    }
    for field, (choices, default) in choice_validations.items():
        value = data.get(field, default)
        if value not in choices:
            errors[field] = f'Invalid choice. Must be one of: {choices}'
        else:
            cleaned[field] = value

    # Boolean fields
    for field in BOOL_FIELDS:
        value = data.get(field, False)
        if not isinstance(value, bool):
            errors[field] = 'Must be a boolean value.'
        else:
            cleaned[field] = value

    # Optional string fields
    for field in OPTIONAL_STR_FIELDS:
        cleaned[field] = data.get(field, '')

    # File fields are not used in API mode (base64 fields are used instead)
    cleaned['iconfile'] = None
    cleaned['logofile'] = None
    cleaned['privacyfile'] = None

    return cleaned, errors


def api_generate(request):
    """
    POST /api/generate

    Accepts a JSON body with client configuration parameters and triggers
    the custom client generation process via GitHub Actions.

    Returns JSON with success status, uuid, filename, platform, and log_url.
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"success": False, "error": f"Invalid JSON: {str(e)}"}, status=400)

    cleaned, errors = validate_generate_params(data)
    if errors:
        return JsonResponse({
            "success": False,
            "error": "Validation errors",
            "details": errors
        }, status=400)

    # Build full_url the same way as generator_view
    full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"

    result = generate_custom_client(cleaned, full_url)

    if result['success']:
        # Add convenience URLs for the API consumer
        result['status_url'] = f"/api/status?uuid={result['uuid']}&platform={result['platform']}&filename={result['filename']}"
        return JsonResponse(result)
    else:
        return JsonResponse({"success": False, "error": result['error']}, status=result.get('status_code', 500))


def api_status(request):
    """
    GET /api/status

    Checks the generation status for a given UUID.
    Returns JSON with status, uuid, and optional log_url/filename/platform.
    """
    if request.method != 'GET':
        return JsonResponse({"success": False, "error": "Method not allowed. Use GET."}, status=405)

    uuid_val = request.GET.get('uuid')
    if not uuid_val:
        return JsonResponse({"error": "Missing required parameter: uuid"}, status=400)

    filename = request.GET.get('filename', '')
    platform = request.GET.get('platform', '')

    result = _get_run_status(uuid_val)

    if not result['found']:
        return JsonResponse({"error": "Run not found"}, status=404)

    response_data = {
        "status": result['status'],
        "uuid": uuid_val,
        "log_url": result['github_log_url'],
    }
    if filename:
        response_data['filename'] = filename
    if platform:
        response_data['platform'] = platform

    return JsonResponse(response_data)


from .models import ClientProfile

def profile_to_dict(profile, request=None):
    base_url = ""
    if request:
        base_url = f"{_settings.PROTOCOL}://{request.get_host()}"
    return {
        "id": profile.id,
        "name": profile.name,
        "variant": profile.variant,
        "exename": profile.exename,
        "appname": profile.appname,
        "compname": profile.compname,
        "androidappid": profile.androidappid,
        "serverIP": profile.serverIP,
        "key": profile.key,
        "apiServer": profile.apiServer,
        "urlLink": profile.urlLink,
        "downloadLink": profile.downloadLink,
        "icon_url": f"{base_url}{profile.icon_image.url}" if profile.icon_image else "",
        "logo_url": f"{base_url}{profile.logo_image.url}" if profile.logo_image else "",
        "privacy_url": f"{base_url}{profile.privacy_image.url}" if profile.privacy_image else "",
        "iconbase64": profile.iconbase64 or "",
        "logobase64": profile.logobase64 or "",
        "privacybase64": profile.privacybase64 or "",
        "config_data": profile.config_data or {},
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def api_profiles_list_create(request):
    """
    GET /api/profiles - List all saved client profiles
    POST /api/profiles - Create a new client profile
    """
    if request.method == 'GET':
        profiles = ClientProfile.objects.all().order_by('-updated_at')
        return JsonResponse({"success": True, "profiles": [profile_to_dict(p, request) for p in profiles]})

    elif request.method == 'POST':
        try:
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Invalid payload: {str(e)}"}, status=400)

        name = data.get('name')
        if not name:
            return JsonResponse({"success": False, "error": "Profile name is required."}, status=400)

        profile = ClientProfile(
            name=name,
            variant=data.get('variant', 'client'),
            exename=data.get('exename', 'rustdesk'),
            appname=data.get('appname', 'rustdesk'),
            compname=data.get('compname', 'Purslane Ltd'),
            androidappid=data.get('androidappid', 'com.carriez.flutter_hbb'),
            serverIP=data.get('serverIP', ''),
            key=data.get('key', ''),
            apiServer=data.get('apiServer', ''),
            urlLink=data.get('urlLink', ''),
            downloadLink=data.get('downloadLink', ''),
            iconbase64=data.get('iconbase64', ''),
            logobase64=data.get('logobase64', ''),
            privacybase64=data.get('privacybase64', ''),
            config_data=data.get('config_data', {}) if isinstance(data.get('config_data'), dict) else {}
        )

        if 'iconfile' in request.FILES:
            profile.icon_image = request.FILES['iconfile']
        if 'logofile' in request.FILES:
            profile.logo_image = request.FILES['logofile']
        if 'privacyfile' in request.FILES:
            profile.privacy_image = request.FILES['privacyfile']

        profile.save()
        return JsonResponse({"success": True, "profile": profile_to_dict(profile, request)}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def api_profile_detail_update_delete(request, profile_id):
    """
    GET /api/profiles/<id> - Fetch profile
    POST/PUT /api/profiles/<id> - Update profile
    DELETE /api/profiles/<id> - Delete profile
    """
    try:
        profile = ClientProfile.objects.get(id=profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profile not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse({"success": True, "profile": profile_to_dict(profile, request)})

    elif request.method in ['POST', 'PUT']:
        try:
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Invalid payload: {str(e)}"}, status=400)

        for field in ['name', 'variant', 'exename', 'appname', 'compname', 'androidappid',
                      'serverIP', 'key', 'apiServer', 'urlLink', 'downloadLink',
                      'iconbase64', 'logobase64', 'privacybase64']:
            if field in data:
                setattr(profile, field, data[field])

        if 'config_data' in data and isinstance(data['config_data'], dict):
            profile.config_data = data['config_data']

        if 'iconfile' in request.FILES:
            profile.icon_image = request.FILES['iconfile']
        if 'logofile' in request.FILES:
            profile.logo_image = request.FILES['logofile']
        if 'privacyfile' in request.FILES:
            profile.privacy_image = request.FILES['privacyfile']

        profile.save()
        return JsonResponse({"success": True, "profile": profile_to_dict(profile, request)})

    elif request.method == 'DELETE':
        profile.delete()
        return JsonResponse({"success": True, "message": "Profile deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


def api_profile_build(request, profile_id):
    """
    POST /api/profiles/<id>/build
    Triggers build using profile's stored settings and images.
    Accepts optional overrides in JSON payload (e.g. platform, version).
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed. Use POST."}, status=405)

    try:
        profile = ClientProfile.objects.get(id=profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profile not found"}, status=404)

    overrides = {}
    if request.body:
        try:
            overrides = json.loads(request.body)
        except Exception:
            pass

    # Merge profile fields + config_data + overrides
    params = {
        'sh_secret_field': _settings.SH_SECRET,
        'platform': overrides.get('platform', 'windows'),
        'version': overrides.get('version', '1.4.10-1'),
        'variant': profile.variant or 'client',
        'exename': profile.exename or 'AcilBir',
        'appname': profile.appname or 'AcilBir',
        'compname': profile.compname or 'ABT Bilgisayar Programlama ve Tic.Ltd.Sti.',
        'androidappid': profile.androidappid or 'com.acilbir.app',
        'serverIP': profile.serverIP or '',
        'key': profile.key or '',
        'apiServer': profile.apiServer or '',
        'urlLink': profile.urlLink or '',
        'downloadLink': profile.downloadLink or '',
        'iconbase64': profile.iconbase64 or '',
        'logobase64': profile.logobase64 or '',
        'privacybase64': profile.privacybase64 or '',
    }

    if profile.config_data and isinstance(profile.config_data, dict):
        params.update(profile.config_data)

    params.update(overrides)

    cleaned, errors = validate_generate_params(params)
    if errors:
        return JsonResponse({"success": False, "error": "Validation errors", "details": errors}, status=400)

    full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"

    result = generate_custom_client(cleaned, full_url)

    if result['success']:
        result['status_url'] = f"/api/status?uuid={result['uuid']}&platform={result['platform']}&filename={result['filename']}"
        result['profile_id'] = profile.id
        result['profile_name'] = profile.name
        return JsonResponse(result)
    else:
        return JsonResponse({"success": False, "error": result['error']}, status=result.get('status_code', 500))

