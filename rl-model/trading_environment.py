"""
Custom OpenAI Gym environment for stock trading with RL
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class StockTradingEnv(gym.Env):
    """
    A stock trading environment for reinforcement learning.
    
    State Space:
        - Current price
        - Price momentum
        - Volatility
        - Volume ratio
        - RSI
        - MACD line
        - MACD signal
        - Bollinger Band position
        - 5-min MA
        - 15-min MA
        - Current position (0=no position, 1=long)
        - Cash balance (normalized)
        - Shares owned (normalized)
    
    Action Space:
        - 0: HOLD
        - 1: BUY (1 share)
        - 2: SELL (1 share if owned)
    
    Reward:
        - Portfolio value change + Sharpe ratio consideration
        - Penalty for invalid actions
    """
    
    metadata = {"render_modes": ["human"]}
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        transaction_cost: float = 0.001,  # 0.1%
        reward_scaling: float = 1e-4
    ):
        """
        Initialize the trading environment
        
        Args:
            df: DataFrame with OHLCV and technical indicators
            initial_balance: Starting cash
            transaction_cost: Fee per transaction as ratio
            reward_scaling: Scale rewards for training stability
        """
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.reward_scaling = reward_scaling
        
        # Validate required columns
        required_cols = ['c', 'ma_5min', 'ma_15min', 'rsi', 'macd_line', 
                        'macd_signal', 'bb_upper', 'bb_lower', 'price_momentum',
                        'volatility', 'volume_ratio']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}. Will use defaults.")
        
        # Action space: 0=HOLD, 1=BUY, 2=SELL
        self.action_space = spaces.Discrete(3)
        
        # Observation space: 13 features (normalized)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(13,),
            dtype=np.float32
        )
        
        # Episode state
        self.current_step = 0
        self.balance = initial_balance
        self.shares_held = 0
        self.total_shares_bought = 0
        self.total_shares_sold = 0
        self.net_worth_history = []
        self.trades = []
        
        logger.info(f"StockTradingEnv initialized with {len(self.df)} steps")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset the environment to initial state"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.balance = self.initial_balance
        self.shares_held = 0
        self.total_shares_bought = 0
        self.total_shares_sold = 0
        self.net_worth_history = [self.initial_balance]
        self.trades = []
        
        return self._get_observation(), {}
    
    def _get_observation(self) -> np.ndarray:
        """
        Get current observation (state)
        
        Returns:
            Numpy array of normalized features
        """
        row = self.df.iloc[self.current_step]
        
        # Extract features with defaults
        current_price = row.get('c', 0)
        price_momentum = row.get('price_momentum', 0)
        volatility = row.get('volatility', 0)
        volume_ratio = row.get('volume_ratio', 1)
        rsi = row.get('rsi', 50) / 100.0  # Normalize to 0-1
        macd_line = row.get('macd_line', 0)
        macd_signal = row.get('macd_signal', 0)
        
        # Bollinger Band position
        bb_upper = row.get('bb_upper', current_price)
        bb_lower = row.get('bb_lower', current_price)
        bb_range = bb_upper - bb_lower if bb_upper > bb_lower else 1.0
        bb_position = (current_price - bb_lower) / bb_range if bb_range > 0 else 0.5
        
        ma_5min = row.get('ma_5min', current_price)
        ma_15min = row.get('ma_15min', current_price)
        
        # Portfolio features
        position = 1.0 if self.shares_held > 0 else 0.0
        cash_ratio = self.balance / self.initial_balance
        shares_ratio = (self.shares_held * current_price) / self.initial_balance if current_price > 0 else 0
        
        observation = np.array([
            current_price / 100.0,  # Normalize price
            price_momentum,
            volatility,
            volume_ratio,
            rsi,
            macd_line / 10.0,
            macd_signal / 10.0,
            bb_position,
            ma_5min / 100.0,
            ma_15min / 100.0,
            position,
            cash_ratio,
            shares_ratio
        ], dtype=np.float32)
        
        # Handle any NaN or inf values
        observation = np.nan_to_num(observation, nan=0.0, posinf=1.0, neginf=-1.0)
        
        return observation
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one time step within the environment
        
        Args:
            action: 0=HOLD, 1=BUY, 2=SELL
        
        Returns:
            observation, reward, terminated, truncated, info
        """
        current_price = self.df.iloc[self.current_step].get('c', 0)
        prev_net_worth = self._get_net_worth(current_price)
        
        # Execute action
        action_valid = True
        if action == 1:  # BUY
            # Buy 1 share if we have enough cash
            cost = current_price * (1 + self.transaction_cost)
            if self.balance >= cost:
                self.shares_held += 1
                self.balance -= cost
                self.total_shares_bought += 1
                self.trades.append({
                    'step': self.current_step,
                    'action': 'BUY',
                    'price': current_price,
                    'shares': 1
                })
            else:
                action_valid = False
        
        elif action == 2:  # SELL
            # Sell 1 share if we have any
            if self.shares_held > 0:
                self.shares_held -= 1
                self.balance += current_price * (1 - self.transaction_cost)
                self.total_shares_sold += 1
                self.trades.append({
                    'step': self.current_step,
                    'action': 'SELL',
                    'price': current_price,
                    'shares': 1
                })
            else:
                action_valid = False
        
        # Move to next step
        self.current_step += 1
        
        # Calculate new net worth
        new_net_worth = self._get_net_worth(current_price)
        self.net_worth_history.append(new_net_worth)
        
        # Calculate reward
        reward = self._calculate_reward(prev_net_worth, new_net_worth, action_valid)
        
        # Check if episode is done
        terminated = self.current_step >= len(self.df) - 1
        truncated = False
        
        # Get next observation
        if not terminated:
            observation = self._get_observation()
        else:
            observation = np.zeros(13, dtype=np.float32)
        
        # Info dict
        info = {
            'net_worth': new_net_worth,
            'balance': self.balance,
            'shares_held': self.shares_held,
            'total_profit': new_net_worth - self.initial_balance,
            'action_valid': action_valid
        }
        
        return observation, reward, terminated, truncated, info
    
    def _get_net_worth(self, current_price: float) -> float:
        """Calculate current net worth"""
        return self.balance + (self.shares_held * current_price)
    
    def _calculate_reward(self, prev_net_worth: float, new_net_worth: float, action_valid: bool) -> float:
        """
        Calculate reward for the step
        
        Reward components:
        1. Portfolio value change
        2. Sharpe ratio consideration
        3. Penalty for invalid actions
        """
        # Portfolio change
        portfolio_change = new_net_worth - prev_net_worth
        
        # Normalize by initial balance
        reward = (portfolio_change / self.initial_balance) * self.reward_scaling
        
        # Penalty for invalid actions
        if not action_valid:
            reward -= 0.01
        
        # Sharpe ratio bonus (if we have enough history)
        if len(self.net_worth_history) > 10:
            returns = np.diff(self.net_worth_history[-10:]) / self.net_worth_history[-10:-1]
            if len(returns) > 0 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns)
                reward += sharpe * 0.001  # Small bonus for good risk-adjusted returns
        
        return float(reward)
    
    def render(self, mode='human'):
        """Render the environment"""
        current_price = self.df.iloc[self.current_step].get('c', 0)
        net_worth = self._get_net_worth(current_price)
        profit = net_worth - self.initial_balance
        profit_pct = (profit / self.initial_balance) * 100
        
        print(f"Step: {self.current_step}/{len(self.df)}")
        print(f"Price: ${current_price:.2f}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Shares: {self.shares_held}")
        print(f"Net Worth: ${net_worth:.2f} ({profit_pct:+.2f}%)")
        print(f"Total Trades: Buy={self.total_shares_bought}, Sell={self.total_shares_sold}")
        print("-" * 50)
    
    def get_portfolio_statistics(self) -> Dict:
        """Get final portfolio statistics"""
        current_price = self.df.iloc[min(self.current_step, len(self.df) - 1)].get('c', 0)
        final_net_worth = self._get_net_worth(current_price)
        
        total_return = final_net_worth - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100
        
        # Calculate Sharpe ratio
        if len(self.net_worth_history) > 1:
            returns = np.diff(self.net_worth_history) / self.net_worth_history[:-1]
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        cummax = np.maximum.accumulate(self.net_worth_history)
        drawdown = (cummax - self.net_worth_history) / cummax
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_net_worth': final_net_worth,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'total_shares_bought': self.total_shares_bought,
            'total_shares_sold': self.total_shares_sold
        }




