import io

from analytics.models import Category, Transaction
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class UploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test', password='test')
        self.category = Category.objects.create(
            name='Marketing', user=self.user)
        self.login = self.client.login(
            username='test', password='test')

    def test_csv_upload(self):
        csv_content = """date,description,amount,category,type
2025-05-01,Google Ads,250,Marketing,expense
2025-05-02,Product Sale,1000,Sales,income
"""

        file = io.StringIO(csv_content)
        file.name = 'test.csv'

        response = self.client.post(reverse('upload'), {
            'file': file
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 2)

        # Check that the first transaction is saved correctly
        tx = Transaction.objects.get(description="Google Ads")
        self.assertEqual(tx.amount, 250)
        self.assertEqual(tx.category.name, "marketing")
        self.assertEqual(tx.type, "expense")
        self.assertEqual(tx.user, self.user)

        tx = Transaction.objects.get(description="Product Sale")
        self.assertEqual(tx.amount, 1000)
        self.assertEqual(tx.category.name, "sales")
        self.assertEqual(tx.type, "income")
        self.assertEqual(tx.user, self.user)
