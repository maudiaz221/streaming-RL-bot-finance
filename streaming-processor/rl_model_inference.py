"""
RL Model inference integration with PySpark
"""
import pandas as pd
import numpy as np
from pyspark.sql import DataFrame
from pyspark.sql.functions import pandas_udf, PandasUDFType, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
import logging
import os

logger = logging.getLogger(__name__)


class RLModelWrapper:
    """
    Wrapper for RL model inference in PySpark
    Uses lazy loading to avoid serialization issues
    """
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
    
    def load_model(self):
        """Load the RL model (lazy loading)"""
        if self._model is None:
            try:
                from stable_baselines3 import PPO
                
                if os.path.exists(self.model_path):
                    logger.info(f"Loading RL model from {self.model_path}")
                    self._model = PPO.load(self.model_path)
                    logger.info("✅ RL model loaded successfully")
                else:
                    logger.warning(f"Model file not found: {self.model_path}")
                    logger.warning("RL predictions will be disabled")
                    self._model = None
            except Exception as e:
                logger.error(f"Failed to load RL model: {e}")
                self._model = None
        
        return self._model
    
    def predict(self, observations: np.ndarray) -> np.ndarray:
        """
        Make predictions using the RL model
        
        Args:
            observations: Numpy array of observations (features)
        
        Returns:
            Numpy array of actions
        """
        model = self.load_model()
        
        if model is None:
            # Return default action (HOLD=0) if model not available
            return np.zeros(len(observations), dtype=int)
        
        try:
            actions, _ = model.predict(observations, deterministic=True)
            return actions
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return np.zeros(len(observations), dtype=int)


