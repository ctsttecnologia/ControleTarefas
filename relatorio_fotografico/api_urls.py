
# relatorio_fotografico/api_urls.py
from rest_framework.routers import DefaultRouter
from .api_views import RelatorioFotograficoViewSet, FotoRelatorioViewSet

router = DefaultRouter()
router.register('relatorios', RelatorioFotograficoViewSet, basename='api-relatorio')
router.register('fotos', FotoRelatorioViewSet, basename='api-foto')

urlpatterns = router.urls


