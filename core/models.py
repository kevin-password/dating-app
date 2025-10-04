from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', unique=True)
    display_name = models.CharField(max_length=80, blank=True, db_index=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, db_index=True)
    birth_date = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=80, blank=True, db_index=True)
    country = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.display_name or self.user.username

class Photo(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='photos', db_index=True)
    image = models.ImageField(upload_to='profile_photos/')
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
    gender_in = models.CharField(max_length=64, blank=True)  # e.g. "male,female"
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
    def __str__(self):
        return f"Msg by {self.from_user.username} in {self.match_id}"

class BlockReport(models.Model):
    TYPE_CHOICES = [('block', 'Block'), ('report', 'Report')]
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_reports_sent', db_index=True)
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_reports_received', db_index=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('from_user', 'to_user', 'type')
    def __str__(self):
        return f"{self.type} {self.from_user.username}→{self.to_user.username}"