def create_rl_features_vector(df: pd.DataFrame) -> np.ndarray:
    """
    Create feature vector for RL model from DataFrame
    
    Expected features (in order):
    - current_price
    - price_momentum
    - volatility
    - volume_ratio
    - rsi
    - macd_line
    - macd_signal
    - bb_position (where price is relative to bands)
    - ma_5min
    - ma_15min
    
    Args:
        df: Pandas DataFrame with calculated indicators
    
    Returns:
        Numpy array of shape (n_samples, n_features)
    """
    features = []
    
    # Price features
    if 'p' in df.columns:
        features.append(df['p'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    # Momentum
    if 'price_momentum' in df.columns:
        features.append(df['price_momentum'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    # Volatility
    if 'volatility' in df.columns:
        features.append(df['volatility'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    # Volume
    if 'volume_ratio' in df.columns:
        features.append(df['volume_ratio'].fillna(1))
    else:
        features.append(pd.Series([1] * len(df)))
    
    # RSI
    if 'rsi' in df.columns:
        features.append(df['rsi'].fillna(50))
    else:
        features.append(pd.Series([50] * len(df)))
    
    # MACD
    if 'macd_line' in df.columns:
        features.append(df['macd_line'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    if 'macd_signal' in df.columns:
        features.append(df['macd_signal'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    # Bollinger Bands position
    if all(col in df.columns for col in ['p', 'bb_upper', 'bb_lower']):
        bb_range = df['bb_upper'] - df['bb_lower']
        bb_position = (df['p'] - df['bb_lower']) / bb_range.where(bb_range > 0, 1)
        features.append(bb_position.fillna(0.5))
    else:
        features.append(pd.Series([0.5] * len(df)))
    
    # Moving averages
    if 'ma_5min' in df.columns:
        features.append(df['ma_5min'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    if 'ma_15min' in df.columns:
        features.append(df['ma_15min'].fillna(0))
    else:
        features.append(pd.Series([0] * len(df)))
    
    # Stack features
    feature_array = np.column_stack(features)
    
    # Handle any remaining NaN values
    feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=0.0, neginf=0.0)
    
    return feature_array


def add_rl_predictions(df: DataFrame, model_path: str) -> DataFrame:
    """
    Add RL model predictions to streaming DataFrame
    
    Args:
        df: PySpark DataFrame with calculated indicators
        model_path: Path to the trained RL model
    
    Returns:
        DataFrame with RL predictions (action and confidence)
    """
    
    # Define the schema for the UDF output
    result_schema = StructType([
        StructField("rl_action", IntegerType(), True),
        StructField("rl_action_name", StringType(), True),
        StructField("rl_confidence", DoubleType(), True)
    ])
    
    # Create a broadcast variable for the model path
    model_wrapper = RLModelWrapper(model_path)
    
    @pandas_udf(result_schema, PandasUDFType.SCALAR)
    def predict_udf(*cols):
        """
        Pandas UDF for batch prediction
        """
        # Reconstruct DataFrame from columns
        df_pandas = pd.DataFrame({
            'p': cols[0] if len(cols) > 0 else pd.Series([0]),
            'price_momentum': cols[1] if len(cols) > 1 else pd.Series([0]),
            'volatility': cols[2] if len(cols) > 2 else pd.Series([0]),
            'volume_ratio': cols[3] if len(cols) > 3 else pd.Series([1]),
            'rsi': cols[4] if len(cols) > 4 else pd.Series([50]),
            'macd_line': cols[5] if len(cols) > 5 else pd.Series([0]),
            'macd_signal': cols[6] if len(cols) > 6 else pd.Series([0]),
            'bb_upper': cols[7] if len(cols) > 7 else pd.Series([0]),
            'bb_lower': cols[8] if len(cols) > 8 else pd.Series([0]),
            'ma_5min': cols[9] if len(cols) > 9 else pd.Series([0]),
            'ma_15min': cols[10] if len(cols) > 10 else pd.Series([0])
        })
        
        # Create feature vector
        features = create_rl_features_vector(df_pandas)
        
        # Make predictions
        actions = model_wrapper.predict(features)
        
        # Map actions to names
        action_names = {0: "HOLD", 1: "BUY", 2: "SELL"}
        action_name_series = pd.Series([action_names.get(a, "HOLD") for a in actions])
        
        # Calculate confidence (placeholder - in real scenario, use model's probability output)
        confidence_series = pd.Series([0.75] * len(actions))
        
        # Return structured result
        result_df = pd.DataFrame({
            'rl_action': actions,
            'rl_action_name': action_name_series,
            'rl_confidence': confidence_series
        })
        
        return result_df
    
    # Apply the UDF
    df_with_predictions = df.withColumn(
        "rl_predictions",
        predict_udf(
            col("p"),
            col("price_momentum"),
            col("volatility"),
            col("volume_ratio"),
            col("rsi"),
            col("macd_line"),
            col("macd_signal"),
            col("bb_upper"),
            col("bb_lower"),
            col("ma_5min"),
            col("ma_15min")
        )
    )
    
    # Expand the struct into separate columns
    df_with_predictions = df_with_predictions.select(
        "*",
        col("rl_predictions.rl_action").alias("rl_action"),
        col("rl_predictions.rl_action_name").alias("rl_action_name"),
        col("rl_predictions.rl_confidence").alias("rl_confidence")
    ).drop("rl_predictions")
    
    return df_with_predictions


def simple_rule_based_strategy(df: DataFrame) -> DataFrame:
    """
    Simple rule-based trading strategy as fallback when RL model is not available
    
    Rules:
    - BUY: RSI < 30 and price below lower Bollinger Band
    - SELL: RSI > 70 and price above upper Bollinger Band
    - HOLD: Otherwise
    
    Args:
        df: DataFrame with technical indicators
    
    Returns:
        DataFrame with strategy signals
    """
    from pyspark.sql.functions import when, lit
    
    df = df.withColumn(
        "rule_action",
        when(
            (col("rsi") < 30) & (col("p") < col("bb_lower")),
            lit(1)  # BUY
        ).when(
            (col("rsi") > 70) & (col("p") > col("bb_upper")),
            lit(2)  # SELL
        ).otherwise(
            lit(0)  # HOLD
        )
    )
    
    df = df.withColumn(
        "rule_action_name",
        when(col("rule_action") == 1, lit("BUY"))
        .when(col("rule_action") == 2, lit("SELL"))
        .otherwise(lit("HOLD"))
    )
    
    return df




