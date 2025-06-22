import pandas as pd
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
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
