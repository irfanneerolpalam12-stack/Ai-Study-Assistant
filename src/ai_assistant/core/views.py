"""
API Views for the AI Study Assistant.
"""

from __future__ import annotations

import os
import threading

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
import traceback
import logging

logger = logging.getLogger(__name__)

from .models import User, Document, Chat, Message, Note, Quiz, Flashcard
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, GoogleAuthSerializer,
    TokenPairSerializer, DocumentSerializer, ChatSerializer, ChatListSerializer,
    MessageSerializer, NoteSerializer, QuizSerializer, FlashcardSerializer,
)
from . import ai_services


# ─────────────────────────────────────────────────────────────────────────────
# Auth Views
# ─────────────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """POST /api/auth/register/ — Create a new user and return JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(TokenPairSerializer.get_tokens(user), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """POST /api/auth/login/ — Authenticate and return JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            return Response(TokenPairSerializer.get_tokens(user))
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class GoogleAuthView(APIView):
    """POST /api/auth/google/ — Verify Google access token and return JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        access_token = serializer.validated_data['access_token']
        client_id = settings.GOOGLE_CLIENT_ID

        if not client_id:
            return Response(
                {'error': 'Google OAuth is not configured on this server.'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        try:
            import requests as py_requests
            
            # Query Google's user info API
            google_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}"
            response = py_requests.get(google_url)
            
            if not response.ok:
                logger.error(f"Google userinfo failed: {response.text}")
                return Response(
                    {"error": "Invalid or expired Google access token."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            google_data = response.json()

            email = google_data.get('email')
            name = google_data.get('name', '')
            picture = google_data.get('picture', '')

            if not email:
                return Response(
                    {"error": "Could not retrieve email from Google profile."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': name.split(' ', 1)[0] if name else '',
                    'last_name': name.split(' ', 1)[1] if ' ' in name else '',
                    'profile_picture': picture,
                },
            )
            if not created and picture and not user.profile_picture:
                user.profile_picture = picture
                user.save(update_fields=['profile_picture'])

            return Response(TokenPairSerializer.get_tokens(user))

        except ValueError as e:
            return Response({'error': f'Invalid Google token: {e}'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/profile/ — Retrieve or update user profile."""
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# ─────────────────────────────────────────────────────────────────────────────
# Document Views
# ─────────────────────────────────────────────────────────────────────────────

def _summarize_document_async(document: Document):
    """Background thread: auto-generate summary AFTER text is already extracted."""
    try:
        if not document.extracted_text:
            return
        summary_data = ai_services.summarize_document(document.extracted_text)
        summary_lines = ['## Key Points\n']
        for kp in summary_data.get('key_points', []):
            summary_lines.append(f'- {kp}')
        summary_lines.append(f'\n## Summary\n{summary_data.get("executive_summary", "")}')
        document.summary = '\n'.join(summary_lines)
        document.save(update_fields=['summary'])
        print(f"✅ SUMMARY: Auto-summary complete for doc_{document.id}.")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Summary generation error: {e}')


