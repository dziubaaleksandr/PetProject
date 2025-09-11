import pandas as pd
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def prepare_dataframe(transactions_queryset):
    transactions = transactions_queryset.filter(type='income')

    monthly_income = transactions.annotate(
        month=TruncMonth('date')).values('month').annotate(
        total=Sum('amount')).order_by('month')

    if not monthly_income:
        return None

    df = pd.DataFrame(monthly_income)
    df['month'] = pd.to_datetime(df['month'])
    df = df.sort_values('month')
    df['month_number'] = ((df['month'] - df['month'].min())
                          .dt.days // 30).astype(float)
    df['smoothed'] = df['total'].rolling(window=3, min_periods=1).mean()
    return df


def calculate_trend(df):
    X_raw = df[['month_number']]
    y = df['smoothed']

    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    model = LinearRegression()
    model.fit(X, y)

    return model, scaler, model.coef_[0]


def compare_recent_months(df, trend_slope):
    insights = []
    if len(df) < 2:
        return insights

    last, prev = df.iloc[-1], df.iloc[-2]
    delta = last['total'] - prev['total']
    pct_change = (delta / prev["total"]) * 100 if prev["total"] != 0 else 0

    if pct_change < -10:
        insights.append(
            f"Your income dropped {abs(pct_change):.1f}% last month.")
        if trend_slope > 0:
            insights.append("This contradicts your trend — monitor closely.")
    elif pct_change > 10:
        insights.append(
            f"Your income increased {pct_change:.1f}% last month.")
    else:
        insights.append("No significant change in income last month.")

    return insights


def check_volatility(df):
    insights = []
    std_dev = df['total'].astype(float).std()
    avg = df['total'].mean()
    if std_dev > avg * 0.4:
        insights.append(
            "Your income is highly volatile. Stabilizing revenue might help.")
    return insights


def forecast_income(df, model, scaler):
    next_month = scaler.transform([[df['month_number'].max() + 1]])
    predicted = model.predict(next_month)[0]
    return f"Projected income next month: ${predicted:.2f}"


def generate_insights(transactions_queryset):
    df = prepare_dataframe(transactions_queryset)
    if df is None:
        return ["No income data available."]

    model, scaler, trend_slope = calculate_trend(df)

    insights = []

    # Trend analysis
    if trend_slope > 0:
        insights.append("Your income shows an upward trend. Keep it up!")
    elif trend_slope < 0:
        insights.append(
            "Your income has been decreasing. Consider reviewing revenue sources.")
    else:
        insights.append("Your income appears stable month to month.")

    # Compare last months
    insights.extend(compare_recent_months(df, trend_slope))

    # Volatility
    insights.extend(check_volatility(df))

    # Forecast
    insights.append(forecast_income(df, model, scaler))

    return insights
