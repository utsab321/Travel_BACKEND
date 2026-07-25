from django.contrib import admin
from .models import KYCProfile
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Q

# KYC admin is now registered in apps.users.admin for better organization
# This file is kept for reference