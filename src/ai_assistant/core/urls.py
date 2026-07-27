"""
URL routing for the core app — all mounted under /api/.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ───────────────────────────────────────────────────────────────
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/google/', views.GoogleAuthView.as_view(), name='auth-google'),
    path('auth/profile/', views.ProfileView.as_view(), name='auth-profile'),

    # ── Documents ──────────────────────────────────────────────────────────
    path('documents/', views.DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<int:pk>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/summarize/', views.DocumentSummarizeView.as_view(), name='document-summarize'),

    # ── Chat ───────────────────────────────────────────────────────────────
    path('chats/', views.ChatListCreateView.as_view(), name='chat-list'),
    path('chats/<int:pk>/', views.ChatDetailView.as_view(), name='chat-detail'),
    path('chats/<int:pk>/message/', views.MessageCreateView.as_view(), name='chat-message'),

    # ── Notes ──────────────────────────────────────────────────────────────
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),
    path('notes/<int:pk>/improve/', views.NoteImproveView.as_view(), name='note-improve'),

    # ── Quizzes ────────────────────────────────────────────────────────────
    path('quizzes/', views.QuizListView.as_view(), name='quiz-list'),
    path('quizzes/generate/', views.QuizGenerateView.as_view(), name='quiz-generate'),
    path('quizzes/<int:pk>/score/', views.QuizScoreView.as_view(), name='quiz-score'),

    # ── Flashcards ─────────────────────────────────────────────────────────
    path('flashcards/', views.FlashcardListView.as_view(), name='flashcard-list'),
    path('flashcards/generate/', views.FlashcardGenerateView.as_view(), name='flashcard-generate'),

    # ── Study Planner ──────────────────────────────────────────────────────
    path('study-plan/', views.StudyPlanView.as_view(), name='study-plan'),

    # ── Dashboard Stats ────────────────────────────────────────────────────
    path('stats/', views.dashboard_stats, name='dashboard-stats'),
]
