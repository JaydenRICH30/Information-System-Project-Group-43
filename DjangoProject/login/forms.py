from django import forms
from django.contrib.auth.forms import get_user_model
from django.utils.translation import gettext as _
from .models import User

User = get_user_model()


def _apply_auth_field_copy(field, *, placeholder=None, required=None, invalid=None, max_length=None, min_length=None):
    if placeholder is not None:
        field.widget.attrs['placeholder'] = placeholder
    if required is not None:
        field.error_messages['required'] = required
    if invalid is not None:
        field.error_messages['invalid'] = invalid
    if max_length is not None:
        field.error_messages['max_length'] = max_length
    if min_length is not None:
        field.error_messages['min_length'] = min_length

class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=20,
        min_length=4,
        widget=forms.TextInput(attrs={'class': 'input'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input'}),
    )
    password = forms.CharField(
        max_length=20,
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'input'}),
    )
    role = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'input'}),
    )
    address = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.Textarea(attrs={'class': 'textarea', 'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_auth_field_copy(
            self.fields['username'],
            placeholder=_('Enter your full name'),
            required=_('Please enter a username'),
            max_length=_('username cannot be more than 20 characters'),
            min_length=_('username cannot be less than 4 characters'),
        )
        _apply_auth_field_copy(
            self.fields['email'],
            placeholder=_('Enter your email'),
            required=_('Please enter a valid email address'),
            invalid=_('Please enter a valid email address'),
        )
        _apply_auth_field_copy(
            self.fields['password'],
            placeholder=_('Use at least 8 characters'),
            required=_('Please enter a password'),
        )
        self.fields['role'].choices = [('customer', _('Customer')), ('merchant', _('Merchant'))]
        _apply_auth_field_copy(
            self.fields['address'],
            placeholder=_('Enter your shipping address'),
            required=_('Please enter a valid address'),
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        exists = User.objects.filter(email=email).exists()
        if exists:
            raise forms.ValidationError(_("Email already exists"))
        return email

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'input'}),
    )
    password = forms.CharField(
        max_length=20,
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'input'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_auth_field_copy(
            self.fields['email'],
            placeholder=_('Enter your email'),
            required=_('Please enter a valid email address'),
            invalid=_('Please enter a valid email address'),
        )
        _apply_auth_field_copy(
            self.fields['password'],
            placeholder=_('Enter your password'),
            required=_('Please enter a password'),
        )


class AccountProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'address']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input', 'placeholder': _('Enter your full name')}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': _('Enter your email')}),
            'address': forms.Textarea(attrs={'class': 'textarea', 'rows': 3, 'placeholder': _('Enter your shipping address')}),
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = _('Enter your full name')
        self.fields['email'].widget.attrs['placeholder'] = _('Enter your email')
        self.fields['address'].widget.attrs['placeholder'] = _('Enter your shipping address')

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email=email)
        if self.user_instance is not None:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Email already exists'))
        return email


class PasswordUpdateForm(forms.Form):
    current_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': _('Enter your password')}),
    )
    new_password = forms.CharField(
        label=_('New Password'),
        min_length=8,
        max_length=20,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': _('Use at least 8 characters')}),
    )
    confirm_password = forms.CharField(
        label=_('Confirm Password'),
        min_length=8,
        max_length=20,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': _('Enter your password')}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['current_password'].widget.attrs['placeholder'] = _('Enter your password')
        self.fields['new_password'].widget.attrs['placeholder'] = _('Use at least 8 characters')
        self.fields['confirm_password'].widget.attrs['placeholder'] = _('Enter your password')

    def clean_current_password(self):
        current_password = self.cleaned_data['current_password']
        if not self.user.check_password(current_password):
            raise forms.ValidationError(_('Current password is incorrect'))
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError(_('New passwords do not match'))
        return cleaned_data