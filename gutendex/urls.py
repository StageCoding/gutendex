from django.urls import include, re_path
from django.views.generic import TemplateView

from rest_framework import routers

from books import views


router = routers.DefaultRouter()
router.register(r'books', views.BookViewSet)
router.register(r'libraryCategories', views.LibraryCategoriesViewSet, basename='library-categories')

urlpatterns = [
    re_path(r'^$', TemplateView.as_view(template_name='home.html')),
    re_path(r'^', include(router.urls)),
]
