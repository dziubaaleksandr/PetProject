import pandas as pd
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.db.models.functions import TruncMonth
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from .forms import UploadFileForm
from .models import Transaction, Category


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

        monthly_income = transactions.annotate(
            month=TruncMonth('date')).values('month').annotate(
            total=Sum('amount')).order_by('month')

        if not monthly_income:
            context['insights'] = ["No income data available."]
            return context

        # Prepare DataFrame
        df = pd.DataFrame(monthly_income)
        df['month'] = pd.to_datetime(df['month'])
        df.sort_values('month')
        df['month_number'] = ((df['month'] - df['month'].min()
                               ).dt.days // 30).astype(float)
        # Apply a 3-month rolling average to smooth out short-term income fluctuations.
        # This helps highlight the underlying trend by reducing the impact of outliers or noise.
        df['smoothed'] = df['total'].rolling(window=3, min_periods=1).mean()

        X_raw = df[['month_number']]
        y = df['smoothed']

        # Normalize X to reduce time-bias
        scaler = StandardScaler()
        X = scaler.fit_transform(X_raw)

        model = LinearRegression()
        model.fit(X, y)
        trend_slope = model.coef_[0]

        insights = []
        if trend_slope > 0:
            insights.append("Your income shows an upward trend. Keep it up!")
        elif trend_slope < 0:
            insights.append(
                "Your income has been decreasing. Consider reviewing revenue sources.")
        else:
            insights.append("Your income appears stable month to month.")

        # Compare the last two months to detect recent income change.
        # If the change is more than ±10%, generate an insight message.
        # Also flag if a sharp drop contradicts the overall upward trend.
        if len(df) >= 2:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            delta = last['total'] - prev['total']
            pct_change = (delta / prev['total']
                          ) * 100 if prev['total'] != 0 else 0

            if pct_change < -10:
                insights.append(
                    f"Your income dropped {abs(pct_change):.1f}% last month.")
                if trend_slope > 0:
                    insights.append(
                        "This contradicts your trend — monitor closely.")
            elif pct_change > 10:
                insights.append(
                    f"Your income increased {pct_change:.1f}% last month.")
            else:
                insights.append("No significant change in income last month.")

        # Volatility check
        std_dev = df['total'].astype(float).std()
        avg = df['total'].mean()
        if std_dev > avg * 0.4:
            insights.append(
                "Your income is highly volatile. Stabilizing revenue might help.")

        # Simple Forecast
        next_month = scaler.transform([[df['month_number'].max() + 1]])
        predicted = model.predict(next_month)[0]
        insights.append(f"Projected income next month: ${predicted:.2f}")

        context['insights'] = insights
        return context
