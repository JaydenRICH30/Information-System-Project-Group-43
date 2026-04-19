from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import CheckoutForm, ProductForm, ReviewForm
from .models import CartItem, Category, Notification, Order, OrderItem, Product, ProductImage, Review, Tag


def _is_merchant(user):
    return user.is_authenticated and getattr(user, 'role', '') == 'merchant'


def _format_local_datetime(value):
    if not value:
        return ''
    return date_format(timezone.localtime(value), format='DATETIME_FORMAT', use_l10n=True)


def _serialize_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'price': str(product.price),
        'stock': product.stock,
        'status': product.status,
        'description': product.description,
        'desc': product.description,
        'image': product.primary_image_url,
        'category': product.category.name if product.category else '',
        'category_id': product.category_id,
        'tags': list(product.tags.values_list('name', flat=True)),
        'average_rating': float(product.average_rating),
        'review_count': product.reviews.count(),
    }


def _serialize_order(order):
    return {
        'id': order.id,
        'order_number': order.id,
        'order_date': _format_local_datetime(order.created_at),
        'total_amount': str(order.total_amount),
        'status': order.status,
        'status_updated_at': _format_local_datetime(order.status_updated_at),
    }


def _serialize_notification(notification):
    return {
        'id': notification.id,
        'type': notification.kind,
        'title': notification.title,
        'message': notification.message,
        'read': notification.is_read,
        'created_at': _format_local_datetime(notification.created_at),
        'link': notification.link,
    }


def _create_notification(recipient, kind, title, message, link=''):
    Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        message=message,
        link=link,
    )


def _sync_product_tags(product, raw_tags):
    product.tags.clear()
    names = [name.strip() for name in raw_tags.split(',') if name.strip()]
    for name in names:
        tag, _ = Tag.objects.get_or_create(name=name)
        product.tags.add(tag)


def _save_gallery_images(product, files):
    for image in files:
        ProductImage.objects.create(product=product, image=image)


def _delete_gallery_images(product, image_ids):
    if not image_ids:
        return

    images = product.images.filter(pk__in=image_ids)
    for image in images:
        image.image.delete(save=False)
        image.delete()


def _customer_has_purchased(user, product):
    return OrderItem.objects.filter(
        order__user=user,
        order__status='delivered',
        product=product,
    ).exists()


def _build_querystring(request, exclude=None):
    params = request.GET.copy()
    for key in (exclude or []):
        params.pop(key, None)
    return params.urlencode()


@require_http_methods(['GET', 'POST'])
@csrf_exempt
def product_api(request, pk=None):
    if request.method == 'GET':
        if pk is not None:
            product = get_object_or_404(
                Product.objects.prefetch_related('tags', 'reviews', 'images').select_related('category'),
                pk=pk,
            )
            data = _serialize_product(product)
            data['images'] = [image.image.url for image in product.images.all()]
            return JsonResponse(data)

        products = Product.objects.filter(status='active').select_related('category').prefetch_related('tags', 'reviews')
        query = request.GET.get('q', '').strip()
        category_id = request.GET.get('category')
        tag_name = request.GET.get('tag', '').strip()
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')

        if _is_merchant(request.user):
            products = Product.objects.filter(owner=request.user).select_related('category').prefetch_related('tags', 'reviews')
        if query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(category__name__icontains=query)
            ).distinct()
        if category_id:
            products = products.filter(category_id=category_id)
        if tag_name:
            products = products.filter(tags__name__iexact=tag_name)
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)

        return JsonResponse([_serialize_product(product) for product in products], safe=False)

    if not _is_merchant(request.user):
        return JsonResponse({'status': 'error', 'message': _('Merchant access required')}, status=403)

    instance = get_object_or_404(Product, pk=pk, owner=request.user) if pk else None
    form = ProductForm(request.POST, request.FILES, instance=instance)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    product = form.save(commit=False)
    product.owner = request.user
    remove_cover_image = request.POST.get('remove_cover_image') == '1'
    remove_gallery_ids = request.POST.getlist('remove_gallery_images')
    if remove_cover_image and not request.FILES.get('image') and instance and instance.image:
        instance.image.delete(save=False)
        product.image = None
    product.save()
    form.save_m2m()
    _sync_product_tags(product, form.cleaned_data.get('tags_text', ''))
    _delete_gallery_images(product, remove_gallery_ids)
    gallery_images = form.cleaned_data.get('gallery_images', [])
    if gallery_images:
        _save_gallery_images(product, gallery_images)
    return JsonResponse({'status': 'success', 'id': product.id})


