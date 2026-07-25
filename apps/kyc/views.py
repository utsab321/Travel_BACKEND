from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .models import KYCProfile
from .serializers import KYCProfileSerializer, KYCReviewSerializer
from .permissions import IsOwnerOrStaff


class KYCListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = KYCProfileSerializer

   

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return KYCProfile.objects.all()
        return KYCProfile.objects.filter(user=user)

    def perform_create(self, serializer):
        # Prevent multiple KYC submissions per user
        if KYCProfile.objects.filter(user=self.request.user).exists():
            raise ValidationError({"detail": "KYC profile already exists for this user."})
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

class KYCDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    serializer_class = KYCProfileSerializer
    queryset = KYCProfile.objects.all()
    lookup_field = 'id'


class KYCReviewView(generics.UpdateAPIView):
    """Staff only - review and approve/reject KYC"""
    permission_classes = [IsAuthenticated]  # Add IsAdminUser if you want stricter
    serializer_class = KYCReviewSerializer
    queryset = KYCProfile.objects.all()
    lookup_field = 'id'

    def perform_update(self, serializer):
        serializer.save(reviewed_by=self.request.user, reviewed_at=timezone.now())  # add from django.utils import timezone