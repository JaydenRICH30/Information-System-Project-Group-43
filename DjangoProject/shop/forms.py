import re

from django import forms
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, Review


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def clean(self, data, initial=None):
        if not data:
            return []

        items = data if isinstance(data, (list, tuple)) else [data]
        cleaned_items = []
        for item in items:
            cleaned_items.append(super().clean(item, initial))
        return cleaned_items


SAFE_RICH_TEXT_TAGS = {'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a'}
SAFE_RICH_TEXT_ATTRIBUTES = {'a': {'href', 'target', 'rel'}}
SAFE_URL_PREFIXES = ('http://', 'https://', 'mailto:', '#', '/')


def sanitize_rich_text(value):
    value = (value or '').strip()
    if not value:
        return ''

    value = re.sub(r'(?is)<script.*?>.*?</script>', '', value)
    value = re.sub(r'(?is)<style.*?>.*?</style>', '', value)

    token_pattern = re.compile(r'(?is)<(/?)([a-z0-9]+)([^>]*)>')
    attribute_pattern = re.compile(r'([a-zA-Z_:][\w:.-]*)\s*=\s*(["\'])(.*?)\2', re.DOTALL)
    result = []
    last_index = 0

    for match in token_pattern.finditer(value):
        result.append(value[last_index:match.start()])
        slash, tag_name, attrs = match.groups()
        tag_name = tag_name.lower()
        if tag_name in SAFE_RICH_TEXT_TAGS:
            if slash:
                result.append(f'</{tag_name}>')
            elif tag_name == 'br':
                result.append('<br>')
            else:
                cleaned_attrs = []
                allowed_attrs = SAFE_RICH_TEXT_ATTRIBUTES.get(tag_name, set())
                for attr_name, _, attr_value in attribute_pattern.findall(attrs):
                    attr_name = attr_name.lower()
                    if attr_name not in allowed_attrs:
                        continue
                    attr_value = attr_value.strip()
                    if attr_name == 'href' and attr_value and not attr_value.startswith(SAFE_URL_PREFIXES):
                        continue
                    if attr_name in {'target', 'rel'} and attr_value:
                        cleaned_attrs.append(f'{attr_name}="{attr_value}"')
                    elif attr_name == 'href' and attr_value:
                        cleaned_attrs.append(f'{attr_name}="{attr_value}"')
                attr_suffix = f' {" ".join(cleaned_attrs)}' if cleaned_attrs else ''
                result.append(f'<{tag_name}{attr_suffix}>')
        last_index = match.end()

    result.append(value[last_index:])
    sanitized = ''.join(result)
    sanitized = re.sub(r'(?i)on[a-z]+\s*=\s*(["\']).*?\1', '', sanitized)
    sanitized = re.sub(r'(?i)javascript:', '', sanitized)
    return sanitized.strip()


class ProductForm(forms.ModelForm):
    tags_text = forms.CharField(
        required=False,
        label=_('Tags'),
        help_text=_('Comma separated tags'),
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': _('Example: eco, gift, home')}),
    )
    gallery_images = MultipleImageField(
        required=False,
        label=_('Gallery Images'),
        help_text=_('You can select multiple images at once.'),
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': 'image/*', 'class': 'input'}),
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'stock', 'status', 'image', 'description']
        labels = {
            'name': _('Product Name'),
            'category': _('Category'),
            'price': _('Price'),
            'stock': _('Stock'),
            'status': _('Status'),
            'image': _('Cover Image'),
            'description': _('Product Description'),
        }
        help_texts = {
            'description': _('Use rich text to format highlights, lists, and links. The product detail page will show the same layout.'),
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': _('Name your product')}),
            'category': forms.Select(attrs={'class': 'select'}),
            'price': forms.NumberInput(attrs={'class': 'input', 'step': '0.01', 'placeholder': '99.00'}),
            'stock': forms.NumberInput(attrs={'class': 'input', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'input', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'rows': 10, 'class': 'textarea rich-text-source', 'placeholder': _('Write the story, highlights, materials, and usage scenarios with rich text')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].required = False
        self.fields['category'].empty_label = _('Select a category')
        if self.instance.pk:
            self.fields['tags_text'].initial = ', '.join(
                self.instance.tags.values_list('name', flat=True)
            )

    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        cleaned = sanitize_rich_text(description)
        if strip_tags(cleaned).strip() == '':
            raise forms.ValidationError(_('Please add a product description.'))
        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        labels = {
            'rating': _('Rating'),
            'comment': _('Comment'),
        }
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'input', 'min': '1', 'max': '5'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'textarea', 'placeholder': _('Share your experience')}),
        }


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        max_length=255,
        label=_('Shipping Address'),
        widget=forms.Textarea(attrs={'class': 'textarea', 'rows': 3, 'placeholder': _('Enter your shipping address')}),
    )