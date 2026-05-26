import os
import pandas as pd
from prophet import Prophet

class FinancePredictor:
    def __init__(self, file_path='lich_su_chi_tieu.csv'):
        self.file_path = file_path

    def _prepare_data(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        df = pd.read_csv(self.file_path)

        if 'Date' in df.columns and 'Amount' in df.columns:
            df = df.rename(columns={'Date': 'ds', 'Amount': 'y'})

        if 'Type' in df.columns:
            df = df[df['Type'] == 'Expense'].copy()

        if df['y'].dtype == object:
            df['y'] = df['y'].astype(str).str.replace(',', '').str.replace('$', '').str.strip()

        df['ds'] = pd.to_datetime(df['ds'], errors='coerce')
        df['y'] = pd.to_numeric(df['y'], errors='coerce')

        df = df.dropna(subset=['ds', 'y'])
        df = df[df['y'] > 0]

        df = df.groupby('ds', as_index=False)['y'].sum()
        df = df.sort_values('ds').reset_index(drop=True)

        return df

    def predict_next_30_days(self):
        try:
            df = self._prepare_data()

            if len(df) < 5:
                return {"status": "error", "detail": "Insufficient data (at least 5 days required)."}

            expected_total_spending = 0
            model_used = "Prophet_AI"

            try:
                m = Prophet(daily_seasonality=False, yearly_seasonality=False, weekly_seasonality=False)
                m.fit(df, algorithm='LBFGS')
                future_days = m.make_future_dataframe(periods=30)
                forecast = m.predict(future_days)
                expected_total_spending = forecast['yhat'].tail(30).sum()
                print("Successfully used AI Prophet!")
                
            except Exception as e:
                print(f"Warning: AI Prophet encountered a C++ error ({str(e)[:50]}). Activating Plan B...")
                model_used = "Mathematical_Moving_Average"
                
                daily_average = df['y'].tail(30).mean()
                expected_total_spending = daily_average * 30
                print("Calculated result using Moving Average algorithm!")

            expected_total_spending = max(0, float(expected_total_spending))

            if expected_total_spending > 5000000:
                warning_message = "DANGER: High risk of budget deficit!"
            else:
                warning_message = "SAFE: Spending is under control"

            return {
                "status": "success",
                "model_used": model_used,
                "total_spending_next_30_days": round(expected_total_spending, 2),
                "warning": warning_message
            }

        except Exception as e:
            return {"status": "error", "detail": str(e)}