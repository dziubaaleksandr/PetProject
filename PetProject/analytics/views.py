import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from .ai import generate_insights
from .forms import UploadFileForm
from .models import Category, Transaction


class UploadView(LoginRequiredMixin, FormView):
    template_name = 'analytics/upload.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('upload')

    def form_valid(self, form):
        # TODO: add file validation
        file = form.cleaned_data['file']
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith('xlsx'):
                df = pd.read_excel(file)
            else:
                form.add_error(
                    'file', 'Unsupported file type. Use .csv or .xlsx')
                return self.form_invalid(form)

            required_cols = ['date', 'description',
                             'amount', 'category', 'type']
            if not all(col in df.columns for col in required_cols):
                form.add_error('file', 'Missing required columns.')
                return self.form_invalid(form)

            for _, row in df.iterrows():
                # Get or create category for this user
                category_name = row['category'].strip().lower()
                category_obj, _ = Category.objects.get_or_create(
                    name=category_name,
                    user=self.request.user
                )

                # Create the transaction
                Transaction.objects.create(
                    user=self.request.user,
                    date=row['date'],
                    description=row['description'],
                    amount=row['amount'],
                    category=category_obj,
                    type=row['type'],
                )
        except Exception as e:
            form.add_error('file', f'Error processing file: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        transaction = Transaction.objects.filter(user=user)

        # KPIs
        context['income_total'] = transaction.filter(
            type='income').aggregate(
            total=Sum('amount'))['total'] or 0
        context['expense_total'] = transaction.filter(
            type='expense').aggregate(
            total=Sum('amount'))['total'] or 0
        context['balance'] = context['income_total'] - context['expense_total']

        # Monthly aggregation
        monthly_data = transaction.annotate(
            month=TruncMonth('date')).values(
            'month', 'type').annotate(
            total=Sum('amount')).order_by('month')

        # Reformat for Chart.js
        months = sorted(set(row['month'].strftime('%Y-%m')
                        for row in monthly_data))
        income_data = {m: 0 for m in months}
        expense_data = {m: 0 for m in months}

        for row in monthly_data:
            month = row['month'].strftime('%Y-%m')
            if row['type'] == 'income':
                income_data[month] = float(row['total'])
            else:
                expense_data[month] = float(row['total'])

        context['chart_labels'] = list(income_data.keys())
        context['chart_income'] = list(income_data.values())
        context['chart_expense'] = list(expense_data.values())

        return context


class InsightView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/insights.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        transactions = Transaction.objects.filter(user=user, type='income')
        insights = generate_insights(transactions)
        context['insights'] = insights
        return context
