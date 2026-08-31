try:
    import jwt
except ImportError:
    jwt = None
import os
from django.conf import settings as _settings

# Secret key for verifying JWT tokens (shared with main website / Go backend)
JWT_SECRET = os.environ.get('JWT_SECRET', getattr(_settings, 'SECRET_KEY', 'secret'))
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ALLOWED_ROLES = os.environ.get('ALLOWED_ROLES', 'admin,tech_support,developer,superadmin').split(',')


def extract_token(request):
    """
    Extract JWT token from Authorization header, query parameter, or cookies.
    """
    # 1. Authorization: Bearer <TOKEN>
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1].strip()

    # 2. Cookies (SSO: auth_token, access_token from Vue dashboard; api-token from Go API)
    for cookie_name in ['auth_token', 'access_token', 'api-token', 'token', 'jwt', 'session_token']:
        token = request.COOKIES.get(cookie_name)
        if token:
            return token.strip()

    # 3. Query string parameter (?token=...)
    token_param = request.GET.get('token') or request.POST.get('token')
    if token_param:
        return token_param.strip()

    return None


def verify_token(token):
    """
    Verify and decode JWT token. Also checks for legacy API secret tokens.
    
    Returns:
        tuple: (is_valid: bool, payload_or_error: dict/str)
    """
    if not token:
        return False, "No token provided"

    # Allow direct API Key fallback (e.g. GHBEARER or SH_SECRET or API_SECRET_KEY)
    direct_keys = [
        getattr(_settings, 'GHBEARER', ''),
        getattr(_settings, 'SH_SECRET', ''),
        os.environ.get('API_SECRET_KEY', '')
    ]
    direct_keys = [k for k in direct_keys if k]
    if token in direct_keys:
        return True, {"sub": "system", "role": "admin", "is_api_key": True}

    if not jwt:
        return False, "PyJWT package not installed on server"

    candidate_keys = [
        os.environ.get('JWT_SECRET'),
        os.environ.get('ACILBIR_API_JWT_KEY'),
        os.environ.get('RUSTDESK_API_JWT_KEY'),
        getattr(_settings, 'SECRET_KEY', None)
    ]
    candidate_keys = [k for k in candidate_keys if k]

    last_error = "Invalid token signature"
    for key in candidate_keys:
        try:
            payload = jwt.decode(token, key, algorithms=["HS256", "HS384", "HS512"])
            user_role = payload.get('role') or payload.get('user_role') or ('admin' if payload.get('is_admin') else None)
            
            # If payload contains user_id / id or is_admin, consider valid admin user
            if ALLOWED_ROLES and user_role and user_role not in ALLOWED_ROLES:
                return False, f"Role '{user_role}' is not authorized to access generator"

            return True, payload
        except jwt.ExpiredSignatureError:
            return False, "Token has expired"
        except jwt.InvalidTokenError as e:
            last_error = str(e)
            continue

    return False, f"Invalid token: {last_error}"
