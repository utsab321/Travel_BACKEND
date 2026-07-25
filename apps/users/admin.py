from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Q
from .models import UserProfile, Match, UserLoginHistory, Interest, ConstraintTag
from apps.kyc.models import KYCProfile, KYCStatus


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'user_count')
    list_filter = ('category',)
    search_fields = ('name',)

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = "Users with this interest"


@admin.register(ConstraintTag)
class ConstraintTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'user_count')
    list_filter = ('category',)
    search_fields = ('name',)

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = "Users with this tag"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'full_name', 'email', 'phone', 'country', 'created_at')
    list_filter   = ('country',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('preview_profile_photo', 'preview_passport_photo', 'created_at')
    filter_horizontal = ('interests', 'constraint_tags')

    fieldsets = (
        ('👤 Account', {
            'fields': ('user',)
        }),
        ('📸 Photos', {
            'fields': ('preview_profile_photo', 'profile_picture', 'preview_passport_photo', 'passport_photo')
        }),
        ('📋 Personal Info', {
            'fields': ('dob', 'gender', 'citizenship', 'passport_no', 'passport_expiry')
        }),
        ('📬 Contact', {
            'fields': ('phone', 'address', 'city', 'country', 'zip_code')
        }),
        ('✈️ Travel Preferences', {
            'fields': ('bio', 'location', 'travel_style', 'pace', 'accomodation_preference',
                       'budget_level', 'adventure_level', 'social_level', 'interests')
        }),
        ('🏷️ Matching Constraints', {
            'fields': ('constraint_tags', 'min_match_age', 'max_match_age'),
            'description': 'These settings ensure compatible matches. Strict tags must match for pairing.'
        }),
    )

    def full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or "—"
    full_name.short_description = "Name"

    def email(self, obj):
        return obj.user.email
    email.short_description = "Email"

    def created_at(self, obj):
        return obj.user.date_joined.strftime("%b %d, %Y")
    created_at.short_description = "Registered"

    def preview_profile_photo(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="height:120px;width:120px;object-fit:cover;border-radius:50%;border:2px solid #ccc" />',
                obj.profile_picture.url
            )
        return "No photo uploaded"
    preview_profile_photo.short_description = "Profile Photo Preview"

    def preview_passport_photo(self, obj):
        if obj.passport_photo:
            return format_html(
                '<img src="{}" style="height:160px;max-width:280px;object-fit:cover;border-radius:8px;border:2px solid #ccc" />',
                obj.passport_photo.url
            )
        return "No passport photo uploaded"
    preview_passport_photo.short_description = "Passport Photo Preview"


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'similarity_score', 'status', 'created_at')
    list_filter  = ('status',)


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address')
    readonly_fields = ('user', 'login_time', 'ip_address', 'user_agent')


