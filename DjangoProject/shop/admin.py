from django.contrib import admin

from .models import CartItem, Category, Notification, Order, OrderItem, OrderStatusHistory, Product, ProductImage, Review, Tag


class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'owner', 'category', 'price', 'stock', 'status', 'created_at')
	list_filter = ('status', 'category')
	search_fields = ('name', 'description', 'owner__username')
	inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'total_amount', 'created_at', 'status_updated_at')
	list_filter = ('status',)
	search_fields = ('user__username', 'user__email')


admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(CartItem)
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
admin.site.register(Notification)
admin.site.register(Review)
