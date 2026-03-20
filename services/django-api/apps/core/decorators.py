"""ForgeLink Permission Decorators"""
from functools import wraps
from django.http import JsonResponse


def require_roles(*allowed_roles):
    """
    Decorator to require specific roles for a view.

    Usage:
        @require_roles('FACTORY_ADMIN', 'PLANT_OPERATOR')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user_roles'):
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=401
                )

            user_roles = set(request.user_roles)
            required_roles = set(allowed_roles)

            if not user_roles & required_roles:
                return JsonResponse(
                    {'error': 'Insufficient permissions'},
                    status=403
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_factory_admin(view_func):
    """Decorator to require FACTORY_ADMIN role."""
    return require_roles('FACTORY_ADMIN')(view_func)


def require_plant_operator(view_func):
    """Decorator to require PLANT_OPERATOR or higher."""
    return require_roles('FACTORY_ADMIN', 'PLANT_OPERATOR')(view_func)


def require_technician(view_func):
    """Decorator to require TECHNICIAN or higher."""
    return require_roles('FACTORY_ADMIN', 'PLANT_OPERATOR', 'TECHNICIAN')(view_func)


def require_authenticated(view_func):
    """Decorator to require any authenticated user."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'jwt_payload') or request.jwt_payload is None:
            return JsonResponse(
                {'error': 'Authentication required'},
                status=401
            )
        return view_func(request, *args, **kwargs)
    return wrapper
