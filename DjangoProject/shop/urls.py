# shop/urls.py
from django.urls import path
from . import views
app_name = 'shop'
urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/<int:pk>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/<int:item_id>/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/<int:item_id>/remove/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/', views.order, name='order'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('manage/', views.manage, name='manage'),
    path('manage/products/new/', views.manage_product_editor, name='manage_product_new'),
    path('manage/products/<int:pk>/edit/', views.manage_product_editor, name='manage_product_edit'),
    path('manage/product/<int:pk>/status/', views.toggle_product_status, name='toggle_product_status'),
    path('manage/orders/', views.merchant_orders, name='merchant_orders'),
    path('manage/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/action/', views.notification_action, name='notification_action'),
    path('api/products', views.product_api, name='product_api'),
    path('api/products/<int:pk>/', views.product_api, name='product_api_detail'),
    path('api/products/<int:pk>/reviews/', views.review_api, name='review_api'),
    path('api/cart/', views.cart_api, name='cart_api'),
    path('api/orders/', views.orders_api, name='orders_api'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
]