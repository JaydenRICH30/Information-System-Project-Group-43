from django.urls import path
from . import views


app_name = 'login'
urlpatterns = [
    path('', views.unlogin, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('index/', views.index, name='index'),

    path('index/account/', views.account, name='account'),
    path('api/currentUser', views.current_user_api, name='current_user_api'),
    path('api/user/status', views.user_status_api, name='user_status_api'),

]