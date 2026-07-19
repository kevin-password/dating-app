# models.py - COMPLETE ENHANCED VERSION WITH DISTANCE CALCULATION
# Copy and paste this entire file

import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from math import radians, sin, cos, sqrt, atan2

class Profile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'), 
        ('female', 'Female'), 
        ('non_binary', 'Non-Binary'),
        ('other', 'Other')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', unique=True)
    display_name = models.CharField(max_length=80, blank=True, db_index=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True, db_index=True)
    birth_date = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=80, blank=True, db_index=True)
    country = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True, db_index=True)
    
    # Subscription and availability
    is_subscribed = models.BooleanField(default=False, help_text="Male users must be True to send messages")
    is_available = models.BooleanField(default=False, help_text="Toggle to signal availability")
    
    # NEW: Enhanced profile fields
    interests = models.JSONField(default=list, blank=True, help_text="List of interest tags")
    verification_level = models.CharField(
        max_length=20, 
        default='unverified',
        choices=[
            ('unverified', 'Unverified'),
            ('email_verified', 'Email Verified'),
            ('photo_verified', 'Photo Verified'),
            ('id_verified', 'ID Verified')
        ]
    )
    safety_score = models.IntegerField(default=100, help_text="Safety reputation score (0-100)")
    
    # NEW: Activity tracking
    hookup_requests_sent = models.IntegerField(default=0)
    hookup_requests_accepted = models.IntegerField(default=0)
    blocked_users_count = models.IntegerField(default=0)
    total_swipes = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    
    # NEW: Location coordinates for distance-based matching
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # NEW: Privacy settings
    show_online_status = models.BooleanField(default=True)
    show_distance = models.BooleanField(default=True)
    incognito_mode = models.BooleanField(default=False, help_text="Hide from feeds until you swipe first")

    class Meta:
        indexes = [
            models.Index(fields=['is_available', '-last_active']),
            models.Index(fields=['gender', 'is_available']),
            models.Index(fields=['safety_score']),
            models.Index(fields=['verification_level']),
        ]

    @property
    def age(self):
        if self.birth_date:
            today = datetime.date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def get_compatibility_score(self, other_profile=None):
        """Calculate compatibility based on shared interests"""
        if not other_profile or not self.interests or not other_profile.interests:
            return 0
        shared = set(self.interests) & set(other_profile.interests)
        if not self.interests:
            return 0
        return round((len(shared) / len(self.interests)) * 100, 1)

    def get_mutual_interests(self, other_profile=None):
        """Get list of mutual interests with another profile"""
        if not other_profile or not self.interests or not other_profile.interests:
            return []
        return list(set(self.interests) & set(other_profile.interests))

    def get_distance_to(self, other_profile):
        """
        Calculate distance in kilometers between two profiles using the Haversine formula.
        Returns None if coordinates are missing.
        SAFE: Won't crash if coordinates are None.
        """
        try:
            if not (self.latitude and self.longitude and other_profile.latitude and other_profile.longitude):
                return None
            
            R = 6371  # Earth's radius in kilometers
            
            lat1 = radians(float(self.latitude))
            lon1 = radians(float(self.longitude))
            lat2 = radians(float(other_profile.latitude))
            lon2 = radians(float(other_profile.longitude))
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            return round(R * c, 1)
        except Exception:
            return None

    def is_safe_user(self):
        """Check if user meets safety threshold"""
        return self.safety_score >= 70

    def __str__(self):
        return self.display_name or self.user.username


