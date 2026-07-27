"""
DRF Serializers for all core models.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Document, Chat, Message, Note, Quiz, Flashcard


# ─────────────────────────────────────────────────────────────────────────────
# Auth Serializers
# ─────────────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'profile_picture')
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm password')
    name = serializers.CharField(write_only=True, required=False, default='')

    class Meta:
        model = User
        fields = ('email', 'name', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        name = validated_data.pop('name', '')
        validated_data.pop('password2')
        parts = name.split(' ', 1)
        first = parts[0] if parts else ''
        last = parts[1] if len(parts) > 1 else ''
        email = validated_data['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=first,
            last_name=last,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        attrs['user'] = user
        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    """Accepts a Google access token from the frontend and verifies it."""
    access_token = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    """Helper to return access + refresh tokens."""
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)

    @staticmethod
    def get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Document Serializers
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('id', 'title', 'file', 'file_url', 'uploaded_at', 'extracted_text', 'summary')
        read_only_fields = ('id', 'uploaded_at', 'extracted_text', 'summary', 'file_url')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Chat Serializers
# ─────────────────────────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'role', 'content', 'created_at')
        read_only_fields = ('id', 'created_at')


class ChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    active_document = DocumentSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = ('id', 'title', 'created_at', 'updated_at', 'messages', 'message_count', 'active_document')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing chats (no messages)."""
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ('id', 'title', 'created_at', 'updated_at', 'message_count')

    def get_message_count(self, obj):
        return obj.messages.count()


# ─────────────────────────────────────────────────────────────────────────────
# Note Serializers
# ─────────────────────────────────────────────────────────────────────────────

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('id', 'title', 'content', 'improved_content', 'is_pinned', 'created_at', 'updated_at')
        read_only_fields = ('id', 'improved_content', 'created_at', 'updated_at')


# ─────────────────────────────────────────────────────────────────────────────
# Quiz Serializers
# ─────────────────────────────────────────────────────────────────────────────

class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ('id', 'title', 'questions_json', 'score', 'total_questions', 'created_at')
        read_only_fields = ('id', 'questions_json', 'total_questions', 'created_at')


# ─────────────────────────────────────────────────────────────────────────────
# Flashcard Serializers
# ─────────────────────────────────────────────────────────────────────────────

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ('id', 'deck_title', 'front', 'back', 'created_at')
        read_only_fields = ('id', 'created_at')
