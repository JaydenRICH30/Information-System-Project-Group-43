from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render, reverse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from shop.models import Notification, Order, Product

from .forms import AccountProfileForm, LoginForm, PasswordUpdateForm, RegisterForm, User

@require_http_methods(['GET','POST'])
def unlogin(request):
    if request.method == 'GET':
        return render(request, 'Login.html', {'form': LoginForm()})
    else:
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = User.objects.filter(email=email).first()
            if not user or not user.check_password(password):
                messages.error(request, _('The email or password is incorrect. Please try again.'))
                return render(request, 'Login.html', {'form': form}, status=400)
            else:
                login(request, user)
                return redirect(reverse('login:index'))
        else:
            messages.error(request, _('Please correct the highlighted fields before continuing.'))
            return render(request, 'Login.html', context={'form': form}, status=400)

@require_http_methods(['GET', 'POST'])
def register(request):
    if request.method == 'GET':
        return render(request, 'Register.html', {'form': RegisterForm()})
    else:
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            username = form.cleaned_data.get('username')
            role = form.cleaned_data.get('role')
            address = form.cleaned_data.get('address')
            User.objects.create_user(username=username, email=email, password=password, role=role, address=address)
            messages.success(request, _('Registration successful. You can now log in.'))
            return redirect(reverse('login:login'))
        else:
            messages.error(request, _('Registration failed. Please review the form and fix the errors.'))
            return render(request, 'Register.html', context={'form': form}, status=400)


def index(request):
    if not request.user.is_authenticated:
        return redirect(reverse('login:login'))
    if request.user.role == 'customer' :
        featured_queryset = Product.objects.filter(status='active').order_by('-created_at')
        featured_paginator = Paginator(featured_queryset, 8)
        featured_page_obj = featured_paginator.get_page(request.GET.get('products_page'))

        if request.GET.get('partial') == 'featured-products':
            html = render_to_string(
                'includes/featured_product_cards.html',
                {'featured_products': featured_page_obj},
                request=request,
            )
            return JsonResponse(
                {
                    'html': html,
                    'has_next': featured_page_obj.has_next(),
                    'next_page': featured_page_obj.next_page_number() if featured_page_obj.has_next() else None,
                    'current_page': featured_page_obj.number,
                }
            )

        return render(
            request,
            'Index.html',
            {
                'featured_products': featured_page_obj,
                'featured_page_obj': featured_page_obj,
                'unread_notifications': Notification.objects.filter(recipient=request.user, is_read=False).count(),
                'latest_orders': Order.objects.filter(user=request.user).order_by('-created_at')[:3],
            },
        )
    elif request.user.role == 'merchant' :
        merchant_products = Product.objects.filter(owner=request.user)
        return render(
            request,
            'Mindex.html',
            {
                'merchant_products': merchant_products.order_by('-created_at')[:8],
                'unread_notifications': Notification.objects.filter(recipient=request.user, is_read=False).count(),
                'open_orders_count': Order.objects.filter(items__product__owner=request.user).exclude(status__in=['delivered', 'cancelled']).distinct().count(),
                'active_product_count': merchant_products.filter(status='active').count(),
            },
        )
    else:
        return redirect(reverse('login:login'))

@login_required
def account(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'profile':
            profile_form = AccountProfileForm(request.POST, instance=request.user, prefix='profile')
            password_form = PasswordUpdateForm(user=request.user, prefix='password')
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _('Account details updated.'))
                return redirect(reverse('login:account'))
            messages.error(request, _('Please correct the account form errors.'))
        elif action == 'password':
            profile_form = AccountProfileForm(instance=request.user, prefix='profile')
            password_form = PasswordUpdateForm(request.POST, user=request.user, prefix='password')
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['new_password'])
                request.user.save(update_fields=['password'])
                messages.success(request, _('Password updated. Please log in again.'))
                logout(request)
                return redirect(reverse('login:login'))
            messages.error(request, _('Please correct the password form errors.'))
        else:
            return redirect(reverse('login:account'))
    else:
        profile_form = AccountProfileForm(instance=request.user, prefix='profile')
        password_form = PasswordUpdateForm(user=request.user, prefix='password')

    if request.user.role == 'merchant':
        stats = {
            'primary': Product.objects.filter(owner=request.user).count(),
            'secondary': Order.objects.filter(items__product__owner=request.user).distinct().count(),
            'primary_label': _('Products'),
            'secondary_label': _('Orders'),
        }
    else:
        stats = {
            'primary': Order.objects.filter(user=request.user).count(),
            'secondary': Notification.objects.filter(recipient=request.user, is_read=False).count(),
            'primary_label': _('Orders'),
            'secondary_label': _('Unread Notifications'),
        }

    return render(request,'MyAccount.html', {
        'user':request.user,
        'unread_notifications': Notification.objects.filter(recipient=request.user, is_read=False).count(),
        'profile_form': profile_form,
        'password_form': password_form,
        'stats': stats,
    })


@require_GET
def current_user_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False, 'role': '', 'email': ''})
    return JsonResponse(
        {
            'authenticated': True,
            'role': request.user.role,
            'email': request.user.email,
            'username': request.user.username,
        }
    )


@require_GET
def user_status_api(request):
    return JsonResponse(
        {
            'logged_in': request.user.is_authenticated,
            'role': getattr(request.user, 'role', ''),
        }
    )


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse('login:login'))