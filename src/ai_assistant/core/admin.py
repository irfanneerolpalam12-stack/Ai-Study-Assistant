"""
Django admin registrations for all core models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Document, Chat, Message, Note, Quiz, Flashcard


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'username')
    ordering = ('email',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('profile_picture',)}),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'uploaded_at')
    search_fields = ('title', 'user__email')
    list_filter = ('uploaded_at',)
    readonly_fields = ('extracted_text', 'summary', 'uploaded_at')


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'user__email')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'role', 'created_at')
    list_filter = ('role',)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_pinned', 'updated_at')
    list_filter = ('is_pinned',)
    search_fields = ('title', 'user__email')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'total_questions', 'score', 'created_at')
    search_fields = ('title', 'user__email')


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('deck_title', 'user', 'created_at')
    search_fields = ('deck_title', 'user__email')