@require_GET
def product_list(request):
    products = Product.objects.filter(status='active').select_related('category', 'owner').prefetch_related('tags', 'reviews')
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    tag_name = request.GET.get('tag', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'newest').strip() or 'newest'

    sort_options = {
        'newest': _("Newest"),
        'price_asc': _("Price: Low to High"),
        'price_desc': _("Price: High to Low"),
        'name_asc': _("Name: A to Z"),
        'rating_desc': _("Rating: High to Low"),
    }
    sort_map = {
        'newest': ('-created_at', '-id'),
        'price_asc': ('price', 'name'),
        'price_desc': ('-price', 'name'),
        'name_asc': ('name',),
        'rating_desc': ('-created_at', '-id'),
    }

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(category__name__icontains=query)
        ).distinct()
    if category_id:
        products = products.filter(category_id=category_id)
    if tag_name:
        products = products.filter(tags__name__iexact=tag_name)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    products = products.order_by(*sort_map.get(sort, sort_map['newest']))
    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'result_count': paginator.count,
        'categories': Category.objects.annotate(product_count=Count('product')).order_by('name'),
        'popular_tags': Tag.objects.annotate(product_count=Count('product')).order_by('-product_count', 'name')[:12],
        'sort_options': sort_options,
        'filters': {
            'q': query,
            'category': category_id,
            'tag': tag_name,
            'min_price': min_price,
            'max_price': max_price,
            'sort': sort,
        },
        'pagination_query': _build_querystring(request, exclude=['page']),
    }
    return render(request, 'ProductList.html', context)


@require_http_methods(['GET', 'POST'])
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category', 'owner').prefetch_related('tags', 'images', 'reviews__user'),
        pk=pk,
        status='active',
    )

    can_review = False
    existing_review = None
    if request.user.is_authenticated and request.user.role == 'customer':
        can_review = _customer_has_purchased(request.user, product)
        existing_review = Review.objects.filter(product=product, user=request.user).first()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login:login')
        if request.user.role != 'customer' or not can_review:
            messages.error(request, _('Only customers who completed a purchase can review this product.'))
            return redirect('shop:product_detail', pk=pk)

        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            if product.owner and product.owner != request.user:
                _create_notification(
                    product.owner,
                    'review',
                    _('New review for %(product)s') % {'product': product.name},
                    _('%(user)s left a %(rating)s-star review.') % {'user': request.user.username, 'rating': review.rating},
                    reverse('shop:product_detail', args=[product.id]),
                )
            messages.success(request, _('Your review was saved.'))
            return redirect('shop:product_detail', pk=pk)
        messages.error(request, _('Please correct the review form.'))
    else:
        form = ReviewForm(instance=existing_review)

    related_products = Product.objects.filter(status='active').exclude(pk=product.pk)
    if product.category_id:
        related_products = related_products.filter(category=product.category)
    tag_ids = list(product.tags.values_list('id', flat=True))
    if tag_ids:
        related_products = related_products.filter(tags__in=tag_ids).distinct()
    related_products = related_products[:4]

    context = {
        'product': product,
        'images': product.images.all(),
        'reviews': product.reviews.select_related('user').all(),
        'review_form': form,
        'can_review': can_review,
        'existing_review': existing_review,
        'related_products': related_products,
    }
    return render(request, 'ProductDetail.html', context)


@login_required
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, status='active')
    if request.user.role != 'customer':
        messages.error(request, _('Only customer accounts can add products to cart.'))
        return redirect('shop:product_detail', pk=pk)

    quantity = max(int(request.POST.get('quantity', 1)), 1)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    cart_item.quantity = cart_item.quantity + quantity if not created else quantity
    cart_item.save()
    messages.success(request, _('%(product)s was added to your cart.') % {'product': product.name})
    return redirect('shop:cart')


@login_required
def cart(request):
    if request.user.role != 'customer':
        return redirect('login:index')

    items = list(
        CartItem.objects.filter(user=request.user)
        .select_related('product', 'product__category')
        .order_by('id')
    )
    total = sum(item.product.price * item.quantity for item in items)
    checkout_form = CheckoutForm(initial={'shipping_address': request.user.address or ''})
    return render(
        request,
        'MyCart.html',
        {
            'cart_items': items,
            'cart_total': total,
            'checkout_form': checkout_form,
        },
    )