class DocumentListCreateView(generics.ListCreateAPIView):
    """GET /api/documents/ — List documents. POST — Upload new document."""
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        try:
            chat_id = request.data.get('chat_id')
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            doc = serializer.save(user=self.request.user)

            # ── SYNCHRONOUS: Extract text + ingest into ChromaDB immediately ────
            # This ensures context is ready before the user sends their first message.
            print(f"\n📤 UPLOAD: Starting synchronous extraction for doc_{doc.id} ({doc.title})")
            try:
                text = ai_services.extract_text_from_file(doc.file.path)
                doc.extracted_text = text
                doc.save(update_fields=['extracted_text'])
                print(f"✅ UPLOAD: Extracted {len(text)} chars from doc_{doc.id}.")

                if text:
                    ai_services.ingest_document_to_chroma(doc.id, text)
                else:
                    print(f"⚠️  UPLOAD: No text extracted from doc_{doc.id} — file may be empty or unsupported.")
            except Exception as e:
                print(f"❌ UPLOAD: Extraction/ingestion error for doc_{doc.id} — {e}")
                logger.error(f"Extraction/ingestion error: {e}", exc_info=True)

            # ── ASYNC: Summarization (slow, runs in background) ──────────────────
            thread = threading.Thread(target=_summarize_document_async, args=(doc,), daemon=True)
            thread.start()

            if chat_id:
                try:
                    chat = Chat.objects.get(pk=chat_id, user=request.user)
                    chat.active_document = doc
                    chat.save(update_fields=['active_document'])
                    print(f"✅ UPLOAD: Linked doc_{doc.id} to chat_{chat_id} as active_document.")
                except Chat.DoesNotExist:
                    pass

            return Response({
                "status": "success",
                "document_id": doc.id,
                "title": doc.title or getattr(doc.file, 'name', 'Uploaded Document'),
                "extracted_text_preview": (doc.extracted_text or '')[:200] + '…' if doc.extracted_text else 'No text extracted.',
                **serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print("Backend Traceback:\n", traceback.format_exc())
            logger.error(f"Backend Traceback:\n{traceback.format_exc()}")
            return Response(
                {"error": "Upload Failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    """GET/DELETE /api/documents/<id>/"""
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class DocumentSummarizeView(APIView):
    """POST /api/documents/<id>/summarize/ — Re-run summarization on a document."""

    def post(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, user=request.user)
        if not doc.extracted_text:
            return Response({'error': 'Document text not yet extracted. Please wait.'}, status=400)
        try:
            summary_data = ai_services.summarize_document(doc.extracted_text)
            summary_lines = ['## Key Points\n']
            for kp in summary_data.get('key_points', []):
                summary_lines.append(f'- {kp}')
            summary_lines.append(f'\n## Summary\n{summary_data.get("executive_summary", "")}')
            doc.summary = '\n'.join(summary_lines)
            doc.save(update_fields=['summary'])
            return Response({'summary': doc.summary, 'structured': summary_data})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Chat Views
# ─────────────────────────────────────────────────────────────────────────────

class ChatListCreateView(generics.ListCreateAPIView):
    """GET /api/chats/ — List chats. POST — Create new chat."""
    serializer_class = ChatListSerializer

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatDetailView(generics.RetrieveDestroyAPIView):
    """GET/DELETE /api/chats/<id>/"""
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)


class MessageCreateView(APIView):
    """POST /api/chats/<id>/message/ — Send a message and get AI response."""

    def post(self, request, pk):
        try:
            chat = get_object_or_404(Chat, pk=pk, user=request.user)
            user_content = request.data.get('content', '').strip()
            user_content = request.data.get('message', user_content).strip()  # support instruction format
            document_id = request.data.get('document_id')  # Optional RAG context
            use_rag = request.data.get('use_rag', False) or bool(document_id)

            if not user_content:
                return Response({'error': 'Message content is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Save user message
            Message.objects.create(chat=chat, role='user', content=user_content)

            # Build history (last 20 messages before the current one)
            recent = list(chat.messages.order_by('-created_at')[1:21])[::-1]
            history = [
                {'role': m.role, 'content': m.content}
                for m in recent
            ]

            # Optionally inject RAG context
            # Re-fetch from DB to get latest extracted_text (avoids stale ORM cache)
            doc_to_use = None
            if chat.active_document_id:
                try:
                    doc_to_use = Document.objects.get(pk=chat.active_document_id, user=request.user)
                    print(f"\n💬 MSG: Active doc = doc_{doc_to_use.id}, extracted_text len = {len(doc_to_use.extracted_text or '')}")
                except Document.DoesNotExist:
                    pass

            if not doc_to_use and use_rag and document_id:
                try:
                    doc_to_use = Document.objects.get(pk=document_id, user=request.user)
                    print(f"\n💬 MSG: Fallback doc from payload = doc_{doc_to_use.id}")
                except Document.DoesNotExist:
                    pass

            try:
                ai_response = ai_services.generate_rag_response(
                    chat.id, user_content, doc_to_use, history
                )
            except RuntimeError as e:
                logger.error(f"AI Service Error:\n{traceback.format_exc()}")
                return Response({'error': 'AI Processing Failed', 'details': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Save assistant message
            assistant_msg = Message.objects.create(chat=chat, role='assistant', content=ai_response)

            # Update chat title if it's the first exchange
            if chat.title == 'New Study Session' and chat.messages.count() <= 2:
                chat.title = user_content[:60] + ('...' if len(user_content) > 60 else '')
                chat.save(update_fields=['title'])

            return Response({
                "role": "assistant",
                "content": ai_response,
                'user_message': MessageSerializer(
                    chat.messages.filter(role='user').last()
                ).data,
                'assistant_message': MessageSerializer(assistant_msg).data,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("Backend Traceback:\n", traceback.format_exc())
            logger.error(f"Backend Traceback:\n{traceback.format_exc()}")
            return Response(
                {"error": "AI Processing Failed", "details": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ─────────────────────────────────────────────────────────────────────────────
# Note Views
# ─────────────────────────────────────────────────────────────────────────────

class NoteListCreateView(generics.ListCreateAPIView):
    """GET /api/notes/ — List. POST — Create."""
    serializer_class = NoteSerializer

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/notes/<id>/"""
    serializer_class = NoteSerializer

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)


class NoteImproveView(APIView):
    """POST /api/notes/<id>/improve/ — AI-improve a note."""

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        if not note.content:
            return Response({'error': 'Note content is empty.'}, status=400)
        try:
            improved = ai_services.improve_notes(note.content)
            note.improved_content = improved
            note.save(update_fields=['improved_content'])
            return Response({'improved_content': improved})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Quiz Views
# ─────────────────────────────────────────────────────────────────────────────

class QuizListView(generics.ListAPIView):
    """GET /api/quizzes/"""
    serializer_class = QuizSerializer

    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user)


class QuizGenerateView(APIView):
    """POST /api/quizzes/generate/ — Generate quiz from document or raw text."""

    def post(self, request):
        document_id = request.data.get('document_id')
        raw_text = request.data.get('text', '')
        num_questions = int(request.data.get('num_questions', 10))
        title = request.data.get('title', 'Generated Quiz')

        text = raw_text
        if document_id:
            try:
                doc = Document.objects.get(pk=document_id, user=request.user)
                text = doc.extracted_text or raw_text
            except Document.DoesNotExist:
                pass

        if not text:
            return Response({'error': 'Provide either document_id or text.'}, status=400)

        try:
            questions = ai_services.generate_quiz(text, num_questions)
            quiz = Quiz.objects.create(
                user=request.user,
                title=title,
                questions_json=questions,
                total_questions=len(questions),
            )
            return Response(QuizSerializer(quiz).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class QuizScoreView(APIView):
    """POST /api/quizzes/<id>/score/ — Save quiz score."""

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, user=request.user)
        score = request.data.get('score')
        if score is None:
            return Response({'error': 'score is required.'}, status=400)
        quiz.score = int(score)
        quiz.save(update_fields=['score'])
        return Response(QuizSerializer(quiz).data)


# ─────────────────────────────────────────────────────────────────────────────
# Flashcard Views
# ─────────────────────────────────────────────────────────────────────────────

class FlashcardListView(generics.ListAPIView):
    """GET /api/flashcards/"""
    serializer_class = FlashcardSerializer

    def get_queryset(self):
        return Flashcard.objects.filter(user=self.request.user)


class FlashcardGenerateView(APIView):
    """POST /api/flashcards/generate/ — Generate flashcards from document or text."""

    def post(self, request):
        document_id = request.data.get('document_id')
        raw_text = request.data.get('text', '')
        deck_title = request.data.get('deck_title', 'Study Deck')

        text = raw_text
        if document_id:
            try:
                doc = Document.objects.get(pk=document_id, user=request.user)
                text = doc.extracted_text or raw_text
            except Document.DoesNotExist:
                pass

        if not text:
            return Response({'error': 'Provide either document_id or text.'}, status=400)

        try:
            cards_data = ai_services.generate_flashcards(text, deck_title)
            created = []
            for card in cards_data:
                fc = Flashcard.objects.create(
                    user=request.user,
                    deck_title=deck_title,
                    front=card.get('front', ''),
                    back=card.get('back', ''),
                )
                created.append(fc)
            return Response(FlashcardSerializer(created, many=True).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Study Planner View
# ─────────────────────────────────────────────────────────────────────────────

class StudyPlanView(APIView):
    """POST /api/study-plan/ — Generate a structured daily study plan."""

    def post(self, request):
        topics = request.data.get('topics', [])
        exam_date = request.data.get('exam_date', '')
        hours_per_day = float(request.data.get('hours_per_day', 2.0))

        if not exam_date:
            return Response({'error': 'exam_date is required (YYYY-MM-DD).'}, status=400)

        try:
            plan = ai_services.generate_study_plan(topics, exam_date, hours_per_day)
            return Response(plan)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Stats / Dashboard View
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def dashboard_stats(request):
    """GET /api/stats/ — Returns summary counts for the dashboard."""
    user = request.user
    return Response({
        'documents': Document.objects.filter(user=user).count(),
        'chats': Chat.objects.filter(user=user).count(),
        'notes': Note.objects.filter(user=user).count(),
        'quizzes': Quiz.objects.filter(user=user).count(),
        'flashcards': Flashcard.objects.filter(user=user).count(),
    })
