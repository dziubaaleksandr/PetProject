from django.db.models import Sum
from rest_framework import generics, permissions
from rest_framework.response import Response

from ..ai import generate_insights
from ..models import Transaction
from .serializers import TransactionSerializer


class TransactionListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class KPIAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        income_total = transactions.filter(
            type='income').aggregate(
            total=Sum('amount'))['total'] or 0
        expense_total = transactions.filter(
            type='expense').aggregate(
            total=Sum('amount'))['total'] or 0

        return Response({
            'income': income_total,
            'expense': expense_total,
            'net': income_total - expense_total
        })


class InsightAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        insights = generate_insights(transactions)
        return Response({'insights': insights})
