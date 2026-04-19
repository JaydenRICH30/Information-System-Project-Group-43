from django.core.management.base import BaseCommand

from login.models import User

from shop.models import CartItem, Category, Notification, Order, OrderItem, Product, Review, Tag


class Command(BaseCommand):
    help = 'Create reusable demo users, products, orders, reviews, and notifications.'

    def handle(self, *args, **options):
        merchant, _ = User.objects.get_or_create(
            email='merchant.demo@example.com',
            defaults={
                'username': 'merchant_demo',
                'role': 'merchant',
                'address': '88 Seller Street, Shenzhen',
            },
        )
        merchant.set_password('DemoPass123')
        merchant.save()

        customer, _ = User.objects.get_or_create(
            email='customer.demo@example.com',
            defaults={
                'username': 'customer_demo',
                'role': 'customer',
                'address': '66 Buyer Avenue, Shanghai',
            },
        )
        customer.set_password('DemoPass123')
        customer.save()

        electronics, _ = Category.objects.get_or_create(name='Electronics')
        lifestyle, _ = Category.objects.get_or_create(name='Lifestyle')
        eco, _ = Tag.objects.get_or_create(name='eco')
        smart, _ = Tag.objects.get_or_create(name='smart')
        premium, _ = Tag.objects.get_or_create(name='premium')

        catalog = [
            {
                'name': 'Smart Lamp Pro',
                'description': '<p>Voice-ready lamp with warm and cool light modes.</p><ul><li>Wi-Fi enabled</li><li>Energy saving</li></ul>',
                'price': '59.90',
                'stock': 18,
                'category': electronics,
                'tags': [smart, eco],
            },
            {
                'name': 'Travel Bottle Max',
                'description': '<p>Insulated bottle for long daily commutes and travel.</p><ul><li>Hot 12h</li><li>Cold 24h</li></ul>',
                'price': '24.50',
                'stock': 35,
                'category': lifestyle,
                'tags': [eco, premium],
            },
            {
                'name': 'Desk Hub Mini',
                'description': '<p>Compact USB-C hub for home office and mobile work.</p><ul><li>HDMI output</li><li>Fast charging</li></ul>',
                'price': '39.00',
                'stock': 22,
                'category': electronics,
                'tags': [smart],
            },
        ]

        products = []
        for item in catalog:
            product, _ = Product.objects.get_or_create(
                owner=merchant,
                name=item['name'],
                defaults={
                    'description': item['description'],
                    'price': item['price'],
                    'stock': item['stock'],
                    'category': item['category'],
                    'status': 'active',
                },
            )
            product.description = item['description']
            product.price = item['price']
            product.stock = item['stock']
            product.category = item['category']
            product.status = 'active'
            product.save()
            product.tags.set(item['tags'])
            products.append(product)

        pending_order, _ = Order.objects.get_or_create(
            user=customer,
            status='pending',
            total_amount='98.90',
            total_price='98.90',
            shipping_address=customer.address,
        )
        OrderItem.objects.get_or_create(
            order=pending_order,
            product=products[0],
            defaults={
                'quantity': 1,
                'unit_price': products[0].price,
                'subtotal': products[0].price,
            },
        )
        OrderItem.objects.get_or_create(
            order=pending_order,
            product=products[1],
            defaults={
                'quantity': 1,
                'unit_price': products[1].price,
                'subtotal': products[1].price,
            },
        )

        delivered_order, _ = Order.objects.get_or_create(
            user=customer,
            status='delivered',
            total_amount='39.00',
            total_price='39.00',
            shipping_address=customer.address,
        )
        delivered_order.shipped_at = delivered_order.shipped_at or delivered_order.created_at
        delivered_order.delivered_at = delivered_order.delivered_at or delivered_order.created_at
        delivered_order.status_updated_at = delivered_order.status_updated_at or delivered_order.created_at
        delivered_order.save(update_fields=['shipped_at', 'delivered_at', 'status_updated_at'])
        OrderItem.objects.get_or_create(
            order=delivered_order,
            product=products[2],
            defaults={
                'quantity': 1,
                'unit_price': products[2].price,
                'subtotal': products[2].price,
            },
        )

        Review.objects.get_or_create(
            user=customer,
            product=products[2],
            defaults={
                'rating': 5,
                'comment': 'Compact, stable, and very useful for a laptop setup.',
            },
        )

        CartItem.objects.get_or_create(user=customer, product=products[0], defaults={'quantity': 1})

        Notification.objects.get_or_create(
            recipient=customer,
            title='Demo order ready',
            defaults={
                'kind': 'order',
                'message': f'Order #{pending_order.id} is waiting for merchant processing.',
                'link': '/shop/order/',
            },
        )
        Notification.objects.get_or_create(
            recipient=merchant,
            title='Demo customer order',
            defaults={
                'kind': 'order',
                'message': f'Order #{pending_order.id} contains products that need processing.',
                'link': '/shop/manage/orders/',
            },
        )

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('Merchant login: merchant.demo@example.com / DemoPass123')
        self.stdout.write('Customer login: customer.demo@example.com / DemoPass123')