class Photo(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='photos', db_index=True)
    image = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    is_public = models.BooleanField(default=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_main:
            Photo.objects.filter(profile=self.profile).exclude(id=self.id).update(is_main=False)
            
    def __str__(self):
        return f"{self.profile} photo #{self.id}"


class Interest(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    
    def __str__(self):
        return self.name


class ProfileInterest(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='profile_interests')
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE, related_name='interest_profiles')
    
    class Meta:
        unique_together = ('profile', 'interest')
    
    def __str__(self):
        return f"{self.profile} ↔ {self.interest}"


class Preference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference', unique=True)
    age_min = models.IntegerField(blank=True, null=True)
    age_max = models.IntegerField(blank=True, null=True)
    gender_in = models.CharField(max_length=64, blank=True)
    distance_km = models.IntegerField(blank=True, null=True)
    city = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    interests_any = models.JSONField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preference({self.user.username})"


class Like(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes_sent', db_index=True)
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes_received', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
    
    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username}"


class Pass(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passes_sent', db_index=True)
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passes_received', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
    
    def __str__(self):
        return f"{self.from_user.username} passed on {self.to_user.username}"


class Match(models.Model):
    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_a', db_index=True)
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_b', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user_a', 'user_b')
    
    def save(self, *args, **kwargs):
        if self.user_a_id and self.user_b_id and self.user_a_id > self.user_b_id:
            self.user_a_id, self.user_b_id = self.user_b_id, self.user_a_id
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Match({self.user_a.username} & {self.user_b.username})"


class Message(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='messages', db_index=True)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent', db_index=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_hookup_request = models.BooleanField(default=False, help_text="True if this is a meetup request")
    is_hookup_accepted = models.BooleanField(default=False, help_text="True if the request was accepted")
    is_system_message = models.BooleanField(default=False, help_text="System-generated messages (safety, etc.)")
    
    # Ephemeral Chat Field
    expires_at = models.DateTimeField(blank=True, null=True, help_text="When this message will permanently disappear")

    def save(self, *args, **kwargs):
        # Automatically set expiration to 24 hours from now if not already set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Msg by {self.from_user.username} in {self.match_id}"


class BlockReport(models.Model):
    TYPE_CHOICES = [
        ('block', 'Block'), 
        ('report', 'Report')
    ]
    
    REASON_CHOICES = [
        ('harassment', 'Harassment'),
        ('fake_profile', 'Fake Profile'),
        ('inappropriate_content', 'Inappropriate Content'),
        ('spam', 'Spam/Scam'),
        ('safety_concern', 'Safety Concern'),
        ('auto_block_from_report', 'Auto-blocked from Report'),
        ('user_block', 'User Block'),
        ('other', 'Other'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_reports_sent', db_index=True)
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_reports_received', db_index=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='block')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, default='user_block')
    description = models.TextField(blank=True, help_text="Additional details for reports")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user', 'type')
        indexes = [
            models.Index(fields=['type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.type} {self.from_user.username}→{self.to_user.username}"


# ============================================================
# SAFETY FEATURE MODELS
# ============================================================

class SafeMeetRequest(models.Model):
    """Safety check-in system for real-life meetings"""
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed Safely'),
        ('emergency', 'Emergency Triggered'),
        ('cancelled', 'Cancelled'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='safemeet_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='safemeet_received')
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='safe_meets')
    
    # Meeting details
    location = models.CharField(max_length=300)
    meeting_time = models.DateTimeField()
    expected_duration = models.IntegerField(default=2, help_text="Expected duration in hours")
    
    # Safety features
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    share_location = models.BooleanField(default=True, help_text="Share real-time location with emergency contact")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_meets')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Check-in system
    check_in_due = models.DateTimeField(null=True, blank=True, help_text="When the safety check-in is expected")
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    check_in_location = models.CharField(max_length=300, blank=True, help_text="Location during check-in")
    
    # Emergency handling
    emergency_triggered = models.BooleanField(default=False)
    emergency_triggered_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-meeting_time']
        indexes = [
            models.Index(fields=['status', 'meeting_time']),
            models.Index(fields=['from_user', 'to_user']),
        ]
    
    def __str__(self):
        return f"SafeMeet: {self.from_user.username} & {self.to_user.username} at {self.meeting_time}"
    
    def is_active(self):
        return self.status in ['pending', 'confirmed', 'in_progress']
    
    def is_overdue(self):
        if self.check_in_due and not self.checked_in:
            return timezone.now() > self.check_in_due
        return False


class UserActivity(models.Model):
    """Track user behavior for safety, analytics, and recommendations"""
    ACTIVITY_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('swipe', 'Swipe'),
        ('match', 'Match'),
        ('message', 'Message'),
        ('hookup_request', 'Hookup Request'),
        ('report', 'Report'),
        ('block', 'Block'),
        ('profile_update', 'Profile Update'),
        ('photo_upload', 'Photo Upload'),
        ('safety_check', 'Safety Check-in'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES)
    description = models.TextField(blank=True, help_text="Additional details about the activity")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Optional tracking data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True, help_text="mobile, desktop, tablet")
    
    # Related objects (optional)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_activities')
    related_match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"


class UserVerification(models.Model):
    """Track user verification attempts"""
    VERIFICATION_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('photo', 'Photo Verification'),
        ('id', 'ID Verification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    proof_file = models.FileField(upload_to='verifications/', null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_users')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'verification_type')
    
    def __str__(self):
        return f"{self.user.username} - {self.verification_type} - {self.status}"


class UserSession(models.Model):
    """Track user sessions for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"Session: {self.user.username} from {self.ip_address}"