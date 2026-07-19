# views.py - COMPLETE WITH HEARTBEAT API
# Copy and paste this entire file

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Count, F, Avg, Case, When, FloatField
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import json
import logging
from .models import Profile, Preference, Like, Pass, Match, Message, BlockReport, SafeMeetRequest, UserActivity
from .forms import SignUpForm, ProfileForm, EnhancedProfileForm, SafeMeetForm, ReportUserForm

logger = logging.getLogger(__name__)

# ============================================================
# SAFE REVERSE GEOCODING
# ============================================================

def reverse_geocode_safe(lat, lon):
    if lat is None or lon is None:
        return None, None
    try:
        import requests
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
        headers = {'User-Agent': 'DatingApp/1.0', 'Accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            city = (address.get('city') or address.get('town') or address.get('village') or 
                   address.get('suburb') or address.get('county') or '')
            country = address.get('country', '')
            return city, country
    except ImportError:
        logger.info("Requests library not installed.")
    except Exception as e:
        logger.warning(f"Reverse geocoding failed: {e}")
    return None, None


# ============================================================
# SMART FEED ALGORITHM
# ============================================================

class SmartFeedAlgorithm:
    @staticmethod
    def get_score_weights():
        return {'compatibility': 0.30, 'availability': 0.20, 'activity': 0.15, 'safety': 0.10, 'popularity': 0.10, 'distance': 0.15}
    
    @classmethod
    def calculate_profile_score(cls, user, candidate_profile):
        weights = cls.get_score_weights()
        scores = {}
        try:
            if hasattr(user, 'profile') and user.profile.interests and candidate_profile.interests:
                shared = set(user.profile.interests) & set(candidate_profile.interests)
                scores['compatibility'] = len(shared) / max(len(user.profile.interests), 1) * 100
            else:
                scores['compatibility'] = 50
        except Exception:
            scores['compatibility'] = 50
        scores['availability'] = 100 if getattr(candidate_profile, 'is_available', False) else 30
        try:
            if getattr(candidate_profile, 'last_active', None):
                hours_inactive = (timezone.now() - candidate_profile.last_active).total_seconds() / 3600
                scores['activity'] = 100 if hours_inactive < 1 else 80 if hours_inactive < 24 else 50 if hours_inactive < 72 else 20
            else:
                scores['activity'] = 0
        except Exception:
            scores['activity'] = 50
        scores['safety'] = getattr(candidate_profile, 'safety_score', 100)
        try:
            total_swipes = getattr(candidate_profile, 'hookup_requests_sent', 0) + 1
            acceptance_rate = (getattr(candidate_profile, 'hookup_requests_accepted', 0) / total_swipes) * 100
            scores['popularity'] = min(acceptance_rate, 100)
        except Exception:
            scores['popularity'] = 50
        try:
            if hasattr(user, 'profile') and user.profile.latitude and user.profile.longitude:
                if candidate_profile.latitude and candidate_profile.longitude:
                    distance = user.profile.get_distance_to(candidate_profile)
                    scores['distance'] = 100 if distance and distance < 5 else 80 if distance and distance < 20 else 60 if distance and distance < 50 else 40 if distance and distance < 100 else 20 if distance else 50
                else:
                    scores['distance'] = 50
            else:
                scores['distance'] = 50
        except Exception:
            scores['distance'] = 50
        try:
            return round(sum(scores.get(k, 50) * weights.get(k, 0.15) for k in weights), 2)
        except Exception:
            return 50.0
    
    @classmethod
    def get_smart_feed(cls, user, limit=20):
        try:
            blocked_ids = BlockReport.objects.filter(Q(from_user=user) | Q(to_user=user)).values_list('from_user_id', 'to_user_id')
            blocked_users = set()
            for from_id, to_id in blocked_ids:
                blocked_users.add(from_id if to_id == user.id else to_id)
            swiped_users = set(Like.objects.filter(from_user=user).values_list('to_user_id', flat=True)) | set(Pass.objects.filter(from_user=user).values_list('to_user_id', flat=True))
            matched_users = set()
            for m in Match.objects.filter(Q(user_a=user) | Q(user_b=user)):
                matched_users.add(m.user_b_id if m.user_a_id == user.id else m.user_a_id)
            excluded_ids = blocked_users | swiped_users | matched_users | {user.id}
            candidates = Profile.objects.exclude(user_id__in=excluded_ids).select_related('user')[:50]
            scored_candidates = [(p, cls.calculate_profile_score(user, p)) for p in candidates]
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            return [profile for profile, score in scored_candidates[:limit]]
        except Exception as e:
            logger.error(f"Smart feed error: {e}")
            return []