@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'status_badge', 'full_name', 'submitted_at', 'days_pending', 'action_buttons']
    list_filter = ['status', 'submitted_at', 'nationality']
    search_fields = ['user__email', 'user__username', 'full_name', 'id_number']
    readonly_fields = ['submitted_at', 'reviewed_at', 'document_preview', 'user_email']
    ordering = ['-reviewed_at', '-submitted_at']
    date_hierarchy = 'submitted_at'

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
        path(
            "<int:pk>/approve/",
            self.admin_site.admin_view(self.approve_view),
            name="kyc_approve",
        ),
             path(
            "<int:pk>/reject/",
            self.admin_site.admin_view(self.reject_view),
            name="kyc_reject",
        ),
        ]
        return custom_urls + urls
    
    def approve_view(self, request, pk):
        try:
            obj = KYCProfile.objects.get(pk=pk)

            obj.status = KYCStatus.APPROVED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()

            self.message_user(
                request,
                f"KYC approved for {obj.user.email}",
                level=messages.SUCCESS,
            )

        except KYCProfile.DoesNotExist:
            self.message_user(
            request,
            "KYC profile not found.",
            level=messages.ERROR,
        )

        return redirect(request.META.get("HTTP_REFERER", "../"))

    def approve_view(self, request, pk):
        try:
            obj = KYCProfile.objects.get(pk=pk)

            obj.status = KYCStatus.APPROVED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()

            self.message_user(
                request,
                f"KYC approved for {obj.user.email}",
                level=messages.SUCCESS,
            )

        except KYCProfile.DoesNotExist:
            self.message_user(
            request,
            "KYC profile not found.",
            level=messages.ERROR,
         )

        return redirect(request.META.get("HTTP_REFERER", "../"))

    def reject_view(self, request, pk):
        try:
            obj = KYCProfile.objects.get(pk=pk)

            obj.status = KYCStatus.REJECTED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()

            self.message_user(
                request,
                f"KYC rejected for {obj.user.email}",
                level=messages.WARNING,
            )

        except KYCProfile.DoesNotExist:
            self.message_user(
                request,
                "KYC profile not found.",
                level=messages.ERROR,
            )

        return redirect(request.META.get("HTTP_REFERER", "../"))
    
    def get_queryset(self, request):
        """Only show KYC profiles that have been actually submitted (have ID number)"""
        qs = super().get_queryset(request)
        # Exclude KYC profiles with no id_number (not submitted)
        return qs.exclude(Q(id_number__isnull=True) | Q(id_number=''))
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'user_email', 'status')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'date_of_birth', 'nationality', 'id_number')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'country', 'proof_of_address_type', 'proof_of_address_date')
        }),
        ('Documents', {
            'fields': ('id_document', 'selfie', 'proof_of_address', 'document_preview'),
            'description': 'View uploaded documents'
        }),
        ('Review Information', {
            'fields': ('notes', 'submitted_at', 'reviewed_by', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        """Display user with email link"""
        return f"{obj.user.username} ({obj.user.email})"
    user_display.short_description = "User"
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            KYCStatus.APPROVED: '#2ecc71',  # green
            KYCStatus.REJECTED: '#e74c3c',  # red
            KYCStatus.PENDING: '#f39c12',   # orange
            KYCStatus.UNDER_REVIEW: '#3498db',  # blue
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def days_pending(self, obj):
        """Show how many days the KYC has been pending"""
        from django.utils import timezone
        from datetime import timedelta
        
        days = (timezone.now() - obj.submitted_at).days
        if days == 0:
            return mark_safe('<span style="color: #e74c3c; font-weight: bold;">Today</span>')
        elif days == 1:
            return mark_safe('<span style="color: #e67e22;">1 day ago</span>')
        elif days <= 3:
            return format_html('<span style="color: #e67e22;">{} days ago</span>', days)
        else:
            return format_html('<span style="color: #e74c3c; font-weight: bold;">{} days ago ⚠️</span>', days)
    days_pending.short_description = "Pending Since"
    
    def action_buttons(self, obj):
        if obj.status == KYCStatus.APPROVED:
            return format_html(
            '<span style="color:green;font-weight:bold;">✓ APPROVED</span>'
        )

        if obj.status == KYCStatus.REJECTED:
            return format_html(
            '<span style="color:red;font-weight:bold;">✗ REJECTED</span>'
        )

        approve_url = reverse(
        "admin:kyc_approve",
        args=[object.pk],
    )

        reject_url = reverse(
        "admin:kyc_reject",
        args=[object.pk],
    )

        return format_html(
        '<a class="button" style="background:#27ae60;color:white;padding:5px 10px;border-radius:4px;text-decoration:none;margin-right:5px;" href="{}">Approve</a>'
        '<a class="button" style="background:#e74c3c;color:white;padding:5px 10px;border-radius:4px;text-decoration:none;" href="{}">Reject</a>',
        approve_url,
        reject_url,
    )

        action_buttons.short_description = "Actions"
    
    def document_preview(self, obj):
        """Preview documents inline"""
        html = '<div style="margin: 10px 0;">'
        
        if obj.id_document:
            html += f'<div style="margin-bottom: 15px;"><strong>ID Document:</strong><br>'
            html += f'<a href="{obj.id_document.url}" target="_blank">📄 View ID Document</a></div>'
        
        if obj.selfie:
            html += f'<div style="margin-bottom: 15px;"><strong>Selfie:</strong><br>'
            html += f'<a href="{obj.selfie.url}" target="_blank">📷 View Selfie</a></div>'
        
        if obj.proof_of_address:
            html += f'<div style="margin-bottom: 15px;"><strong>Proof of Address:</strong><br>'
            html += f'<a href="{obj.proof_of_address.url}" target="_blank">🏠 View Proof of Address</a></div>'
        
        if not any([obj.id_document, obj.selfie, obj.proof_of_address]):
            html += '<p style="color: #e74c3c;">No documents uploaded</p>'
        
        html += '</div>'
        return mark_safe(html)
    document_preview.short_description = "Document Preview"
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = "Email"
    
    actions = ['approve_kyc', 'reject_kyc', 'mark_under_review']
    
    def approve_kyc(self, request, queryset):
        """Bulk approve KYC"""
        updated = queryset.update(status=KYCStatus.APPROVED, reviewed_by=request.user)
        self.message_user(request, f'{updated} KYC profile(s) approved.')
    approve_kyc.short_description = "✓ Approve selected KYC"
    
    def reject_kyc(self, request, queryset):
        """Bulk reject KYC"""
        updated = queryset.update(status=KYCStatus.REJECTED, reviewed_by=request.user)
        self.message_user(request, f'{updated} KYC profile(s) rejected.')
    reject_kyc.short_description = "✗ Reject selected KYC"
    
    def mark_under_review(self, request, queryset):
        """Mark as under review"""
        updated = queryset.update(status=KYCStatus.UNDER_REVIEW, reviewed_by=request.user)
        self.message_user(request, f'{updated} KYC profile(s) marked as under review.')
    mark_under_review.short_description = "⏳ Mark as Under Review"