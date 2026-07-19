# forms.py - COMPLETE ENHANCED VERSION
# Copy and paste this entire file

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import re
from .models import Profile, SafeMeetRequest, BlockReport

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition bg-gray-50',
            'placeholder': 'Enter your email'
        })
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition bg-gray-50',
        'placeholder': 'Enter your username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition bg-gray-50',
        'placeholder': 'Enter your password'
    }))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['display_name', 'gender', 'birth_date', 'city', 'country', 'bio']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class EnhancedProfileForm(forms.ModelForm):
    """Enhanced profile form with interest tags and additional fields"""
    
    interests_input = forms.CharField(
        max_length=300, 
        required=False,
        help_text="Enter interests separated by commas (e.g., hiking, coffee, movies, travel)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': 'Add interests (e.g., hiking, coffee, music)',
            'data-role': 'tags-input'
        })
    )
    
    profile_pic = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    class Meta:
        model = Profile
        fields = [
            'display_name', 'gender', 'birth_date', 'city', 'country', 
            'bio', 'is_available', 'profile_pic', 'show_online_status',
            'show_distance', 'incognito_mode'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
                'placeholder': 'Write something about yourself...',
                'maxlength': 500
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
                'placeholder': 'Your display name'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
                'placeholder': 'Country'
            }),
        }
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = timezone.now().date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                raise forms.ValidationError("You must be at least 18 years old to use this app.")
            if age > 120:
                raise forms.ValidationError("Please enter a valid birth date.")
        return birth_date
    
    def clean_display_name(self):
        display_name = self.cleaned_data.get('display_name')
        if display_name:
            # Check for inappropriate content (basic filter)
            inappropriate_words = ['admin', 'moderator', 'support', 'djao']
            if display_name.lower() in inappropriate_words:
                raise forms.ValidationError("This display name is not allowed.")
            if len(display_name) < 2:
                raise forms.ValidationError("Display name must be at least 2 characters.")
            if len(display_name) > 80:
                raise forms.ValidationError("Display name must be less than 80 characters.")
        return display_name
    
    def clean_interests_input(self):
        interests_str = self.cleaned_data.get('interests_input', '')
        if interests_str:
            # Clean and parse interests
            interests = [i.strip().lower() for i in interests_str.split(',') if i.strip()]
            # Remove duplicates while preserving order
            seen = set()
            unique_interests = []
            for interest in interests:
                if interest not in seen and len(interest) <= 50:
                    seen.add(interest)
                    unique_interests.append(interest)
            return unique_interests[:15]  # Max 15 interests
        return []
    
    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '')
        if bio and len(bio) < 10:
            raise forms.ValidationError("Bio must be at least 10 characters long.")
        return bio
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        interests = self.cleaned_data.get('interests_input', [])
        profile.interests = interests
        
        # Handle profile picture
        profile_pic = self.cleaned_data.get('profile_pic')
        if profile_pic and hasattr(profile, 'profile_pic'):
            profile.profile_pic = profile_pic
        
        if commit:
            profile.save()
        return profile


class SafeMeetForm(forms.ModelForm):
    """Form for scheduling safe meetings with emergency check-in"""
    
    meeting_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500'
        }),
        help_text="Select date and time of your meeting"
    )
    
    emergency_contact_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': 'Emergency contact name (optional)'
        })
    )
    
    emergency_contact_phone = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': '+1234567890 (optional)'
        })
    )
    
    expected_duration = forms.IntegerField(
        initial=2,
        min_value=1,
        max_value=24,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': 'Expected duration in hours'
        }),
        help_text="How long do you expect the meeting to last?"
    )
    
    share_location = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-pink-600 shadow-sm focus:border-pink-300 focus:ring focus:ring-pink-200 focus:ring-opacity-50'
        }),
        help_text="Share my location with emergency contact during the meeting"
    )
    
    class Meta:
        model = SafeMeetRequest
        fields = ['location', 'meeting_time', 'expected_duration']
        widgets = {
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
                'placeholder': 'Meeting location (e.g., Starbucks, 123 Main St)'
            }),
        }
    
    def clean_meeting_time(self):
        meeting_time = self.cleaned_data.get('meeting_time')
        if meeting_time:
            now = timezone.now()
            if meeting_time < now:
                raise forms.ValidationError("Meeting time must be in the future.")
            if meeting_time > now + timedelta(days=30):
                raise forms.ValidationError("Cannot schedule a meeting more than 30 days in advance.")
            if meeting_time < now + timedelta(hours=1):
                raise forms.ValidationError("Please schedule meetings at least 1 hour in advance.")
        return meeting_time
    
    def clean_emergency_contact_phone(self):
        phone = self.cleaned_data.get('emergency_contact_phone', '')
        if phone:
            # Basic phone number validation
            phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
            if not re.match(r'^\+?1?\d{10,15}$', phone_clean):
                raise forms.ValidationError("Enter a valid phone number (e.g., +1234567890).")
            return phone_clean
        return ''
    
    def clean_location(self):
        location = self.cleaned_data.get('location')
        if location:
            if len(location) < 5:
                raise forms.ValidationError("Please enter a more detailed location.")
            if len(location) > 300:
                raise forms.ValidationError("Location description is too long.")
        return location
    
    def save(self, commit=True):
        safemeet = super().save(commit=False)
        safemeet.emergency_contact_name = self.cleaned_data.get('emergency_contact_name', '')
        safemeet.emergency_contact_phone = self.cleaned_data.get('emergency_contact_phone', '')
        safemeet.share_location = self.cleaned_data.get('share_location', True)
        
        # Set check-in due time based on meeting time + expected duration
        if safemeet.meeting_time and safemeet.expected_duration:
            safemeet.check_in_due = safemeet.meeting_time + timedelta(hours=safemeet.expected_duration)
        
        if commit:
            safemeet.save()
        return safemeet