# ============================================================
# AUTH VIEWS
# ============================================================

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user, defaults={'display_name': user.username, 'safety_score': 100})
            Preference.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Welcome! Complete your profile to get started.")
            return redirect('profile')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})


# ============================================================
# FEED & SWIPE VIEWS
# ============================================================

@login_required
def feed_view(request):
    user = request.user
    try:
        if user.profile.interests and len(user.profile.interests) > 0:
            candidates = SmartFeedAlgorithm.get_smart_feed(user, limit=1)
            next_profile = candidates[0] if candidates else None
        else:
            blocked_qs = BlockReport.objects.filter(Q(from_user=user) | Q(to_user=user))
            blocked_ids = [b.from_user_id if b.to_user_id == user.id else b.to_user_id for b in blocked_qs]
            liked_ids = list(Like.objects.filter(from_user=user).values_list('to_user_id', flat=True))
            passed_ids = list(Pass.objects.filter(from_user=user).values_list('to_user_id', flat=True))
            matched_qs = Match.objects.filter(Q(user_a=user) | Q(user_b=user))
            matched_ids = [m.user_a_id if m.user_b_id == user.id else m.user_b_id for m in matched_qs]
            exclude_ids = list(set(blocked_ids + liked_ids + passed_ids + matched_ids + [user.id]))
            candidates = Profile.objects.exclude(user_id__in=exclude_ids).select_related('user').order_by('-is_available', '-updated_at')
            next_profile = candidates.first()
    except Exception:
        next_profile = None
    is_matched = False
    if next_profile:
        try:
            is_matched = Match.objects.filter(Q(user_a=user, user_b=next_profile.user) | Q(user_a=next_profile.user, user_b=user)).exists()
        except Exception:
            is_matched = False
    discover_suggestions = []
    try:
        discover_suggestions = Profile.objects.exclude(Q(user_id__in=[user.id]) | Q(user=user)).filter(last_active__gte=timezone.now() - timedelta(hours=24), safety_score__gte=80).select_related('user').order_by('?')[:5]
    except Exception:
        pass
    return render(request, 'feed.html', {'next_profile': next_profile, 'is_matched': is_matched, 'discover_suggestions': discover_suggestions})


@login_required
def swipe_action(request, profile_id, action):
    target_profile = get_object_or_404(Profile, id=profile_id)
    target_user = target_profile.user
    if target_user == request.user:
        messages.error(request, "You can't do that to yourself!")
        return redirect('home')
    if action == 'like':
        Like.objects.get_or_create(from_user=request.user, to_user=target_user)
        if Like.objects.filter(from_user=target_user, to_user=request.user).exists():
            match, created = Match.objects.get_or_create(user_a=request.user, user_b=target_user)
            if created:
                messages.success(request, f"🔥 It's a match with {target_profile.display_name}!")
            else:
                messages.info(request, f"You already matched with {target_profile.display_name}!")
    elif action == 'pass':
        Pass.objects.get_or_create(from_user=request.user, to_user=target_user)
    return redirect('home')


# ============================================================
# PROFILE VIEWS
# ============================================================

@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        if 'toggle_availability' in request.POST:
            profile.is_available = not profile.is_available
            profile.save()
            status = "🟢 Available Now" if profile.is_available else "🔴 Hidden"
            messages.success(request, f"Your status is now: {status}")
            return redirect('profile')
        form = EnhancedProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            profile.refresh_from_db()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EnhancedProfileForm(instance=profile)
    stats = {
        'likes_received': Like.objects.filter(to_user=request.user).count(),
        'total_matches': Match.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)).count(),
        'messages_sent': Message.objects.filter(from_user=request.user).count(),
        'profile_completion': calculate_profile_completion(profile)
    }
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile, 'stats': stats})


def calculate_profile_completion(profile):
    try:
        fields = ['display_name', 'bio', 'birth_date', 'gender', 'city', 'country']
        completed = sum(1 for field in fields if getattr(profile, field, None))
        if profile.interests and len(profile.interests) > 0:
            completed += 1
        if profile.photos.exists():
            completed += 1
        return int((completed / (len(fields) + 2)) * 100)
    except Exception:
        return 0


