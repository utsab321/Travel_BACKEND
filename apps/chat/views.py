from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import ChatMessage, Message
from apps.users.models import UserProfile
from apps.trips.models import City, Destination
from apps.kyc.permissions import IsKYCApproved


class ChatMessageSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'user', 'username', 'message', 'response', 'created_at']
        read_only_fields = ['id', 'user', 'response', 'created_at', 'username']
    
    def get_username(self, obj):
        return obj.user.user.username if obj.user else None


class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]  # Chat doesn't require KYC approval
    
    def get_queryset(self):
        try:
            user_profile = UserProfile.objects.get(user=self.request.user)
            return ChatMessage.objects.filter(user=user_profile).order_by('-created_at')
        except UserProfile.DoesNotExist:
            return ChatMessage.objects.none()

    def create(self, request, *args, **kwargs):
        """Override create to handle chat messages"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            message = request.data.get('message', '').strip()
            
            if not message:
                return Response(
                    {'error': 'Message cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user profile
            try:
                user_profile = UserProfile.objects.get(user=request.user)
            except UserProfile.DoesNotExist:
                logger.error(f"UserProfile not found for user {request.user}")
                return Response(
                    {'error': 'User profile not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate response (now returns structured data)
            response_data = self.generate_response(message)
            response_text = response_data.get('response', '')
            
            # Save chat message
            chat_msg = ChatMessage.objects.create(
                user=user_profile,
                message=message,
                response=response_text
            )
            
            serializer = self.get_serializer(chat_msg)
            
            # Return response with additional metadata for frontend
            return Response({
                **serializer.data,
                'response_metadata': {
                    'type': response_data.get('type', 'default'),
                    'links': response_data.get('links', [])
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error in chat endpoint: {str(e)}")
            return Response(
                {'error': f'Server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_response(self, message):
        """Generate a response based on the message with optional clickable keywords"""
        message_lower = message.lower()
        
        # Check if user specifically asking for map
        map_specific_keywords = ['map', 'explore', 'show map', 'where is the map', 'where\'s the map']
        is_asking_for_map = any(keyword in message_lower for keyword in map_specific_keywords)
        
        # Keywords that indicate destination queries (not just map)
        destination_keywords = ['destination', 'location', 'visit', 'go to', 'where is']
        is_destination_query = any(keyword in message_lower for keyword in destination_keywords)
        
        # Check if user is asking about specific destinations or cities
        destinations = Destination.objects.all()
        cities = City.objects.all()
        
        mentioned_destinations = []
        mentioned_cities = []
        
        # Check for mentioned destinations
        for dest in destinations:
            if dest.name.lower() in message_lower:
                mentioned_destinations.append(dest)
        
        # Check for mentioned cities
        for city in cities:
            if city.name.lower() in message_lower:
                mentioned_cities.append(city)
        
        # If user specifically asks for map, redirect to Explore page
        if is_asking_for_map and not mentioned_destinations and not mentioned_cities:
            return {
                'response': "Let me take you to the map where you can explore all destinations! Click below to see the interactive map.",
                'type': 'map',
                'links': [
                    {'keyword': 'map', 'route': '/explore', 'type': 'action'}
                ]
            }
        
        # If user asks about specific destinations/locations, provide those
        if mentioned_destinations or mentioned_cities:
            response_data = {
                'response': '',
                'type': 'destination',
                'links': []
            }
            
            if mentioned_destinations:
                dest_names = ', '.join([f"**{d.name}**" for d in mentioned_destinations])
                response_data['response'] = (
                    f"Great choice! You're interested in {dest_names}. "
                    f"Click on any location to view more details and explore trips!"
                )
                for dest in mentioned_destinations:
                    response_data['links'].append({
                        'keyword': dest.name,
                        'route': f'/destination/{dest.id}',
                        'type': 'destination'
                    })
            
            if mentioned_cities:
                city_names = ', '.join([f"**{c.name}**" for c in mentioned_cities])
                response_data['response'] += (
                    f"\n\nYou can also explore all trips in {city_names}. "
                    f"Click on any city to see available trips!"
                )
                for city in mentioned_cities:
                    response_data['links'].append({
                        'keyword': city.name,
                        'route': f'/city/{city.id}',
                        'type': 'city'
                    })
            
            # Add link to explore all destinations
            response_data['response'] += "\n\nOr visit the **map** to see all destinations!"
            response_data['links'].append({
                'keyword': 'map',
                'route': '/explore',
                'type': 'action'
            })
            
            return response_data
        
        # Greetings
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return {
                'response': "Hello! How can I assist you with your travel plans today? You can ask me about destinations, create a trip, or explore the **map**.",
                'type': 'greeting',
                'links': [
                    {'keyword': 'map', 'route': '/explore', 'type': 'action'}
                ]
            }
        
        # Trip planning
        if any(word in message_lower for word in ['trip', 'plan', 'travel', 'create']):
            return {
                'response': "I can help you plan your trip! You can **create a new trip**, **browse destinations**, or get suggestions. What would you like to do?",
                'type': 'trip',
                'links': [
                    {'keyword': 'create a new trip', 'route': '/create-trip', 'type': 'action'},
                    {'keyword': 'browse destinations', 'route': '/explore', 'type': 'action'}
                ]
            }
        
        # Expense tracking
        if any(word in message_lower for word in ['expense', 'cost', 'budget', 'price']):
            return {
                'response': "You can track expenses for your trips on the **Dashboard**. Would you like help managing your trip budget?",
                'type': 'expense',
                'links': [
                    {'keyword': 'Dashboard', 'route': '/dashboard', 'type': 'action'}
                ]
            }
        
        # Thanks
        if any(word in message_lower for word in ['thank', 'thanks']):
            return {
                'response': "You're welcome! Feel free to ask me anything about your travels.",
                'type': 'thanks',
                'links': []
            }
        
        # Default response
        return {
            'response': (
                "I'm here to help with travel planning! You can ask me about **trips**, **destinations**, "
                "**expenses**, or view the **map**. What can I help you with?"
            ),
            'type': 'default',
            'links': [
                {'keyword': 'map', 'route': '/explore', 'type': 'action'},
                {'keyword': 'trips', 'route': '/dashboard', 'type': 'action'},
                {'keyword': 'destinations', 'route': '/explore', 'type': 'action'}
            ]
        }


# ═══════════════════════════════════════════════════════════════
# DIRECT MESSAGING (Friend-to-Friend & Group Chat)
# ═══════════════════════════════════════════════════════════════

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    trip_name = serializers.SerializerMethodField()
    isSent = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'receiver', 'receiver_name', 'trip', 'trip_name', 'content', 'timestamp', 'isSent', 'is_system', 'is_read', 'profile_picture']
        read_only_fields = ['sender', 'receiver', 'trip', 'timestamp', 'is_system']
    
    def get_sender_name(self, obj):
        return obj.sender.user.get_full_name() or obj.sender.user.username if obj.sender else None
    
    def get_receiver_name(self, obj):
        return obj.receiver.user.get_full_name() or obj.receiver.user.username if obj.receiver else None
    
    def get_trip_name(self, obj):
        return obj.trip.title if obj.trip else None
    
    def get_profile_picture(self, obj):
        """Get sender's profile picture URL"""
        if obj.sender and obj.sender.profile_picture:
            try:
                return obj.sender.profile_picture.url
            except ValueError:
                return None
        return None
        
    
    def get_isSent(self, obj):
        request = self.context.get('request')
        if request:
            return obj.sender.user == request.user
        return False


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            user = self.request.user
            user_profile = UserProfile.objects.get(user=user)
            # Get messages where user is sender or receiver
            return Message.objects.filter(
                Q(sender=user_profile) | Q(receiver=user_profile)
            ).order_by('timestamp')
        except UserProfile.DoesNotExist:
            return Message.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Send a message (direct or group)"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Message create request. Data: {request.data}")
            logger.info(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
            
            # Check if user has approved KYC
            from apps.kyc.models import KYCProfile
            try:
                kyc_profile = request.user.kyc_profile
                logger.info(f"KYC Status: {kyc_profile.status}")
                if kyc_profile.status != 'approved':
                    logger.warning(f"KYC not approved for user {request.user}")
                    return Response({
                        'error': 'KYC approval required to send messages',
                        'kyc_status': kyc_profile.status
                    }, status=status.HTTP_403_FORBIDDEN)
            except KYCProfile.DoesNotExist:
                logger.warning(f"No KYC profile for user {request.user}")
                return Response({
                    'error': 'You must complete and get KYC approval before sending messages',
                    'kyc_status': 'not_submitted'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get sender profile
            try:
                sender_profile = UserProfile.objects.get(user=request.user)
                logger.info(f"Sender profile found: {sender_profile}")
            except UserProfile.DoesNotExist:
                logger.error(f"UserProfile not found for user {request.user}")
                return Response({
                    'error': 'User profile not found. Please complete your profile setup.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            content = request.data.get('content', '').strip()
            logger.info(f"Message content: {content}")
            
            if not content:
                logger.warning("Empty message content")
                return Response(
                    {'error': 'Message content cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if this is a system message
            is_system = request.data.get('is_system', False)
            logger.info(f"Is system message: {is_system}")
            
            # Determine if it's a direct message or group message
            receiver_id = request.data.get('receiver_id')
            trip_id = request.data.get('trip_id')
            logger.info(f"Receiver ID: {receiver_id}, Trip ID: {trip_id}")
            
            if receiver_id:
                # Direct message
                try:
                    receiver_id = int(receiver_id)
                    receiver = UserProfile.objects.get(id=receiver_id)
                    logger.info(f"Receiver found: {receiver}")
                except (ValueError, UserProfile.DoesNotExist) as e:
                    logger.error(f"Receiver lookup failed: {e}")
                    return Response(
                        {'error': 'Receiver not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                message = Message.objects.create(
                    sender=sender_profile,
                    receiver=receiver,
                    content=content,
                    is_system=is_system
                )
                logger.info(f"Direct message created: {message}")
            elif trip_id:
                # Group message
                from apps.trips.models import Trip
                try:
                    trip_id = int(trip_id)
                    logger.info(f"Looking for trip with ID: {trip_id}")
                    trip = Trip.objects.get(id=trip_id)
                    logger.info(f"Trip found: {trip}")
                    # Check if user is a member of the trip
                    is_member = sender_profile in trip.participants.all()
                    logger.info(f"Is sender member of trip: {is_member}")
                    if not is_member:
                        logger.warning(f"User {sender_profile} is not member of trip {trip}")
                        return Response(
                            {'error': 'You are not a member of this trip'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except ValueError as e:
                    logger.error(f"Invalid trip ID format: {e}")
                    return Response(
                        {'error': 'Invalid trip ID format'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Trip.DoesNotExist as e:
                    logger.error(f"Trip not found: {e}")
                    return Response(
                        {'error': 'Trip not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                message = Message.objects.create(
                    sender=sender_profile,
                    trip=trip,
                    content=content,
                    is_system=is_system
                )
                logger.info(f"Group message created: {message}")
            else:
                logger.warning("Neither receiver_id nor trip_id provided")
                return Response(
                    {'error': 'Either receiver_id or trip_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Serializing message: {message}")
            serializer = self.get_serializer(message, context={'request': request})
            logger.info(f"Serialized data: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            import traceback
            error_msg = f"Error in message creation: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg)
            return Response({
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def direct_messages(self, request):
        """Get direct messages with a specific user"""
        recipient_id = request.query_params.get('recipient_id')
        if not recipient_id:
            return Response(
                {'error': 'recipient_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recipient = UserProfile.objects.get(id=recipient_id)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Recipient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Get all messages between these two users
        messages = Message.objects.filter(
            Q(sender=user_profile, receiver=recipient) |
            Q(sender=recipient, receiver=user_profile),
            trip__isnull=True
        ).order_by('timestamp')
        
        serializer = self.get_serializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def group_messages(self, request):
        """Get group messages for a specific trip"""
        import logging
        logger = logging.getLogger(__name__)
        
        trip_id = request.query_params.get('trip_id')
        logger.info(f"group_messages called with trip_id: {trip_id}")
        
        if not trip_id:
            return Response(
                {'error': 'trip_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.trips.models import Trip
        try:
            trip_id = int(trip_id)
            trip = Trip.objects.get(id=trip_id)
            logger.info(f"Trip found: {trip}")
        except (ValueError, Trip.DoesNotExist) as e:
            logger.error(f"Trip lookup failed: {e}")
            return Response(
                {'error': f'Trip not found: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all messages for this trip
        messages = Message.objects.filter(trip=trip).order_by('timestamp')
        logger.info(f"Found {messages.count()} messages for trip")
        
        serializer = self.get_serializer(messages, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread messages for the current user from friends and groups"""
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            from apps.users.models import FriendRequest
            
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            # Get unread DIRECT messages where:
            # 1. User is the receiver
            # 2. Sender and receiver are accepted friends
            direct_unread = Message.objects.filter(
                receiver=user_profile,
                trip__isnull=True,  # Direct message (no trip)
                is_read=False,
                is_system=False
            ).exclude(sender=user_profile)  # Exclude own messages
            
            # Filter to only show messages from accepted friends
            friend_direct_unread = []
            for msg in direct_unread:
                # Check if sender and receiver are friends (accepted in both directions)
                is_friend = FriendRequest.objects.filter(
                    from_user=msg.sender.user,
                    to_user=request.user,
                    status='accepted'
                ).exists() or FriendRequest.objects.filter(
                    from_user=request.user,
                    to_user=msg.sender.user,
                    status='accepted'
                ).exists()
                
                if is_friend:
                    friend_direct_unread.append(msg.id)
            
            # Get unread GROUP messages where user is a participant
            group_unread = Message.objects.filter(
                trip__participants=user_profile,
                trip__isnull=False,  # Group message (has trip)
                is_read=False,
                is_system=False
            ).exclude(sender=user_profile).distinct()
            
            # Combine friendly direct messages and group messages
            all_unread_ids = friend_direct_unread
            unread_messages = Message.objects.filter(
                Q(id__in=all_unread_ids) | Q(id__in=group_unread.values_list('id', flat=True))
            ).distinct().order_by('-timestamp')
            
            # Also include recently read messages (within 24 hours) for seamless notification flow
            # For direct: only from friends
            # For groups: only from trips user is in
            recently_read_direct = Message.objects.filter(
                receiver=user_profile,
                trip__isnull=True,
                is_read=True,
                is_read_at__gte=cutoff_time,
                is_system=False
            ).exclude(sender=user_profile)
            
            recently_read_direct_ids = []
            for msg in recently_read_direct:
                is_friend = FriendRequest.objects.filter(
                    from_user=msg.sender.user,
                    to_user=request.user,
                    status='accepted'
                ).exists() or FriendRequest.objects.filter(
                    from_user=request.user,
                    to_user=msg.sender.user,
                    status='accepted'
                ).exists()
                
                if is_friend:
                    recently_read_direct_ids.append(msg.id)
            
            recently_read_group = Message.objects.filter(
                trip__participants=user_profile,
                trip__isnull=False,
                is_read=True,
                is_read_at__gte=cutoff_time,
                is_system=False
            ).exclude(sender=user_profile).distinct()
            
            # Combine all notifications
            all_notification_ids = all_unread_ids + recently_read_direct_ids + list(group_unread.values_list('id', flat=True)) + list(recently_read_group.values_list('id', flat=True))
            all_notifications = Message.objects.filter(
                id__in=all_notification_ids
            ).distinct().order_by('-timestamp')
            
            serializer = self.get_serializer(all_notifications, many=True, context={'request': request})
            return Response({
                'results': serializer.data,
                'count': len(serializer.data)
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark a message as read and set the read timestamp"""
        try:
            message = Message.objects.get(id=pk)
            message.is_read = True
            message.is_read_at = timezone.now()
            message.save()
            serializer = self.get_serializer(message, context={'request': request})
            return Response(serializer.data)
        except Message.DoesNotExist:
            return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)

