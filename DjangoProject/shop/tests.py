from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from login.models import User

from .models import CartItem, Category, Notification, Order, OrderItem, Product, ProductImage


PNG_BYTES = (
	b'\x89PNG\r\n\x1a\n'
	b'\x00\x00\x00\rIHDR'
	b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
	b'\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef'
	b'\x00\x00\x00\x00IEND\xaeB`\x82'
)


class ShopFlowTests(TestCase):
	def setUp(self):
		self.customer = User.objects.create_user(
			username='customer1',
			email='customer@example.com',
			password='password123',
			role='customer',
		)
		self.merchant = User.objects.create_user(
			username='merchant1',
			email='merchant@example.com',
			password='password123',
			role='merchant',
		)
		self.category = Category.objects.create(name='Electronics')
		self.product = Product.objects.create(
			owner=self.merchant,
			name='Wireless Mouse',
			description='<p>Fast and lightweight.</p>',
			price='25.00',
			stock=10,
			category=self.category,
		)

	def test_product_catalog_page_loads(self):
		response = self.client.get(reverse('shop:product_list'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Wireless Mouse')

	def test_order_status_transition_creates_history(self):
		order = Order.objects.create(
			user=self.customer,
			total_amount='25.00',
			total_price='25.00',
			shipping_address='123 Example Street',
		)
		order.update_status('hold', changed_by=self.merchant)
		order.refresh_from_db()

		self.assertEqual(order.status, 'hold')
		self.assertIsNotNone(order.held_at)
		self.assertEqual(order.status_history.count(), 1)

	def test_customer_order_detail_page_loads(self):
		order = Order.objects.create(
			user=self.customer,
			total_amount='25.00',
			total_price='25.00',
			shipping_address='123 Example Street',
		)
		OrderItem.objects.create(
			order=order,
			product=self.product,
			quantity=1,
			unit_price='25.00',
			subtotal='25.00',
		)

		self.client.login(username='customer1', password='password123')
		response = self.client.get(reverse('shop:order_detail', args=[order.id]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Wireless Mouse')

	def test_checkout_creates_order_and_notifications(self):
		self.client.login(username='customer1', password='password123')
		CartItem.objects.create(user=self.customer, product=self.product, quantity=2)

		response = self.client.post(
			reverse('shop:checkout'),
			{'shipping_address': '123 Example Street'},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		order = Order.objects.get(user=self.customer)
		self.assertEqual(order.items.count(), 1)
		self.assertFalse(CartItem.objects.filter(user=self.customer).exists())
		self.assertEqual(Notification.objects.filter(recipient=self.customer, kind='order').count(), 1)
		self.assertEqual(Notification.objects.filter(recipient=self.merchant, kind='order').count(), 1)

	def test_order_detail_displays_translated_status_in_chinese(self):
		order = Order.objects.create(
			user=self.customer,
			total_amount='25.00',
			total_price='25.00',
			shipping_address='123 Example Street',
		)
		self.client.login(username='customer1', password='password123')
		self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'zh-hans'
		response = self.client.get(reverse('shop:order_detail', args=[order.id]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '待处理')

	def test_orders_api_localizes_datetime_for_active_language(self):
		order = Order.objects.create(
			user=self.customer,
			total_amount='25.00',
			total_price='25.00',
			shipping_address='123 Example Street',
		)

		self.client.login(username='customer1', password='password123')
		self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'zh-hans'
		response = self.client.get(reverse('shop:orders_api'))

		expected = date_format(timezone.localtime(order.created_at), format='DATETIME_FORMAT', use_l10n=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()[0]['order_date'], expected)

	def test_product_catalog_supports_sorting_and_pagination(self):
		for index in range(12):
			Product.objects.create(
				owner=self.merchant,
				name=f'Product {index:02d}',
				description='Extra product',
				price=str(10 + index),
				stock=5,
				category=self.category,
			)

		response = self.client.get(reverse('shop:product_list'), {'sort': 'price_asc', 'page': 2})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'page=1')
		self.assertContains(response, 'page=2')

	def test_merchant_orders_supports_sorting(self):
		other_order = Order.objects.create(
			user=self.customer,
			total_amount='55.00',
			total_price='55.00',
			shipping_address='Address A',
		)
		another_order = Order.objects.create(
			user=self.customer,
			total_amount='15.00',
			total_price='15.00',
			shipping_address='Address B',
		)
		for order, subtotal in ((other_order, '55.00'), (another_order, '15.00')):
			OrderItem.objects.create(
				order=order,
				product=self.product,
				quantity=1,
				unit_price=subtotal,
				subtotal=subtotal,
			)

		self.client.login(username='merchant1', password='password123')
		response = self.client.get(reverse('shop:merchant_orders'), {'sort': 'amount_desc'})

		self.assertEqual(response.status_code, 200)
		content = response.content.decode('utf-8')
		self.assertLess(content.find('$55.00'), content.find('$15.00'))

	def test_merchant_manage_accepts_multiple_gallery_images(self):
		self.client.login(username='merchant1', password='password123')
		cover = SimpleUploadedFile('cover.png', PNG_BYTES, content_type='image/png')
		gallery_one = SimpleUploadedFile('gallery-1.png', PNG_BYTES, content_type='image/png')
		gallery_two = SimpleUploadedFile('gallery-2.png', PNG_BYTES, content_type='image/png')

		response = self.client.post(
			reverse('shop:manage_product_new'),
			{
				'name': 'Desk Lamp',
				'category': str(self.category.id),
				'price': '49.90',
				'stock': '8',
				'status': 'active',
				'image': cover,
				'description': 'Warm light for reading corners.',
				'tags_text': 'home, lighting',
				'gallery_images': [gallery_one, gallery_two],
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		product = Product.objects.get(name='Desk Lamp')
		self.assertEqual(product.images.count(), 2)

	def test_manage_product_list_and_editor_are_separate_pages(self):
		self.client.login(username='merchant1', password='password123')

		list_response = self.client.get(reverse('shop:manage'))
		editor_response = self.client.get(reverse('shop:manage_product_new'))

		self.assertEqual(list_response.status_code, 200)
		self.assertEqual(editor_response.status_code, 200)
		self.assertContains(list_response, 'Current Products')
		self.assertNotContains(list_response, 'Save Product')
		self.assertContains(editor_response, 'Save Product')

	def test_manage_product_edit_supports_removing_cover_and_gallery_images(self):
		self.client.login(username='merchant1', password='password123')
		self.product.image = SimpleUploadedFile('existing-cover.png', PNG_BYTES, content_type='image/png')
		self.product.save(update_fields=['image'])
		gallery_one = ProductImage.objects.create(
			product=self.product,
			image=SimpleUploadedFile('existing-gallery-1.png', PNG_BYTES, content_type='image/png'),
		)
		ProductImage.objects.create(
			product=self.product,
			image=SimpleUploadedFile('existing-gallery-2.png', PNG_BYTES, content_type='image/png'),
		)

		response = self.client.post(
			reverse('shop:manage_product_edit', args=[self.product.id]),
			{
				'name': self.product.name,
				'category': str(self.category.id),
				'price': '25.00',
				'stock': '10',
				'status': 'active',
				'description': '<p>Fast and lightweight.</p>',
				'tags_text': '',
				'remove_cover_image': '1',
				'remove_gallery_images': [str(gallery_one.id)],
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.product.refresh_from_db()
		self.assertFalse(self.product.image)
		self.assertEqual(self.product.images.count(), 1)
		self.assertFalse(self.product.images.filter(id=gallery_one.id).exists())

	def test_login_and_register_placeholders_follow_language(self):
		self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
		login_response = self.client.get(reverse('login:login'))
		register_response = self.client.get(reverse('login:register'))

		self.assertContains(login_response, 'placeholder="Enter your email"')
		self.assertContains(register_response, 'placeholder="Enter your shipping address"')

		self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'zh-hans'
		login_response_zh = self.client.get(reverse('login:login'))
		register_response_zh = self.client.get(reverse('login:register'))

		self.assertContains(login_response_zh, 'placeholder="请输入你的邮箱"')
		self.assertContains(register_response_zh, 'placeholder="请输入你的收货地址"')

	def test_product_description_renders_rich_text_safely(self):
		self.client.login(username='merchant1', password='password123')
		response = self.client.post(
			reverse('shop:manage_product_edit', args=[self.product.id]),
			{
				'name': self.product.name,
				'category': str(self.category.id),
				'price': '25.00',
				'stock': '10',
				'status': 'active',
				'description': '<p><strong>Fast</strong> and light.</p><script>alert(1)</script>',
				'tags_text': '',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.product.refresh_from_db()
		self.assertEqual(self.product.description, '<p><strong>Fast</strong> and light.</p>')

		detail_response = self.client.get(reverse('shop:product_detail', args=[self.product.id]))
		self.assertContains(detail_response, '<strong>Fast</strong>', html=False)
		self.assertNotContains(detail_response, '<script>alert(1)</script>', html=False)

	def test_import_workspace_catalog_command_imports_products(self):
		call_command('import_workspace_catalog', owner_email=self.merchant.email)

		self.assertTrue(Product.objects.filter(owner=self.merchant, name='Apple iPhone 15 128GB').exists())
		imported_product = Product.objects.get(owner=self.merchant, name='Apple iPhone 15 128GB')
		self.assertEqual(imported_product.category.name, 'Electronics')
		self.assertGreaterEqual(imported_product.images.count(), 1)
