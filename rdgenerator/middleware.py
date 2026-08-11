from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings as _settings
from urllib.parse import quote, urlencode, urlparse, urlunparse, parse_qs
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

LOGIN_URL = os.environ.get('LOGIN_URL', 'https://acilbir.com/console/login')
ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'True').lower() in ['true', '1', 't']

HTML_401_PAGE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erişim Engellendi — AcilBir.com</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; max-width: 450px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
        .icon { font-size: 48px; margin-bottom: 16px; }
        h1 { font-size: 22px; font-weight: 700; margin: 0 0 12px 0; color: #ef4444; }
        p { color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }
        .btn { display: inline-block; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; }
        .tip { font-size: 12px; color: #64748b; margin-top: 20px; }
        code { background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; color: #60a5fa; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🔒</div>
        <h1>Yetkisiz Erişim (401)</h1>
        <p>Bu alana erişebilmek için <strong>AcilBir.com Admin Paneli</strong> üzerinde yetkili oturum açmış olmanız veya geçerli bir gizli erişim anahtarına sahip olmanız gerekmektedir.</p>
        <a href="__LOGIN_URL__" class="btn">Admin Paneline Giriş Yap</a>
        <div class="tip">Gizli anahtarınız varsa: <code>?secret=ŞİFRE</code> kullanabilirsiniz.</div>
    </div>
</body>
</html>"""


def _get_cookie_domain(request):
    """Derive the root domain for cross-subdomain cookie scope.

    For 'generator.acilbir.com' → '.acilbir.com'
    For 'localhost' or IP addresses → None (no domain scope)
    """
    host = request.get_host().split(':')[0]  # Strip port
    parts = host.split('.')
    if len(parts) >= 2 and not host.replace('.', '').isdigit():
        return '.' + '.'.join(parts[-2:])
    return None


def _strip_token_from_url(absolute_uri):
    """Remove the 'token' query parameter from a URL to produce a clean redirect target."""
    parsed = urlparse(absolute_uri)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs.pop('token', None)
    clean_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=clean_query))


class RdgenAuthMiddleware:
    """
    Middleware that enforces JWT / Cookie SSO Authentication across rdgen.
    
    - Web generator pages (/ and /generator) block unauthenticated users with a 401 Access Denied page.
    - JSON API endpoints (/api/generate and /api/status) return HTTP 401 JSON error for unauthenticated requests.
    - Callback and public download endpoints are exempt.
    - When a ?token= query parameter is present (e.g. from dashboard SSO link),
      the token is persisted as an auth_token cookie and the user is redirected
      to a clean URL (without the token in the query string).
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

        # ── Token-in-URL SSO flow ──
        # Dashboard opens generator with ?token=... in a new tab.
        # Persist it as a cookie and redirect to a clean URL so the token
        # isn't leaked in referrer headers or browser history.
        url_token = request.GET.get('token')
        if url_token:
            is_valid, _ = verify_token(url_token)
            if is_valid:
                clean_url = _strip_token_from_url(request.build_absolute_uri())
                # Ensure HTTPS if PROTOCOL setting says so
                protocol = getattr(_settings, 'PROTOCOL', 'https')
                if protocol == 'https' and clean_url.startswith('http://'):
                    clean_url = 'https://' + clean_url[7:]
                response = HttpResponseRedirect(clean_url)
                cookie_domain = _get_cookie_domain(request)
                cookie_kwargs = {
                    'max_age': 7 * 24 * 60 * 60,  # 7 days, matching Vue dashboard
                    'path': '/',
                    'httponly': False,  # Must be readable by frontend JS
                    'samesite': 'Lax',
                }
                if cookie_domain:
                    cookie_kwargs['domain'] = cookie_domain
                if protocol == 'https':
                    cookie_kwargs['secure'] = True
                response.set_cookie('auth_token', url_token, **cookie_kwargs)
                response.set_cookie('access_token', url_token, **cookie_kwargs)
                return response

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

            # Web page requests return custom HTML 401 Access Denied page with return redirect
            from django.http import HttpResponse
            target_uri = request.build_absolute_uri()
            protocol = getattr(_settings, 'PROTOCOL', 'https')
            if protocol == 'https' and target_uri.startswith('http://'):
                target_uri = 'https://' + target_uri[7:]
            login_target = f"{LOGIN_URL}?redirect={quote(target_uri)}"
            page_html = HTML_401_PAGE.replace('__LOGIN_URL__', login_target)
            return HttpResponse(page_html, status=401)

        # Attach auth payload to request for downstream views if needed
        request.jwt_user = payload_or_err if isinstance(payload_or_err, dict) else {}

        return self.get_response(request)

