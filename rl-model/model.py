"""
RL Model wrapper for inference
"""
import os
import numpy as np
from stable_baselines3 import PPO
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class TradingModel:
    """Wrapper class for RL trading model"""
    
    def __init__(self, model_path: str):
        """
        Initialize model wrapper
        
        Args:
            model_path: Path to saved model (.zip file)
        """
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        
        # Action mapping
        self.action_map = {
            0: "HOLD",
            1: "BUY",
            2: "SELL"
        }
    
    def load(self):
        """Load the model from disk"""
        if self.is_loaded:
            return
        
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model not found at {self.model_path}")
            
            logger.info(f"Loading model from {self.model_path}")
            self.model = PPO.load(self.model_path)
            self.is_loaded = True
            logger.info("✅ Model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def predict(self, observation: np.ndarray, deterministic: bool = True) -> Tuple[int, str, float]:
        """
        Make a prediction
        
        Args:
            observation: State observation (13 features)
            deterministic: Use deterministic policy
        
        Returns:
            Tuple of (action, action_name, confidence)
        """
        if not self.is_loaded:
            self.load()
        
        try:
            # Ensure observation is 2D
            if observation.ndim == 1:
                observation = observation.reshape(1, -1)
            
            # Get action from model
            action, _states = self.model.predict(observation, deterministic=deterministic)
            
            # Extract action value
            if isinstance(action, np.ndarray):
                action = int(action[0])
            else:
                action = int(action)
            
            # Map to action name
            action_name = self.action_map.get(action, "HOLD")
            
            # Confidence (simplified - in production, use model's action probabilities)
            confidence = 0.75
            
            return action, action_name, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0, "HOLD", 0.0
    
    def predict_batch(self, observations: np.ndarray, deterministic: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Make batch predictions
        
        Args:
            observations: Batch of observations (n_samples, 13)
            deterministic: Use deterministic policy
        
        Returns:
            Tuple of (actions, action_names, confidences)
        """
        if not self.is_loaded:
            self.load()
        
        try:
            # Get actions from model
            actions, _states = self.model.predict(observations, deterministic=deterministic)
            
            # Map to action names
            action_names = np.array([self.action_map.get(int(a), "HOLD") for a in actions])
            
            # Confidences (simplified)
            confidences = np.full(len(actions), 0.75)
            
            return actions, action_names, confidences
            
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            n = len(observations)
            return np.zeros(n), np.array(["HOLD"] * n), np.zeros(n)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        if not self.is_loaded:
            self.load()
        
        return {
            'model_path': self.model_path,
            'model_type': 'PPO',
            'is_loaded': self.is_loaded,
            'action_space': list(self.action_map.values()),
            'observation_space_size': 13
        }


def create_observation(
    price: float,
    price_momentum: float = 0.0,
    volatility: float = 0.0,
    volume_ratio: float = 1.0,
    rsi: float = 50.0,
    macd_line: float = 0.0,
    macd_signal: float = 0.0,
    bb_position: float = 0.5,
    ma_5min: float = None,
    ma_15min: float = None,
    position: int = 0,
    cash_ratio: float = 1.0,
    shares_ratio: float = 0.0
) -> np.ndarray:
    """
    Create observation vector from individual features
    
    Args:
        price: Current price
        price_momentum: Price momentum
        volatility: Volatility
        volume_ratio: Volume ratio
        rsi: RSI value (0-100)
        macd_line: MACD line
        macd_signal: MACD signal
        bb_position: Bollinger Band position (0-1)
        ma_5min: 5-minute MA
        ma_15min: 15-minute MA
        position: Current position (0 or 1)
        cash_ratio: Cash to initial balance ratio
        shares_ratio: Shares value to initial balance ratio
    
    Returns:
        Numpy array observation
    """
    if ma_5min is None:
        ma_5min = price
    if ma_15min is None:
        ma_15min = price
    
    observation = np.array([
        price / 100.0,
        price_momentum,
        volatility,
        volume_ratio,
        rsi / 100.0,
        macd_line / 10.0,
        macd_signal / 10.0,
        bb_position,
        ma_5min / 100.0,
        ma_15min / 100.0,
        float(position),
        cash_ratio,
        shares_ratio
    ], dtype=np.float32)
    
    # Handle NaN or inf
    observation = np.nan_to_num(observation, nan=0.0, posinf=1.0, neginf=-1.0)
    
    return observation

