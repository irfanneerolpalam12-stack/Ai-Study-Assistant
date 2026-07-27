"""
Database models for the AI Study Assistant.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


# ─────────────────────────────────────────────────────────────────────────────
# Custom User
# ─────────────────────────────────────────────────────────────────────────────

class User(AbstractUser):
    """Extended user model using email as the primary identifier."""
    email = models.EmailField(unique=True)
    profile_picture = models.URLField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


# ─────────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────────

class Document(models.Model):
    """Uploaded study document with extracted text for RAG."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} ({self.user.email})'


# ─────────────────────────────────────────────────────────────────────────────
# Chat & Messages
# ─────────────────────────────────────────────────────────────────────────────

class Chat(models.Model):
    """A conversation session."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
    title = models.CharField(max_length=255, default='New Study Session')
    active_document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL, related_name='active_in_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} — {self.user.email}'


class Message(models.Model):
    """A single turn in a chat session."""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content[:60]}'


# ─────────────────────────────────────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────────────────────────────────────

class Note(models.Model):
    """User study note, optionally improved by AI."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    content = models.TextField()
    improved_content = models.TextField(blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return f'{self.title} ({self.user.email})'


# ─────────────────────────────────────────────────────────────────────────────
# Quizzes
# ─────────────────────────────────────────────────────────────────────────────

class Quiz(models.Model):
    """AI-generated MCQ quiz."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    # JSON structure: [{"question": "...", "options": ["A","B","C","D"], "answer": "A", "explanation": "..."}]
    questions_json = models.JSONField(default=list)
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f'{self.title} ({self.user.email})'


# ─────────────────────────────────────────────────────────────────────────────
# Flashcards
# ─────────────────────────────────────────────────────────────────────────────

class Flashcard(models.Model):
    """A single study flashcard."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    deck_title = models.CharField(max_length=255, default='My Deck')
    front = models.TextField()
    back = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.front[:60]} (deck: {self.deck_title})'
