import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

class HydroWatchForecaster:
    """
    Trains the forecasting model and runs a recursive walk-forward validation backtest.
    """
    def __init__(self, seed=42):
        self.feature_cols = [
            "lag_1_area",
            "weighted_catchment_precip_mm",
            "lag_1_catchment_precip_mm",
            "mean_temp_c",
            "sin_q",
            "cos_q"
        ]
        self.model = RandomForestRegressor(n_estimators=150, max_depth=4, random_state=seed)

    def fit(self, train_df):
        self.model.fit(train_df[self.feature_cols], train_df["water_area_ha"])

    def run_backtest(self, train_df, test_df):
        backtest_preds = []
        prev_area = train_df["water_area_ha"].iloc[-1]

        for i, row in test_df.reset_index(drop=True).iterrows():
            prev_precip = (
                train_df["weighted_catchment_precip_mm"].iloc[-1]
                if i == 0
                else test_df["weighted_catchment_precip_mm"].iloc[i-1]
            )

            X_row = pd.DataFrame([{
                "lag_1_area": prev_area,
                "weighted_catchment_precip_mm": row["weighted_catchment_precip_mm"],
                "lag_1_catchment_precip_mm": prev_precip,
                "mean_temp_c": row["mean_temp_c"],
                "sin_q": row["sin_q"],
                "cos_q": row["cos_q"]
            }])

            pred = float(self.model.predict(X_row[self.feature_cols])[0])
            backtest_preds.append(round(pred, 2))
            prev_area = pred

            test_df.loc[test_df.index[i], "predicted_ha"] = round(pred, 2)

        test_df["error_pct"] = (np.abs(test_df["water_area_ha"] - test_df["predicted_ha"]) / test_df["water_area_ha"] * 100).round(2)
        mae = mean_absolute_error(test_df["water_area_ha"], test_df["predicted_ha"])
        mape = mean_absolute_percentage_error(test_df["water_area_ha"], test_df["predicted_ha"]) * 100
        
        return test_df, mae, mape
