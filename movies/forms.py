from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    
    email = forms.EmailField(required=True, help_text='Required. A valid email address.')
    mobile_no = forms.CharField(required=False, max_length=15, help_text='Optional.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        # Add placeholders for a better UI
        self.fields['username'].widget.attrs.update({'placeholder': 'Username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email Address'})
        self.fields['mobile_no'].widget.attrs.update({'placeholder': 'Mobile Number (Optional)'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm Password'})


class CustomAuthenticationForm(AuthenticationForm):
    """
    A custom form for user login to ensure consistent styling and placeholders.
    """
    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Password'})

# --- ADD THESE NEW FORMS ---

class UserUpdateForm(forms.ModelForm):
    """
    A form for updating the user's basic information (username and email).
    """
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        # Add placeholders to match the site's style
        self.fields['username'].widget.attrs.update({'placeholder': 'Username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email Address'})


class ProfileUpdateForm(forms.ModelForm):
    """
    A form for updating the user's profile, specifically for the profile picture.
    """
    class Meta:
        model = Profile
        fields = ['profile_pic']