@login_required
@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    quantity = max(int(request.POST.get('quantity', 1)), 1)
    if quantity > item.product.stock:
        messages.error(request, _('Quantity exceeds available stock.'))
    else:
        item.quantity = quantity
        item.save(update_fields=['quantity'])
        messages.success(request, _('Cart updated.'))
    return redirect('shop:cart')


@login_required
@require_POST
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    item.delete()
    messages.success(request, _('Item removed from cart.'))
    return redirect('shop:cart')


@login_required
@require_POST
def checkout(request):
    if request.user.role != 'customer':
        return redirect('login:index')

    items = list(CartItem.objects.filter(user=request.user).select_related('product', 'product__owner'))
    if not items:
        messages.error(request, _('Your cart is empty.'))
        return redirect('shop:cart')

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, _('Please provide a valid shipping address.'))
        return redirect('shop:cart')

    for item in items:
        if item.quantity > item.product.stock:
            messages.error(request, _('%(product)s does not have enough stock.') % {'product': item.product.name})
            return redirect('shop:cart')

    total = sum(item.product.price * item.quantity for item in items)
    order = Order.objects.create(
        user=request.user,
        total_amount=total,
        total_price=total,
        shipping_address=form.cleaned_data['shipping_address'],
    )

    vendors = set()
    for item in items:
        product = item.product
        product.stock -= item.quantity
        product.save(update_fields=['stock'])
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item.quantity,
            unit_price=product.price,
            subtotal=product.price * item.quantity,
        )
        if product.owner_id:
            vendors.add(product.owner)

    CartItem.objects.filter(user=request.user).delete()

    for vendor in vendors:
        _create_notification(
            vendor,
            'order',
            _('New order #%(order_id)s') % {'order_id': order.id},
            _('A new order contains one or more of your products.'),
            reverse('shop:merchant_orders'),
        )

    _create_notification(
        request.user,
        'order',
        _('Order #%(order_id)s created') % {'order_id': order.id},
        _('Your order is pending and waiting for merchant processing.'),
        reverse('shop:order'),
    )
    messages.success(request, _('Checkout completed. Order #%(order_id)s has been created.') % {'order_id': order.id})
    return redirect('shop:order')


@login_required
def order(request):
    if request.user.role != 'customer':
        return redirect('login:index')

    orders = Order.objects.filter(user=request.user).prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.select_related('product')),
        'status_history',
    )
    return render(request, 'MyOrders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    if request.user.role != 'customer':
        return redirect('login:index')

    order = get_object_or_404(
        Order.objects.filter(user=request.user).prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product')),
            'status_history',
        ),
        pk=order_id,
    )
    return render(request, 'CustomerOrderDetail.html', {'order': order})


@login_required
def manage(request):
    if not _is_merchant(request.user):
        return redirect('login:index')

    products = Product.objects.filter(owner=request.user).select_related('category').prefetch_related('tags', 'images')
    sort = request.GET.get('sort', 'updated_desc').strip() or 'updated_desc'
    sort_options = {
        'updated_desc': _("Recently Updated"),
        'price_asc': _("Price: Low to High"),
        'price_desc': _("Price: High to Low"),
        'stock_desc': _("Stock: High to Low"),
        'name_asc': _("Name: A to Z"),
    }
    sort_map = {
        'updated_desc': ('-updated_at', '-id'),
        'price_asc': ('price', 'name'),
        'price_desc': ('-price', 'name'),
        'stock_desc': ('-stock', 'name'),
        'name_asc': ('name',),
    }
    products = products.order_by(*sort_map.get(sort, sort_map['updated_desc']))
    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'ProductManagement.html',
        {
            'products': page_obj,
            'page_obj': page_obj,
            'sort': sort,
            'sort_options': sort_options,
            'pagination_query': _build_querystring(request, exclude=['page']),
        },
    )


@login_required
def manage_product_editor(request, pk=None):
    if not _is_merchant(request.user):
        return redirect('login:index')

    instance = get_object_or_404(Product, pk=pk, owner=request.user) if pk else None
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            remove_cover_image = request.POST.get('remove_cover_image') == '1'
            remove_gallery_ids = request.POST.getlist('remove_gallery_images')
            if remove_cover_image and not request.FILES.get('image') and instance and instance.image:
                instance.image.delete(save=False)
                product.image = None
            product.save()
            form.save_m2m()
            _sync_product_tags(product, form.cleaned_data.get('tags_text', ''))
            _delete_gallery_images(product, remove_gallery_ids)
            gallery_images = form.cleaned_data.get('gallery_images', [])
            if gallery_images:
                _save_gallery_images(product, gallery_images)
            messages.success(request, _('Product saved.'))
            return redirect('shop:manage_product_edit', pk=product.id)
        messages.error(request, _('Please correct the product form.'))
    else:
        form = ProductForm(instance=instance)

    return render(
        request,
        'ProductEditor.html',
        {
            'form': form,
            'edit_product': instance,
        },
    )


