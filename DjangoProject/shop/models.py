from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    shipping_address = models.TextField(max_length=255)
    preferred_language = models.CharField(max_length=10, default='en')
    role = models.CharField(
        max_length=20,
        choices=[('vendor', _('Vendor')), ('customer', _('Customer'))],
        default='customer'
    )

    def __str__(self):
        return self.full_name


class Vendor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contact_email = models.EmailField(max_length=255)
    contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('draft', _('Draft')),
        ('archived', _('Archived')),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products', null=True,
                              blank=True)

    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def primary_image_url(self):
        if self.image:
            return self.image.url
        gallery_image = self.images.first()
        return gallery_image.image.url if gallery_image else ''

    @property
    def average_rating(self):
        values = list(self.reviews.values_list('rating', flat=True))
        if not values:
            return Decimal('0.0')
        return round(sum(values) / len(values), 1)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_gallery/')

    def __str__(self):
        return f"Image for {self.product.name}"


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('shipped', _('Shipped')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled')),
        ('hold', _('Hold')),
        ('returned', _('Returned')),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.CharField(max_length=255, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    held_at = models.DateTimeField(null=True, blank=True)
    status_updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def allowed_next_statuses(self):
        transitions = {
            'pending': ['hold', 'shipped', 'cancelled'],
            'hold': ['pending', 'shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': [],
            'returned': [],
        }
        return transitions.get(self.status, [])

    @property
    def next_status_choices(self):
        labels = dict(self.STATUS_CHOICES)
        return [(value, labels.get(value, value)) for value in self.allowed_next_statuses()]

    def update_status(self, new_status, changed_by=None):
        if new_status == self.status:
            return

        if new_status not in self.allowed_next_statuses():
            raise ValueError(f'Invalid status transition from {self.status} to {new_status}')

        previous_status = self.status
        now = timezone.now()
        self.status = new_status
        self.status_updated_at = now

        if new_status == 'shipped':
            self.shipped_at = now
        elif new_status == 'delivered':
            self.delivered_at = now
        elif new_status == 'cancelled':
            self.cancelled_at = now
        elif new_status == 'hold':
            self.held_at = now

        self.save(update_fields=[
            'status',
            'status_updated_at',
            'shipped_at',
            'delivered_at',
            'cancelled_at',
            'held_at',
        ])
        OrderStatusHistory.objects.create(
            order=self,
            from_status=previous_status,
            to_status=new_status,
            changed_by=changed_by,
        )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} at ${self.unit_price}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changed_orders',
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'Order #{self.order_id}: {self.from_status} -> {self.to_status}'

    @property
    def from_status_display(self):
        return dict(Order.STATUS_CHOICES).get(self.from_status, self.from_status)

    @property
    def to_status_display(self):
        return dict(Order.STATUS_CHOICES).get(self.to_status, self.to_status)


class Notification(models.Model):
    KIND_CHOICES = [
        ('system', _('System')),
        ('order', _('Order')),
        ('review', _('Review')),
        ('inventory', _('Inventory')),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='system')
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_read', '-created_at']

    def __str__(self):
        return f'{self.title} -> {self.recipient.username}'