# ============================================================
# MESSAGING VIEWS
# ============================================================

@login_required
def messages_view(request):
    matches = Match.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)).order_by('-created_at')
    enhanced_matches = []
    for match in matches:
        try:
            other_user = match.user_b if match.user_a == request.user else match.user_a
            unread_count = Message.objects.filter(match=match, from_user=other_user, is_read=False).count()
            last_message = Message.objects.filter(match=match).order_by('-created_at').first()
            is_online = (timezone.now() - other_user.profile.last_active).seconds < 300 if other_user.profile.last_active else False
            enhanced_matches.append({'match': match, 'other_user': other_user, 'unread_count': unread_count, 'last_message': last_message, 'is_online': is_online})
        except Exception:
            continue
    return render(request, 'messages_list.html', {'matches': enhanced_matches})


@login_required
def chat_view(request, match_id):
    match = get_object_or_404(Match, Q(user_a=request.user) | Q(user_b=request.user), id=match_id)
    msgs = match.messages.filter(expires_at__gt=timezone.now()).order_by('created_at')
    other_user = match.user_b if match.user_a == request.user else match.user_a
    msgs.filter(from_user=other_user, is_read=False).update(is_read=True)
    is_paywalled = (request.user.profile.gender == 'male' and not request.user.profile.is_subscribed)
    safe_meets = SafeMeetRequest.objects.filter(Q(from_user=request.user, to_user=other_user) | Q(from_user=other_user, to_user=request.user)).order_by('-created_at')
    return render(request, 'chat.html', {'match': match, 'other_user': other_user, 'messages': msgs, 'is_paywalled': is_paywalled, 'safe_meets': safe_meets, 'blocked_by_you': BlockReport.objects.filter(from_user=request.user, to_user=other_user).exists(), 'blocked_you': BlockReport.objects.filter(from_user=other_user, to_user=request.user).exists()})


@login_required
def send_message_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    other_user = match.user_b if match.user_a == request.user else match.user_a
    if BlockReport.objects.filter(Q(from_user=request.user, to_user=other_user) | Q(from_user=other_user, to_user=request.user)).exists():
        messages.error(request, "Cannot send messages to this user.")
        return redirect('chat', match_id=match.id)
    if request.user.profile.gender == 'male' and not request.user.profile.is_subscribed:
        messages.error(request, "Please upgrade to Premium.")
        return redirect('chat', match_id=match.id)
    body = request.POST.get('body')
    if body:
        Message.objects.create(match=match, from_user=request.user, body=body)
    return redirect('chat', match_id=match.id)


@login_required
def send_hookup_request_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    request.user.profile.hookup_requests_sent += 1
    request.user.profile.save()
    Message.objects.create(match=match, from_user=request.user, body="I'd like to meet up. Are you free?", is_hookup_request=True)
    messages.success(request, "Hookup request sent!")
    return redirect('chat', match_id=match.id)