@login_required
@require_POST
def toggle_product_status(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    next_status = request.POST.get('status')
    if next_status not in {'active', 'draft', 'archived'}:
        return HttpResponseBadRequest(_('Invalid status'))
    product.status = next_status
    product.save(update_fields=['status'])
    messages.success(request, _('Product status updated.'))
    return redirect('shop:manage')


@login_required
def merchant_orders(request):
    if not _is_merchant(request.user):
        return redirect('login:index')

    orders = (
        Order.objects.filter(items__product__owner=request.user)
        .distinct()
        .select_related('user')
        .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('product')))
    )
    status_filter = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'latest').strip() or 'latest'
    sort_options = {
        'latest': _("Latest First"),
        'oldest': _("Oldest First"),
        'amount_desc': _("Amount: High to Low"),
        'amount_asc': _("Amount: Low to High"),
        'status_asc': _("Status"),
    }
    if status_filter:
        orders = orders.filter(status=status_filter)
    if search:
        search_filter = Q(user__username__icontains=search) | Q(user__email__icontains=search)
        if search.isdigit():
            search_filter = search_filter | Q(pk=int(search))
        orders = orders.filter(search_filter)

    sort_map = {
        'latest': ('-created_at', '-id'),
        'oldest': ('created_at', 'id'),
        'amount_desc': ('-total_amount', '-created_at'),
        'amount_asc': ('total_amount', '-created_at'),
        'status_asc': ('status', '-created_at'),
    }
    orders = orders.order_by(*sort_map.get(sort, sort_map['latest']))
    paginator = Paginator(orders, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'OrdersManagement.html',
        {
            'orders': page_obj,
            'page_obj': page_obj,
            'status_filter': status_filter,
            'search': search,
            'sort': sort,
            'sort_options': sort_options,
            'status_choices': Order.STATUS_CHOICES,
            'pagination_query': _build_querystring(request, exclude=['page']),
        },
    )


@login_required
@require_POST
def update_order_status(request, order_id):
    if not _is_merchant(request.user):
        return redirect('login:index')

    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=order_id)
    if not order.items.filter(product__owner=request.user).exists():
        return HttpResponseBadRequest(_('Order does not belong to this merchant'))

    next_status = request.POST.get('status')
    try:
        order.update_status(next_status, changed_by=request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('shop:merchant_orders')

    _create_notification(
        order.user,
        'order',
        _('Order #%(order_id)s updated') % {'order_id': order.id},
        _('Your order status changed to %(status)s.') % {'status': order.get_status_display()},
        reverse('shop:order'),
    )
    messages.success(request, _('Order status updated.'))
    return redirect('shop:merchant_orders')


@login_required
def notifications(request):
    user_notifications = request.user.notifications.all()
    template_name = 'MNotification.html' if _is_merchant(request.user) else 'Notification.html'
    return render(request, template_name, {'notifications': user_notifications})


@login_required
@require_POST
def notification_action(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    action = request.POST.get('action')
    if action == 'read':
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    elif action == 'delete':
        notification.delete()
    else:
        return HttpResponseBadRequest(_('Invalid action'))
    return redirect('shop:notifications')


@login_required
@require_GET
def cart_api(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')
    data = [
        {
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name,
            'price': float(item.product.price),
            'quantity': item.quantity,
            'image': item.product.primary_image_url,
        }
        for item in items
    ]
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def orders_api(request):
    orders = Order.objects.filter(user=request.user)
    return JsonResponse([_serialize_order(order) for order in orders], safe=False)


@login_required
@require_GET
def review_api(request, pk):
    product = get_object_or_404(Product, pk=pk)
    reviews = product.reviews.select_related('user')
    data = [
        {
            'user_name': review.user.username,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': _format_local_datetime(review.created_at),
        }
        for review in reviews
    ]
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def notifications_api(request):
    return JsonResponse([_serialize_notification(item) for item in request.user.notifications.all()], safe=False)