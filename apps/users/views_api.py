from rest_framework.decorators import api_view,permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import find_similar_users, calculate_user_similarity
from .models import Match, UserProfile, FriendRequest
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from apps.kyc.models import KYCProfile


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def match_users(request):
    # Check if user has approved KYC
    try:
        kyc_profile = request.user.kyc_profile
        if kyc_profile.status != 'approved':
            return Response({
                "detail": f"KYC approval required to find matches. Your status: {kyc_profile.status or 'not_submitted'}",
                "kyc_status": kyc_profile.status
            }, status=403)
    except KYCProfile.DoesNotExist:
        return Response({
            "detail": "You must complete and get KYC approval before finding matches",
            "kyc_status": "not_submitted"
        }, status=403)
    
    try:
        profile = request.user.userprofile
    except  UserProfile.DoesNotExist:
        return Response({"detail": "User profile not found"}, status=404)
    matches = find_similar_users(profile)

    result = []

    for user, similarity in matches:
        # ✅ Privacy check: Skip if private profile (unless they are friends)
        if not user.public_profile:
            is_friend = FriendRequest.objects.filter(
                status='accepted'
            ).filter(
                (Q(from_user=request.user, to_user=user.user) | Q(from_user=user.user, to_user=request.user))
            ).exists()
            
            if not is_friend:
                # Skip this match - private profile and not a friend
                continue

        result.append({
            "username": user.user.username,
            "similarity": similarity
        })

    return Response(result)
class MatchActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id):
        match = get_object_or_404(Match, id=match_id)

        # Security: only the receiver can accept/reject
        if match.user2 != request.user:
            return Response({"detail": "Not authorized"}, status=403)

        action = request.data.get("action").lower() # "accept" or "reject"

        if action == "accept":
            match.status = "accepted"
            match.save()
            # Optional: create reverse match or chat room here
            return Response({"status": "accepted"})

        elif action == "reject":
            match.status = "rejected"
            match.save()
            return Response({"status": "rejected"})

        return Response({"detail": "Invalid action"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Search users by username, first name, or last name - respects privacy settings"""
    # Removed KYC check - search is just general user discovery
    
    query = request.query_params.get('q', '').strip()
    
    if not query or len(query) < 2:
        return Response({"results": []})
    
    # Search by username, first_name, or last_name
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:20]  # Limit to 20 results
    
    results = []
    for user in users:
        profile_pic = None
        try:
            profile = user.userprofile
            
            # ✅ Privacy check: Skip if private profile (unless they are friends)
            if not profile.public_profile:
                is_friend = FriendRequest.objects.filter(
                    status='accepted'
                ).filter(
                    (Q(from_user=request.user, to_user=user) | Q(from_user=user, to_user=request.user))
                ).exists()
                
                if not is_friend:
                    # Skip this user - private profile and not a friend
                    continue
            
            if profile.profile_picture:
                profile_pic = profile.profile_picture.url
        except UserProfile.DoesNotExist:
            pass
        
        results.append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_pic,
            "location": profile.location if 'profile' in locals() else ""
        })
    
    return Response({"results": results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request, user_id):
    """Get public profile details of a user by ID"""
    try:
        user = User.objects.get(id=user_id)
        profile = user.userprofile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return Response({"detail": "User profile not found"}, status=404)
    
    # Check privacy settings - only allow if:
    # 1. User's profile is public, OR
    # 2. Requester is the profile owner, OR
    # 3. Requester is a friend (accepted friend request exists)
    if not profile.public_profile:
        # Profile is private
        if not request.user.is_authenticated:
            # Not logged in - cannot view private profile
            return Response(
                {"detail": "This profile is private. You must be a friend to view it."},
                status=403
            )
        
        # Check if requester is the profile owner
        if request.user.id != user_id:
            # Check if they are friends (mutual accepted friend request)
            is_friend = FriendRequest.objects.filter(
                status='accepted'
            ).filter(
                (Q(from_user=request.user, to_user=user) | Q(from_user=user, to_user=request.user))
            ).exists()
            
            if not is_friend:
                return Response(
                    {"detail": "This profile is private. You must be a friend to view it."},
                    status=403
                )
    
    profile_pic = profile.profile_picture.url if profile.profile_picture else None
    interests = [{"id": i.id, "name": i.name, "category": i.category} for i in profile.interests.all()]
    
    return Response({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "profile_picture": profile_pic,
        "bio": profile.bio,
        "location": profile.location,
        "preferred_destinations": profile.preferred_destinations,
        "travel_style": profile.travel_style,
        "pace": profile.pace,
        "accomodation_preference": profile.accomodation_preference,
        "budget_level": profile.budget_level,
        "adventure_level": profile.adventure_level,
        "social_level": profile.social_level,
        "interests": interests,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_similarity(request, user_id):
    """Calculate similarity score between current user and target user (0-100%)"""
    try:
        current_profile = request.user.userprofile
        target_user = User.objects.get(id=user_id)
        target_profile = target_user.userprofile
    except (UserProfile.DoesNotExist, User.DoesNotExist):
        return Response({"detail": "User profile not found"}, status=404)
    
    similarity_score = calculate_user_similarity(current_profile, target_profile)
    
    return Response({
        "similarity": similarity_score,
        "username": target_user.username,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trip_user_suggestions(request):
    """
    Get user suggestions for inviting to a trip.
    Based on similarity scores, excludes current user, trip members, and already invited users.
    
    Query params:
    - trip_id: Trip ID to get suggestions for
    """
    from apps.trips.models import Trip, TripInvitation
    
    trip_id = request.query_params.get('trip_id')
    if not trip_id:
        return Response({"detail": "trip_id parameter required"}, status=400)
    
    try:
        trip = Trip.objects.get(id=trip_id)
    except Trip.DoesNotExist:
        return Response({"detail": "Trip not found"}, status=404)
    
    # Only trip members can request suggestions
    user_profile = request.user.userprofile
    is_creator = trip.creator == user_profile
    is_member = trip.participants.filter(id=user_profile.id).exists()
    
    if not is_creator and not is_member:
        return Response({"detail": "Only trip members can request suggestions"}, status=403)
    
    # Get current user's profile
    current_profile = request.user.userprofile
    
    # Get trip members and invited users
    trip_members = set(trip.participants.values_list('id', flat=True))
    invited_users = set(
        TripInvitation.objects.filter(trip=trip, status='pending').values_list('invited_user_id', flat=True)
    )
    
    # Get all other users for similarity comparison
    all_profiles = UserProfile.objects.exclude(
        id__in=trip_members | invited_users | {current_profile.id}
    )
    
    # Calculate similarity for each user
    from .utils import calculate_user_similarity
    
    suggestions = []
    for profile in all_profiles:
        try:
            # Check if they are friends
            is_friend = FriendRequest.objects.filter(
                status='accepted'
            ).filter(
                (Q(from_user=request.user, to_user=profile.user) | Q(from_user=profile.user, to_user=request.user))
            ).exists()
            
            # ✅ Privacy check: Skip if private profile (unless they are friends)
            if not profile.public_profile and not is_friend:
                # Skip this user - private profile and not a friend
                continue
            
            similarity = calculate_user_similarity(current_profile, profile)
            
            # Only suggest users with > 0.3 (30%) similarity
            if similarity > 0.3:
                user = profile.user
                # Get profile picture URL
                profile_pic_url = None
                if profile.profile_picture:
                    profile_pic_url = profile.profile_picture.url if hasattr(profile.profile_picture, 'url') else str(profile.profile_picture)
                
                suggestions.append({
                    'id': profile.id,
                    'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email,
                    'avatar': (user.first_name[0] + user.last_name[0]).upper() if user.first_name and user.last_name else user.username[0].upper(),
                    'profile_picture': profile_pic_url,
                    'interests': list(profile.constraint_tags.values_list('name', flat=True)),
                    'similarity': round(similarity * 100, 0),  # Convert to percentage
                    'is_friend': is_friend
                })
        except Exception as e:
            # Skip users with calculation errors
            continue
    
    # Sort by similarity descending
    suggestions.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Limit to top 10
    return Response(suggestions[:10])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request, user_id):
    """Send a friend request to another user"""
    from datetime import timedelta
    from django.utils import timezone
    
    # Check if user has approved KYC
    try:
        kyc_profile = request.user.kyc_profile
        if kyc_profile.status != 'approved':
            return Response({
                "detail": f"KYC approval required to send friend requests. Your status: {kyc_profile.status or 'not_submitted'}",
                "kyc_status": kyc_profile.status
            }, status=403)
    except KYCProfile.DoesNotExist:
        return Response({
            "detail": "You must complete and get KYC approval before sending friend requests",
            "kyc_status": "not_submitted"
        }, status=403)
    
    try:
        to_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)
    
    if to_user == request.user:
        return Response({"detail": "Cannot send friend request to yourself"}, status=400)
    
    # Check if request already exists
    existing_request = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=to_user
    ).first()
    
    if existing_request:
        # If rejected, check if cooldown period has passed (7 days)
        if existing_request.status == 'rejected':
            cooldown_period = timedelta(days=7)
            time_since_rejection = timezone.now() - existing_request.updated_at
            
            if time_since_rejection < cooldown_period:
                remaining_time = cooldown_period - time_since_rejection
                days_remaining = remaining_time.days
                hours_remaining = remaining_time.seconds // 3600
                
                return Response({
                    "detail": f"Friend request was rejected. You can send another request in {days_remaining}d {hours_remaining}h",
                    "status": "rejected",
                    "cooldown_remaining": {
                        "days": days_remaining,
                        "hours": hours_remaining,
                        "total_seconds": remaining_time.total_seconds()
                    }
                }, status=400)
            else:
                # Cooldown has passed, delete the old request and allow new one
                existing_request.delete()
        else:
            # Pending or accepted - cannot send another request
            return Response({
                "detail": f"Friend request already {existing_request.status}",
                "status": existing_request.status
            }, status=400)
    
    # Check for reverse request (to_user sent to request.user)
    reverse_request = FriendRequest.objects.filter(
        from_user=to_user,
        to_user=request.user,
        status='pending'
    ).first()
    
    if reverse_request:
        # Auto-accept if there's a pending request from them
        reverse_request.status = 'accepted'
        reverse_request.save()
        
        # Create a request from current user too
        friend_request = FriendRequest.objects.create(
            from_user=request.user,
            to_user=to_user,
            status='accepted'
        )
        return Response({
            "detail": "Friend request accepted and mutual friendship created",
            "status": "accepted",
            "type": "outgoing",
            "request_id": friend_request.id
        }, status=201)
    
    # Create new friend request
    friend_request = FriendRequest.objects.create(
        from_user=request.user,
        to_user=to_user,
        status='pending'
    )
    
    return Response({
        "detail": "Friend request sent",
        "status": "pending",
        "type": "outgoing",
        "request_id": friend_request.id
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friend_request_status(request, user_id):
    """Get friend request status between current user and another user"""
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)
    
    # Check for request from current user to target
    outgoing = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=target_user
    ).first()
    
    # Check for request from target to current user
    incoming = FriendRequest.objects.filter(
        from_user=target_user,
        to_user=request.user
    ).first()
    
    # Determine overall status
    if outgoing and outgoing.status == 'accepted':
        return Response({"status": "friends", "type": "outgoing", "request_id": outgoing.id})
    elif incoming and incoming.status == 'accepted':
        return Response({"status": "friends", "type": "incoming", "request_id": incoming.id})
    elif outgoing and outgoing.status == 'pending':
        return Response({"status": "pending", "type": "outgoing", "request_id": outgoing.id})
    elif incoming and incoming.status == 'pending':
        return Response({"status": "pending", "type": "incoming", "request_id": incoming.id})
    else:
        return Response({"status": "none"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_friend_request(request, request_id):
    """Accept or reject a friend request"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id)
    except FriendRequest.DoesNotExist:
        return Response({"detail": "Friend request not found"}, status=404)
    
    if friend_request.to_user != request.user:
        return Response({"detail": "Not authorized to respond to this request"}, status=403)
    
    action = request.data.get('action', '').lower()
    
    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()
        
        # Create reverse request if it doesn't exist
        reverse = FriendRequest.objects.filter(
            from_user=friend_request.to_user,
            to_user=friend_request.from_user
        ).first()
        
        if not reverse:
            FriendRequest.objects.create(
                from_user=friend_request.to_user,
                to_user=friend_request.from_user,
                status='accepted'
            )
        
        return Response({"detail": "Friend request accepted", "status": "accepted"})
    
    elif action == 'reject':
        friend_request.status = 'rejected'
        friend_request.save()
        return Response({"detail": "Friend request rejected", "status": "rejected"})
    
    else:
        return Response({"detail": "Invalid action"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_friend_requests(request):
    """Get all pending friend requests for current user"""
    pending_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user')
    
    print(f"DEBUG: User {request.user.username} - Found {pending_requests.count()} pending requests")
    
    requests_data = []
    for freq in pending_requests:
        try:
            profile = freq.from_user.userprofile
            profile_pic = profile.profile_picture.url if profile.profile_picture else None
        except UserProfile.DoesNotExist:
            profile_pic = None
        
        requests_data.append({
            "id": freq.id,
            "from_user_id": freq.from_user.id,
            "username": freq.from_user.username,
            "first_name": freq.from_user.first_name,
            "last_name": freq.from_user.last_name,
            "profile_picture": profile_pic,
            "created_at": freq.created_at,
            "request_id": freq.id
        })
    
    return Response({"pending_requests": requests_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_friend_request(request, request_id):
    """Cancel an outgoing friend request"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id)
    except FriendRequest.DoesNotExist:
        return Response({"detail": "Friend request not found"}, status=404)
    
    # Only the sender can cancel their own request
    if friend_request.from_user != request.user:
        return Response({"detail": "Not authorized to cancel this request"}, status=403)
    
    # Only cancel pending requests
    if friend_request.status != 'pending':
        return Response({"detail": "Can only cancel pending requests"}, status=400)
    
    friend_request.delete()
    return Response({"detail": "Friend request cancelled", "status": "none"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_friends(request, user_id=None):
    """Get all friends of a user (both incoming and outgoing accepted requests)"""
    if user_id is None:
        target_user = request.user
    else:
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
    
    # Get all accepted friend requests involving this user
    outgoing_friends = FriendRequest.objects.filter(
        from_user=target_user,
        status='accepted'
    ).select_related('to_user')
    
    incoming_friends = FriendRequest.objects.filter(
        to_user=target_user,
        status='accepted'
    ).select_related('from_user')
    
    friends_data = []
    friends_ids = set()
    
    # Add friends from outgoing requests
    for freq in outgoing_friends:
        friend_user = freq.to_user
        if friend_user.id not in friends_ids:
            try:
                profile = friend_user.userprofile
                profile_pic = profile.profile_picture.url if profile.profile_picture else None
            except UserProfile.DoesNotExist:
                profile_pic = None
                profile = None
            
            if profile:  # Only add if profile exists
                # ✅ Use is_online field from profile, respecting privacy settings
                show_online_status = profile.show_online_status
                is_online = profile.is_online if show_online_status else False
                
                friends_data.append({
                    "id": profile.id,  # UserProfile ID (for messaging)
                    "user_id": friend_user.id,  # Also include User ID for reference
                    "username": friend_user.username,
                    "first_name": friend_user.first_name,
                    "last_name": friend_user.last_name,
                    "profile_picture": profile_pic,
                    "last_login": friend_user.last_login,
                    "is_online": is_online,
                    "show_online_status": show_online_status,
                })
                friends_ids.add(friend_user.id)
    
    # Add friends from incoming requests
    for freq in incoming_friends:
        friend_user = freq.from_user
        if friend_user.id not in friends_ids:
            try:
                profile = friend_user.userprofile
                profile_pic = profile.profile_picture.url if profile.profile_picture else None
            except UserProfile.DoesNotExist:
                profile_pic = None
                profile = None
            
            if profile:  # Only add if profile exists
                # ✅ Use is_online field from profile, respecting privacy settings
                show_online_status = profile.show_online_status
                is_online = profile.is_online if show_online_status else False
                
                friends_data.append({
                    "id": profile.id,  # UserProfile ID (for messaging)
                    "user_id": friend_user.id,  # Also include User ID for reference
                    "username": friend_user.username,
                    "first_name": friend_user.first_name,
                    "last_name": friend_user.last_name,
                    "profile_picture": profile_pic,
                    "last_login": friend_user.last_login,
                    "is_online": is_online,
                    "show_online_status": show_online_status,
                })
                friends_ids.add(friend_user.id)
    
    return Response({"friends": friends_data, "friends_count": len(friends_data)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfriend_user(request, user_id):
    """Remove a friend from current user's friend list"""
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)
    
    if target_user == request.user:
        return Response({"detail": "Cannot unfriend yourself"}, status=400)
    
    # Find and delete both directions of the friendship
    outgoing = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=target_user,
        status='accepted'
    ).first()
    
    incoming = FriendRequest.objects.filter(
        from_user=target_user,
        to_user=request.user,
        status='accepted'
    ).first()
    
    if not outgoing and not incoming:
        return Response({"detail": "Not friends with this user"}, status=400)
    
    # Delete both friend requests
    if outgoing:
        outgoing.delete()
    if incoming:
        incoming.delete()
    
    return Response({"detail": "Friend removed successfully", "status": "none"}, status=200)


# ═══════════════════════════════════════════════════════════════════════════
# ✅ KYC (Know Your Customer) Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def kyc_submission(request):
    """
    POST: User submits KYC form
    GET: User checks their KYC status
    """
    if request.method == 'POST':
        # Get data from request
        print("CONTENT TYPE:", request.content_type)
        print("POST:", request.POST)
        print("FILES:", request.FILES)
        print("citizenship:", request.POST.get("citizenship"))
        print("passport_no:", request.POST.get("passport_no"))
        print("passport_expiry:", request.POST.get("passport_expiry"))
        citizenship = request.POST.get('citizenship', '').strip()
        passport_no = request.POST.get('passport_no', '').strip()
        passport_expiry = request.POST.get('passport_expiry', '').strip()
        passport_photo = request.FILES.get('passport_photo')
        
        # Validate required fields
        if not citizenship:
            return Response({"success": False, "message": "Citizenship is required"}, status=400)
        if not passport_no:
            return Response({"success": False, "message": "Passport number is required"}, status=400)
        if not passport_expiry:
            return Response({"success": False, "message": "Passport expiry is required"}, status=400)
        if not passport_photo:
            return Response({"success": False, "message": "Passport photo is required"}, status=400)
        
        # Basic validation
        from datetime import datetime
        try:
            expiry_date = datetime.strptime(passport_expiry, "%Y-%m-%d").date()
            if expiry_date < datetime.now().date():
                return Response({"success": False, "message": "Passport has expired"}, status=400)
        except ValueError:
            return Response({"success": False, "message": "Invalid passport expiry date format"}, status=400)
        
        # Create or update KYCProfile
        kyc_profile, created = KYCProfile.objects.get_or_create(user=request.user)
        
        # Populate personal information from UserProfile
        try:
            user_profile = request.user.userprofile
            # Full name from user's first and last name
            kyc_profile.full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            # Date of birth from user profile
            if user_profile.dob:
                kyc_profile.date_of_birth = user_profile.dob
            # Address information from user profile
            if user_profile.address:
                kyc_profile.address = user_profile.address
            if user_profile.city:
                kyc_profile.city = user_profile.city
            if user_profile.country:
                kyc_profile.country = user_profile.country
        except UserProfile.DoesNotExist:
            pass
        
        # KYC-specific information
        kyc_profile.nationality = citizenship
        kyc_profile.id_number = passport_no
        kyc_profile.id_expiry_date = expiry_date
        if passport_photo:
            kyc_profile.id_document = passport_photo
        kyc_profile.status = 'pending'  # Set status to pending for admin review
        kyc_profile.save()
        
        return Response({
            "success": True,
            "message": "KYC form submitted successfully. Awaiting admin verification.",
            "kyc_status": kyc_profile.status
        }, status=200)
    
    elif request.method == 'GET':
        # Return user's KYC status and information
        try:
            kyc_profile = KYCProfile.objects.get(user=request.user)
            # Check if it's been actually submitted (has ID number)
            if not kyc_profile.id_number:
                return Response({
                    "kyc_status": "not_submitted",
                    "detail": "KYC form not yet submitted"
                }, status=200)
            
            return Response({
                "kyc_status": kyc_profile.status,
                # Personal Information
                "full_name": kyc_profile.full_name,
                "date_of_birth": str(kyc_profile.date_of_birth) if kyc_profile.date_of_birth else None,
                "nationality": kyc_profile.nationality,
                "id_number": kyc_profile.id_number,
                "citizenship": kyc_profile.nationality,  # For backwards compatibility
                "passport_no": kyc_profile.id_number,    # For backwards compatibility
                # Address Information
                "address": kyc_profile.address,
                "city": kyc_profile.city,
                "country": kyc_profile.country,
                # Documents
                "passport_expiry": str(kyc_profile.id_expiry_date) if kyc_profile.id_expiry_date else None,
                "id_document": kyc_profile.id_document.url if kyc_profile.id_document else None,
                "selfie": kyc_profile.selfie.url if kyc_profile.selfie else None,
                "proof_of_address": kyc_profile.proof_of_address.url if kyc_profile.proof_of_address else None,
                # Admin notes
                "notes": kyc_profile.notes,
            })
        except KYCProfile.DoesNotExist:
            return Response({
                "kyc_status": "not_submitted",
                "detail": "No KYC profile found"
            }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kyc_pending_list(request):
    """
    Admin endpoint: Get list of pending KYC submissions (only for staff)
    """
    if not request.user.is_staff:
        return Response({"detail": "Admin access required"}, status=403)
    
    # Only get KYCs that have been actually submitted (have id_number)
    pending_kycs = KYCProfile.objects.filter(status='pending').exclude(id_number__isnull=True, id_number='').select_related('user')
    
    results = []
    for kyc in pending_kycs:
        results.append({
            "id": kyc.id,
            "user_id": kyc.user.id,
            "username": kyc.user.username,
            "email": kyc.user.email,
            "first_name": kyc.user.first_name,
            "last_name": kyc.user.last_name,
            "full_name": kyc.full_name,
            "nationality": kyc.nationality,
            "id_number": kyc.id_number,
            "id_document": kyc.id_document.url if kyc.id_document else None,
            "selfie": kyc.selfie.url if kyc.selfie else None,
            "proof_of_address": kyc.proof_of_address.url if kyc.proof_of_address else None,
            "submitted_at": kyc.submitted_at.isoformat(),
        })
    
    return Response({
        "pending_count": len(results),
        "kyc_submissions": results
    })


class KYCAdminActionView(APIView):
    """
    Admin endpoint: Approve or reject KYC submissions
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, profile_id):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required"}, status=403)
        
        try:
            kyc_profile = KYCProfile.objects.get(id=profile_id)
        except KYCProfile.DoesNotExist:
            return Response({"detail": "KYC profile not found"}, status=404)
        
        action = request.data.get('action', '').lower()
        reason = request.data.get('reason', '')
        
        if action == 'approve':
            kyc_profile.status = 'approved'
            kyc_profile.notes = ''
            kyc_profile.reviewed_by = request.user
            from django.utils import timezone
            kyc_profile.reviewed_at = timezone.now()
            kyc_profile.save()
            return Response({
                "success": True,
                "message": f"KYC approved for {kyc_profile.user.username}",
                "new_status": kyc_profile.status
            })
        
        elif action == 'reject':
            if not reason:
                return Response({"success": False, "message": "Rejection reason is required"}, status=400)
            kyc_profile.status = 'rejected'
            kyc_profile.notes = reason
            kyc_profile.reviewed_by = request.user
            from django.utils import timezone
            kyc_profile.reviewed_at = timezone.now()
            kyc_profile.save()
            return Response({
                "success": True,
                "message": f"KYC rejected for {kyc_profile.user.username}",
                "new_status": kyc_profile.status
            })
        
        else:
            return Response({"detail": "Invalid action. Use 'approve' or 'reject'"}, status=400)