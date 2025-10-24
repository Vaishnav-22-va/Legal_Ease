# partner/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Partner, PartnerPlan,Customer



class WalletTopUpForm(forms.Form):
    """
    A form for users to top up their wallet.
    """
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        label="Top-Up Amount"
    )

    

# partner/forms.py



# Get your custom user model
User = get_user_model()

class PartnerCreationForm(forms.ModelForm):
    """
    A custom form for the admin to create a new Partner and their associated User account.
    """
    # --- Fields for creating or finding the User ---
    email = forms.EmailField(
        required=True, 
        help_text="Enter the user's email. If the user already exists, they will be linked. Otherwise, a new user will be created."
    )
    password = forms.CharField(
        widget=forms.PasswordInput, 
        required=False,
        help_text="Required only if creating a new user. Leave blank if linking to an existing user."
    )
    full_name = forms.CharField(
        max_length=150, 
        required=True, 
        help_text="The user's full name (e.g., 'John Doe'). This will be split into first and last names."
    )
    phone = forms.CharField(
        max_length=15, 
        required=True,
        help_text="The user's contact phone number. Must be unique for new users."
    )

    # --- Field for the initial subscription ---
    subscription_plan = forms.ModelChoiceField(
        queryset=PartnerPlan.objects.all(),
        required=False, # Make it optional
        help_text="Optional: Select an initial subscription plan for the partner."
    )

    class Meta:
        model = Partner
        # --- Fields from the Partner model itself ---
        fields = ('business_name', 'address', 'city', 'state', 'pincode')

    def clean(self):
        """
        Provides critical validation before attempting to save.
        """
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")

class CustomerEditForm(forms.ModelForm):
    """
    A form for editing an existing customer's details.
    """
    class Meta:
        model = Customer
        fields = ['full_name', 'email', 'phone', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

        # This logic applies ONLY when
    # You can add more fields here if needed
    # For example, a field for payment method:
    # payment_method = forms.ChoiceField(choices=[('credit_card', 'Credit Card'), ('upi', 'UPI')])