from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Notification, Order, Product

from .models import User


class AccountViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='account_user',
			email='account@example.com',
			password='password123',
			role='customer',
			address='Old Address',
		)

	def test_profile_update(self):
		self.client.login(username='account_user', password='password123')
		response = self.client.post(
			reverse('login:account'),
			{
				'action': 'profile',
				'profile-username': 'account_user',
				'profile-email': 'updated@example.com',
				'profile-address': 'New Address',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.user.refresh_from_db()
		self.assertEqual(self.user.email, 'updated@example.com')
		self.assertEqual(self.user.address, 'New Address')

	def test_login_invalid_credentials_shows_friendly_message(self):
		response = self.client.post(
			reverse('login:login'),
			{'email': 'account@example.com', 'password': 'wrongpass'},
		)

		self.assertEqual(response.status_code, 400)
		self.assertContains(response, 'The email or password is incorrect. Please try again.', status_code=400)

	def test_register_short_password_shows_form_error(self):
		response = self.client.post(
			reverse('login:register'),
			{
				'username': 'newuser',
				'email': 'newuser@example.com',
				'password': '123456',
				'role': 'customer',
				'address': 'Some address',
			},
		)

		self.assertEqual(response.status_code, 400)
		self.assertContains(response, 'Registration failed. Please review the form and fix the errors.', status_code=400)

	def test_login_page_renders_in_chinese(self):
		self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'zh-hans'
		response = self.client.get(reverse('login:login'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '登录')

	def test_customer_dashboard_paginates_featured_products(self):
		category = Category.objects.create(name='Dashboard')
		for index in range(10):
			Product.objects.create(
				name=f'Homepage Product {index}',
				description='For dashboard pagination',
				price='12.00',
				stock=5,
				status='active',
				category=category,
			)

		self.client.login(username='account_user', password='password123')
		response = self.client.get(reverse('login:index'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Homepage Product 9')
		self.assertNotContains(response, 'Homepage Product 0')
		self.assertContains(response, '?products_page=2')

	def test_customer_dashboard_supports_partial_featured_product_loading(self):
		category = Category.objects.create(name='Async Dashboard')
		for index in range(9):
			Product.objects.create(
				name=f'Async Product {index}',
				description='For infinite loading',
				price='18.00',
				stock=7,
				status='active',
				category=category,
			)

		self.client.login(username='account_user', password='password123')
		response = self.client.get(reverse('login:index'), {'products_page': 2, 'partial': 'featured-products'})

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn('Async Product 0', payload['html'])
		self.assertFalse(payload['has_next'])
