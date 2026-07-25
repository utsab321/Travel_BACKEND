from django.urls import path
from .views_api import (
    match_users, search_users, get_user_profile, calculate_similarity,
    send_friend_request, get_friend_request_status, respond_friend_request,
    get_pending_friend_requests, cancel_friend_request, get_user_friends,
    get_user_profile_by_username,
    unfriend_user, kyc_submission, kyc_pending_list, KYCAdminActionView, trip_user_suggestions
)
from . import views_api
from . import views

urlpatterns = [
    path("login/", views.frontend_login, name="frontend-login"),
    path("register/", views.frontend_register, name="frontend-register"),
    path("matches/", match_users),
    path("search/", search_users, name="search-users"),
    path("suggestions/", trip_user_suggestions, name="trip-user-suggestions"),
    path("user-profile/<int:user_id>/", get_user_profile, name="get-user-profile"),
    path("user-profile/username/<str:username>/", get_user_profile_by_username, name="get-user-profile-by-username"),
    path("similarity/<int:user_id>/", calculate_similarity, name="calculate-similarity"),
    path("friend-request/send/<int:user_id>/", send_friend_request, name="send-friend-request"),
    path("friend-request/status/<int:user_id>/", get_friend_request_status, name="friend-request-status"),
    path("friend-request/<int:request_id>/respond/", respond_friend_request, name="respond-friend-request"),
    path("friend-request/<int:request_id>/cancel/", cancel_friend_request, name="cancel-friend-request"),
    path("unfriend/<int:user_id>/", unfriend_user, name="unfriend-user"),
    path("friend-requests/pending/", get_pending_friend_requests, name="pending-friend-requests"),
    path("friends/", get_user_friends, name="user-friends"),
    path("friends/<int:user_id>/", get_user_friends, name="user-friends-by-id"),
    path("me/", views.me_view, name="me"),
    path("me/logout/", views.logout_view, name="logout"),
    path("me/change-password/", views.change_password_view, name="change-password"),
    path("me/delete/", views.delete_account_view, name="delete-account"),
    path("me/preferences/", views.user_preferences_view, name="user-preferences"),
    path("me/security-questions/", views.save_security_questions, name="save-security-questions"),
    path("interests/", views.get_interests, name="get-interests"),
    path("constraint-tags/", views.get_constraint_tags, name="get-constraint-tags"),
    path("profile/update/", views.update_profile_view, name="profile-update"),
    path('match/<int:match_id>/action/', views_api.MatchActionView.as_view(), name='match-action'),
    
    # ✅ Password Recovery Endpoints
    path("security-questions/", views.get_security_questions, name="get-security-questions"),
    path("forgot-password/step1/", views.forgot_password_step1, name="forgot-password-step1"),
    path("forgot-password/step2/", views.forgot_password_step2, name="forgot-password-step2"),
    
    # Admin password reset endpoints
    path("admin/users/", views.admin_users_list, name="admin-users-list"),
    path("admin/reset-password/", views.admin_reset_password, name="admin-reset-password"),
    
    # ✅ KYC Endpoints
    path("kyc/", kyc_submission, name="kyc-submission"),
    path("kyc/pending/", kyc_pending_list, name="kyc-pending-list"),
    path("kyc/<int:profile_id>/action/", KYCAdminActionView.as_view(), name="kyc-admin-action"),
]