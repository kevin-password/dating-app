from django.contrib import admin
from .models import Profile, Photo, Interest, ProfileInterest, Preference, Like, Match, Message, BlockReport

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'display_name', 'gender', 'city', 'created_at')
    search_fields = ('user__username', 'display_name', 'city')
    list_filter = ('gender', 'city')

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'is_main', 'is_public', 'created_at')
    list_filter = ('is_main', 'is_public')

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')

@admin.register(ProfileInterest)
class ProfileInterestAdmin(admin.ModelAdmin):
    list_display = ('profile', 'interest')
    search_fields = ('profile__user__username', 'interest__name')

@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'age_min', 'age_max', 'gender_in', 'city', 'country', 'updated_at')
    search_fields = ('user__username', 'city', 'country')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'created_at')
    search_fields = ('user_a__username', 'user_b__username')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('match', 'from_user', 'created_at', 'is_read')
    list_filter = ('is_read',)

@admin.register(BlockReport)
class BlockReportAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'type', 'created_at')
    list_filter = ('type',)