@login_required
def accept_hookup_view(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    if msg.match.user_a != request.user and msg.match.user_b != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect('messages')
    if msg.from_user != request.user:
        msg.is_hookup_accepted = True
        msg.save()
        msg.from_user.profile.hookup_requests_accepted += 1
        msg.from_user.profile.save()
        messages.success(request, "Hookup request accepted!")
    return redirect('chat', match_id=msg.match.id)


# ============================================================
# SUBSCRIPTION
# ============================================================

@login_required
def subscribe_view(request):
    if request.method == 'POST':
        request.user.profile.is_subscribed = True
        request.user.profile.save()
        messages.success(request, "Welcome to Premium!")
    return render(request, 'subscribe.html')


# ============================================================
# KNOCKS VIEWS
# ============================================================

@login_required
def knocks_view(request):
    knocks = Like.objects.filter(to_user=request.user).select_related('from_user__profile').order_by('-created_at')
    enhanced_knocks = []
    for knock in knocks:
        try:
            profile = knock.from_user.profile
            mutual = list(set(request.user.profile.interests) & set(profile.interests)) if request.user.profile.interests and profile.interests else []
            compatibility = SmartFeedAlgorithm.calculate_profile_score(request.user, profile) if request.user.profile.interests else 0
            enhanced_knocks.append({'knock': knock, 'profile': profile, 'mutual_interests': mutual, 'compatibility': compatibility})
        except Exception:
            continue
    return render(request, 'knocks.html', {'knocks': enhanced_knocks})


@login_required
def accept_knock_view(request, like_id):
    knock = get_object_or_404(Like, id=like_id, to_user=request.user)
    Match.objects.get_or_create(user_a=request.user, user_b=knock.from_user)
    knock.delete()
    messages.success(request, f"🔥 You matched with {knock.from_user.profile.display_name}!")
    return redirect('knocks')


@login_required
def reject_knock_view(request, like_id):
    knock = get_object_or_404(Like, id=like_id, to_user=request.user)
    Pass.objects.get_or_create(from_user=request.user, to_user=knock.from_user)
    knock.delete()
    return redirect('knocks')


# ============================================================
# SAFETY FEATURES
# ============================================================

@login_required
def safety_center_view(request):
    user = request.user
    active_meets = SafeMeetRequest.objects.filter(Q(from_user=user) | Q(to_user=user), meeting_time__gte=timezone.now(), is_confirmed=True).order_by('meeting_time')
    pending_meets = SafeMeetRequest.objects.filter(Q(from_user=user) | Q(to_user=user), is_confirmed=False)
    blocked_users = BlockReport.objects.filter(from_user=user).select_related('to_user__profile')
    return render(request, 'safety_center.html', {'active_meets': active_meets, 'pending_meets': pending_meets, 'blocked_users': blocked_users, 'safety_tips': ["Meet in public", "Share location", "Trust instincts", "Keep info private"], 'profile_safety_score': getattr(user.profile, 'safety_score', 100)})


@login_required
def report_user_view(request, user_id):
    from django.contrib.auth.models import User
    reported_user = get_object_or_404(User, id=user_id)
    if reported_user == request.user:
        messages.error(request, "Cannot report yourself.")
        return redirect('home')
    if request.method == 'POST':
        form = ReportUserForm(request.POST)
        if form.is_valid():
            BlockReport.objects.create(from_user=request.user, to_user=reported_user, reason=form.cleaned_data['reason'], description=form.cleaned_data.get('description', ''))
            BlockReport.objects.get_or_create(from_user=request.user, to_user=reported_user, defaults={'reason': 'auto_block_from_report'})
            profile = reported_user.profile
            profile.safety_score = max(0, profile.safety_score - 20)
            profile.save()
            messages.success(request, "Report submitted!")
            return redirect('home')
    else:
        form = ReportUserForm()
    return render(request, 'report_user.html', {'form': form, 'reported_user': reported_user})


@login_required
def block_user_view(request, user_id):
    from django.contrib.auth.models import User
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "Cannot block yourself.")
        return redirect('home')
    BlockReport.objects.get_or_create(from_user=request.user, to_user=target_user, defaults={'reason': 'user_block'})
    messages.success(request, f"Blocked {target_user.profile.display_name}.")
    return redirect('home')


@login_required
def schedule_safe_meet_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    if request.user not in [match.user_a, match.user_b]:
        messages.error(request, "Unauthorized.")
        return redirect('messages')
    other_user = match.user_b if match.user_a == request.user else match.user_a
    if request.method == 'POST':
        form = SafeMeetForm(request.POST)
        if form.is_valid():
            safemeet = form.save(commit=False)
            safemeet.from_user = request.user
            safemeet.to_user = other_user
            safemeet.match = match
            safemeet.status = 'pending'
            safemeet.is_confirmed = False
            safemeet.check_in_due = form.cleaned_data['meeting_time'] + timedelta(hours=safemeet.expected_duration)
            safemeet.save()
            Message.objects.create(match=match, from_user=request.user, body=f"🛡️ Meeting proposed: {safemeet.meeting_time.strftime('%B %d at %I:%M %p')} at {safemeet.location}", is_system_message=True)
            messages.success(request, "Meeting proposed!")
            return redirect('chat', match_id=match.id)
    else:
        form = SafeMeetForm()
    return render(request, 'schedule_safe_meet.html', {'form': form, 'match': match, 'other_user': other_user})


