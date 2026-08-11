from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings as _settings
from urllib.parse import quote
import os
from .auth import extract_token, verify_token

EXEMPT_PATHS = [
    '/get_png',
    '/save_custom_client',
    '/cleanzip',
    '/download',
    '/updategh',
    '/creategh',
    '/startgh',
    '/get_zip',
]

LOGIN_URL = os.environ.get('LOGIN_URL', 'https://acilbir.com/console/#/login')
ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'True').lower() in ['true', '1', 't']


class RdgenAuthMiddleware:
    """
    Middleware that enforces JWT / Cookie SSO Authentication across rdgen.
    
    - Web generator pages (/ and /generator) redirect unauthenticated users to acilbir.com/login.
    - JSON API endpoints (/api/generate and /api/status) return HTTP 401 JSON error for unauthenticated requests.
    - Callback and public download endpoints are exempt.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not ENABLE_AUTH:
            return self.get_response(request)

        path = request.path

        # Check exempt paths
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt):
                return self.get_response(request)

        # Allow query string secret bypass for convenience (e.g. ?secret=SH_SECRET)
        secret_param = request.GET.get('secret') or request.POST.get('secret')
        if secret_param and getattr(_settings, 'SH_SECRET', None) and secret_param == _settings.SH_SECRET:
            return self.get_response(request)

        # Extract and verify JWT / Bearer / Cookie token
        token = extract_token(request)
        is_valid, payload_or_err = verify_token(token)

        if not is_valid:
            # API requests return 401 JSON error
            if path.startswith('/api/'):
                return JsonResponse({
                    "success": False,
                    "error": "Unauthorized",
                    "details": payload_or_err
                }, status=401)

            # Web page requests redirect to login page or return 403
            redirect_target = f"{LOGIN_URL}?redirect={quote(request.build_absolute_uri())}"
            return HttpResponseRedirect(redirect_target)

        # Attach auth payload to request for downstream views if needed
        request.jwt_user = payload_or_err if isinstance(payload_or_err, dict) else {}

        return self.get_response(request)
