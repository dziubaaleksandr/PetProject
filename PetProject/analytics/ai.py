import pandas as pd
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def generate_insights(transactions_queryset):
    transactions = transactions_queryset.filter(type='income')

    monthly_income = transactions.annotate(
        month=TruncMonth('date')).values('month').annotate(
        total=Sum('amount')).order_by('month')

    if not monthly_income:
        return ["No income data available."]

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

    return insights