@login_required
def confirm_safe_meet_view(request, safemeet_id):
    safemeet = get_object_or_404(SafeMeetRequest, id=safemeet_id)
    if request.user != safemeet.to_user:
        messages.error(request, "Only invited person can confirm.")
        return redirect('safety_center')
    safemeet.is_confirmed = True
    safemeet.status = 'confirmed'
    safemeet.confirmed_by = request.user
    safemeet.confirmed_at = timezone.now()
    safemeet.save()
    if safemeet.match:
        Message.objects.create(match=safemeet.match, from_user=request.user, body=f"✅ Meeting confirmed for {safemeet.meeting_time.strftime('%B %d at %I:%M %p')}!", is_system_message=True)
    messages.success(request, "✅ Meeting confirmed!")
    return redirect('safety_center')


@login_required
def emergency_check_in_view(request, safemeet_id):
    safemeet = get_object_or_404(SafeMeetRequest, id=safemeet_id)
    if request.user not in [safemeet.from_user, safemeet.to_user]:
        messages.error(request, "Unauthorized.")
        return redirect('safety_center')
    is_overdue = safemeet.check_in_due and safemeet.check_in_due < timezone.now()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'check_in':
            safemeet.checked_in = True
            safemeet.save()
            messages.success(request, "✅ Check-in confirmed!")
        elif action == 'emergency':
            safemeet.checked_in = True
            safemeet.save()
            messages.warning(request, "🚨 Emergency triggered.")
        return redirect('safety_center')
    return render(request, 'emergency_check_in.html', {'safemeet': safemeet, 'is_overdue': is_overdue})


# ============================================================
# GEOLOCATION API
# ============================================================

@login_required
@require_http_methods(["POST"])
def api_update_location_view(request):
    try:
        body = json.loads(request.body)
        latitude, longitude = float(body.get('latitude', 0)), float(body.get('longitude', 0))
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return JsonResponse({'status': 'error'}, status=400)
        profile = request.user.profile
        profile.latitude, profile.longitude = latitude, longitude
        city, country = reverse_geocode_safe(latitude, longitude)
        if city: profile.city = city
        if country: profile.country = country
        profile.save()
        return JsonResponse({'status': 'success', 'city': profile.city or '', 'country': profile.country or ''})
    except Exception:
        return JsonResponse({'status': 'error'}, status=500)


# ============================================================
# REAL-TIME HEARTBEAT API (NEW)
# ============================================================

@login_required
@require_http_methods(["POST"])
def api_heartbeat_view(request):
    """Pinged every 3 seconds by frontend. Returns live notifications count."""
    user = request.user
    
    # Update user's last_active timestamp
    user.profile.last_active = timezone.now()
    user.profile.save(update_fields=['last_active'])
    
    # Count new knocks (likes received)
    knocks_count = Like.objects.filter(to_user=user).count()
    
    # Count unread messages
    unread = Message.objects.filter(
        match__in=Match.objects.filter(Q(user_a=user) | Q(user_b=user)),
        is_read=False
    ).exclude(from_user=user).count()
    
    return JsonResponse({
        'status': 'ok',
        'online': True,
        'knocks': knocks_count,
        'unread_messages': unread,
        'timestamp': timezone.now().isoformat()
    })


# ============================================================
# API ENDPOINTS
# ============================================================

@login_required
@require_http_methods(["GET"])
def api_feed_view(request):
    profiles = SmartFeedAlgorithm.get_smart_feed(request.user, limit=20)
    data = [{'id': p.id, 'display_name': p.display_name, 'age': p.age, 'city': p.city or '', 'is_available': p.is_available} for p in profiles]
    return JsonResponse({'profiles': data})


@login_required
@require_http_methods(["POST"])
def api_swipe_view(request):
    try:
        body = json.loads(request.body)
        profile_id, action = body.get('profile_id'), body.get('action')
    except:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    if action == 'like':
        Like.objects.get_or_create(from_user=request.user, to_user_id=profile_id)
        return JsonResponse({'status': 'liked'})
    Pass.objects.get_or_create(from_user=request.user, to_user_id=profile_id)
    return JsonResponse({'status': 'passed'})


@login_required
@require_http_methods(["GET"])
def api_matches_view(request):
    matches = Match.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)).order_by('-created_at')
    data = [{'id': m.id, 'display_name': (m.user_b if m.user_a == request.user else m.user_a).profile.display_name} for m in matches]
    return JsonResponse({'matches': data})


@login_required
@require_http_methods(["GET"])
def api_user_stats_view(request):
    u = request.user
    return JsonResponse({'knocks': Like.objects.filter(to_user=u).count(), 'matches': Match.objects.filter(Q(user_a=u) | Q(user_b=u)).count()})
