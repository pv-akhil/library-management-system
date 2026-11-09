from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts import views as account_views
from library import views as library_views
from transactions import views as trans_views
from reservations import views as res_views

# DRF API Router
router = DefaultRouter()
router.register(r'users', account_views.UserViewSet, basename='user')
router.register(r'categories', library_views.CategoryViewSet, basename='category')
router.register(r'authors', library_views.AuthorViewSet, basename='author')
router.register(r'publishers', library_views.PublisherViewSet, basename='publisher')
router.register(r'books', library_views.BookViewSet, basename='book')
router.register(r'copies', library_views.BookCopyViewSet, basename='bookcopy')
router.register(r'transactions', trans_views.TransactionViewSet, basename='transaction')
router.register(r'fines', trans_views.FineViewSet, basename='fine')
router.register(r'reservations', res_views.ReservationViewSet, basename='reservation')


def service_worker(request):
    """Serve PWA service worker with correct scope and content-type."""
    with open(settings.BASE_DIR / 'static' / 'pwa' / 'sw.js', 'r') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def pwa_manifest(request):
    """Serve PWA manifest with correct JSON content-type."""
    with open(settings.BASE_DIR / 'static' / 'pwa' / 'manifest.json', 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/manifest+json')


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication Web Routes
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('register/', account_views.register_view, name='register'),

    # PWA Support
    path('manifest.json', pwa_manifest, name='pwa_manifest'),
    path('sw.js', service_worker, name='service_worker'),

    # Web Applications
    path('', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('catalog/', include('library.urls', namespace='library')),
    path('circulation/', include('transactions.urls', namespace='transactions')),
    path('reservations/', include('reservations.urls', namespace='reservations')),

    # REST API Specific Endpoints (before router so exact paths match)
    path('api/v1/auth/register/', account_views.RegisterAPIView.as_view(), name='api_register'),
    path('api/v1/auth/me/', account_views.CurrentUserAPIView.as_view(), name='api_me'),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/circulation/issue/', trans_views.IssueBookAPIView.as_view(), name='api_issue_book'),
    path('api/v1/circulation/return/', trans_views.ReturnBookAPIView.as_view(), name='api_return_book'),
    path('api/v1/reservations/reserve/', res_views.ReserveBookAPIView.as_view(), name='api_reserve_book'),
    path('api/v1/', include(router.urls)),

    # OpenAPI 3.0 Documentation (Swagger & ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Static & Media serving during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
