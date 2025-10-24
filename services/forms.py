from django import forms
from .models import ServiceOrder
from django.utils.text import slugify

class ServiceOrderForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = ['full_name', 'email', 'phone', 'additional_info']
        widgets = {
            'additional_info': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        # Pop dynamic_fields_data and required_docs from kwargs
        dynamic_fields_data = kwargs.pop('dynamic_fields', [])
        required_docs = kwargs.pop('required_docs', [])
        
        super().__init__(*args, **kwargs)

        # Add dynamic document fields
        for doc in required_docs:
            field_name = f'document_{slugify(doc.name)}'
            self.fields[field_name] = forms.FileField(
                label=doc.name,
                required=doc.is_mandatory,
                help_text=doc.description
            )
        
        for field in dynamic_fields_data:
            field_name = f'dynamic_field_{slugify(field.name)}'
            field_label = field.label
            field_type = field.field_type
            is_required = field.is_mandatory
            
            # Create form field based on the object's attributes
            if field_type == 'text':
                self.fields[field_name] = forms.CharField(label=field_label, required=is_required)
            elif field_type == 'textarea':
                self.fields[field_name] = forms.CharField(label=field_label, widget=forms.Textarea, required=is_required)
            # Add other field types (number, etc.) here

    class Meta:
        model = ServiceOrder
        fields = ['full_name', 'email', 'phone', 'additional_info']