class ReportUserForm(forms.Form):
    """Form for reporting users who violate community guidelines"""
    
    REASON_CHOICES = [
        ('', 'Select a reason...'),
        ('harassment', 'Harassment or Bullying'),
        ('fake_profile', 'Fake Profile / Impersonation'),
        ('inappropriate_content', 'Inappropriate Content'),
        ('spam', 'Spam or Scam'),
        ('safety_concern', 'Safety Concern'),
        ('underage', 'Underage User'),
        ('other', 'Other'),
    ]
    
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': 'Provide additional details to help our safety team investigate...',
            'maxlength': 1000
        }),
        required=False,
        help_text="Provide any additional details that might help us investigate."
    )
    
    include_screenshot = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-pink-600 shadow-sm focus:border-pink-300 focus:ring focus:ring-pink-200 focus:ring-opacity-50'
        }),
        help_text="I can provide screenshots if contacted"
    )
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if not reason:
            raise forms.ValidationError("Please select a reason for reporting.")
        return reason
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        if description and len(description) < 10:
            raise forms.ValidationError("Please provide more details (at least 10 characters).")
        return description


class BlockUserForm(forms.Form):
    """Quick block form"""
    reason = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500',
            'placeholder': 'Optional: Why are you blocking this user?'
        })
    )
    
    also_report = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-pink-600 shadow-sm focus:border-pink-300 focus:ring focus:ring-pink-200 focus:ring-opacity-50'
        }),
        help_text="Also report this user for inappropriate behavior"
    )


class PreferenceForm(forms.Form):
    """Form for setting matching preferences"""
    age_min = forms.IntegerField(
        min_value=18, 
        max_value=100, 
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300',
            'placeholder': 'Min age'
        })
    )
    age_max = forms.IntegerField(
        min_value=18, 
        max_value=100, 
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300',
            'placeholder': 'Max age'
        })
    )
    distance_km = forms.IntegerField(
        min_value=1, 
        max_value=500, 
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300',
            'placeholder': 'Max distance (km)'
        })
    )
    gender_preference = forms.MultipleChoiceField(
        choices=[('male', 'Male'), ('female', 'Female'), ('non_binary', 'Non-Binary'), ('other', 'Other')],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'space-y-2'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError("Minimum age cannot be greater than maximum age.")
        
        return cleaned_data


class VerificationForm(forms.Form):
    """Form for submitting verification requests"""
    VERIFICATION_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('photo', 'Photo Verification'),
    ]
    
    verification_type = forms.ChoiceField(
        choices=VERIFICATION_TYPES,
        widget=forms.RadioSelect(attrs={
            'class': 'space-y-2'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300',
            'placeholder': '+1234567890'
        })
    )
    
    verification_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text="Upload a clear photo of yourself holding a paper with your username"
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        verification_type = self.cleaned_data.get('verification_type')
        
        if verification_type == 'phone' and not phone:
            raise forms.ValidationError("Phone number is required for phone verification.")
        
        if phone:
            phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
            if not re.match(r'^\+?1?\d{10,15}$', phone_clean):
                raise forms.ValidationError("Enter a valid phone number.")
            return phone_clean
        return phone