# RL Trading Model

Reinforcement Learning trading model using PPO (Proximal Policy Optimization) for stock trading decisions.

## Features

- ✅ Custom Gymnasium trading environment
- ✅ PPO algorithm implementation using stable-baselines3
- ✅ Risk-adjusted rewards (Sharpe ratio)
- ✅ Transaction cost modeling
- ✅ Portfolio tracking and statistics
- ✅ Model checkpointing and evaluation
- ✅ Integration with PySpark for real-time inference

## Environment

### State Space (13 features)
1. Current price (normalized)
2. Price momentum (5-bar change)
3. Volatility (20-bar rolling std)
4. Volume ratio (current / MA)
5. RSI (0-1, normalized)
6. MACD line
7. MACD signal
8. Bollinger Band position (0-1)
9. 5-minute MA
10. 15-minute MA
11. Current position (0 or 1)
12. Cash ratio
13. Shares value ratio

### Action Space
- **0: HOLD** - Do nothing
- **1: BUY** - Buy 1 share (if enough cash)
- **2: SELL** - Sell 1 share (if owned)

### Reward Function
```python
reward = portfolio_change / initial_balance * scaling_factor
       + sharpe_ratio * 0.001
       - invalid_action_penalty
```

## Installation

```bash
cd rl-model
pip install -r requirements.txt
```

## Usage

### 1. Prepare Training Data

Data should be in parquet or CSV format with these columns:
- `timestamp`: Timestamp
- `S`: Symbol
- `o`, `h`, `l`, `c`: OHLC prices
- `v`: Volume
- Technical indicators: `rsi`, `macd_line`, `macd_signal`, `bb_upper`, `bb_lower`, `ma_5min`, `ma_15min`, `price_momentum`, `volatility`, `volume_ratio`

If indicators are missing, they will be calculated automatically.

### 2. Train the Model

```bash
# Train with default settings
python train_model.py \
  --data-path ../data/processed \
  --symbol AAPL \
  --timesteps 100000 \
  --save-path ./models

# With custom parameters
python train_model.py \
  --data-path ../data/processed \
  --symbol TSLA \
  --timesteps 200000 \
  --save-path ./models \
  --model-name ppo_tsla_model \
  --train-split 0.8
```

Parameters:
- `--data-path`: Path to processed data directory
- `--symbol`: Stock symbol to train on
- `--timesteps`: Total training timesteps (default: 100,000)
- `--save-path`: Directory to save models (default: ./models)
- `--model-name`: Model filename (default: ppo_trading_model)
- `--train-split`: Train/test split ratio (default: 0.8)

### 3. Monitor Training

View training progress with TensorBoard:

```bash
tensorboard --logdir ./models/tensorboard
```

Access at: http://localhost:6006

### 4. Evaluate Model

The training script automatically evaluates on train and test sets. Sample output:

```
Training Set Performance:
  avg_episode_reward: 125.42
  avg_total_return: 523.15
  avg_return_pct: 5.23
  avg_sharpe_ratio: 1.85
  avg_max_drawdown: 0.12
  avg_total_trades: 45
```

### 5. Use for Inference

```python
from model import TradingModel, create_observation

# Load model
model = TradingModel("./models/ppo_trading_model.zip")
model.load()

# Create observation
obs = create_observation(
    price=150.25,
    rsi=45.0,
    macd_line=0.5,
    macd_signal=0.3,
    bb_position=0.6,
    ma_5min=149.80,
    ma_15min=149.50
)

# Get prediction
action, action_name, confidence = model.predict(obs)
print(f"Action: {action_name} (confidence: {confidence:.2f})")
```

## Architecture

### PPO Configuration
- **Policy**: MLP (Multi-Layer Perceptron)
- **Learning rate**: 3e-4
- **Batch size**: 64
- **N steps**: 2048
- **N epochs**: 10
- **Gamma**: 0.99 (discount factor)
- **GAE lambda**: 0.95
- **Clip range**: 0.2

### Network Architecture
The MLP policy uses:
- Input: 13 features
- Hidden layers: 2 layers of 64 units each
- Activation: Tanh
- Output: 3 actions (discrete)

## Training Tips

### 1. Data Quality
- Ensure sufficient historical data (>10,000 samples recommended)
- Include various market conditions (bull, bear, sideways)
- Verify technical indicators are calculated correctly

### 2. Hyperparameter Tuning
- Increase `timesteps` for better convergence (200,000+)
- Adjust `learning_rate` if training is unstable
- Tune `batch_size` based on available memory

### 3. Reward Shaping
- Modify reward function in `trading_environment.py`
- Consider different risk metrics (Sortino ratio, Calmar ratio)
- Experiment with transaction cost values

### 4. Evaluation
- Always evaluate on held-out test data
- Compare against buy-and-hold baseline
- Monitor Sharpe ratio and max drawdown

## Integration with PySpark

The model can be used in PySpark streaming for real-time predictions:

```python
from rl_model_inference import add_rl_predictions

# Add predictions to streaming DataFrame
df_with_predictions = add_rl_predictions(df, model_path="./models/ppo_trading_model.zip")
```

See `../streaming-processor/rl_model_inference.py` for implementation.

## Model Files

After training, you'll find:

```
models/
├── ppo_trading_model.zip          # Final trained model
├── best_model/
│   └── best_model.zip              # Best model during training
├── checkpoints/
│   ├── ppo_trading_model_10000_steps.zip
│   ├── ppo_trading_model_20000_steps.zip
│   └── ...
├── eval_logs/
│   └── evaluations.npz             # Evaluation metrics
└── tensorboard/
    └── PPO_1/                      # TensorBoard logs
```

## Performance Metrics

### Key Metrics
- **Total Return**: Profit/loss in dollars and percentage
- **Sharpe Ratio**: Risk-adjusted return metric
- **Max Drawdown**: Maximum peak-to-trough decline
- **Total Trades**: Number of buy/sell actions
- **Win Rate**: Percentage of profitable trades

### Benchmarking
Compare your model against:
1. **Buy-and-hold**: Simply buy at start, sell at end
2. **Rule-based**: RSI + Bollinger Band strategy
3. **Random**: Random actions

## Troubleshooting

### Issue: Training is slow

**Solutions:**
- Reduce `n_steps` parameter
- Decrease `total_timesteps`
- Use GPU (PyTorch will auto-detect)
- Simplify environment (fewer features)

### Issue: Model doesn't improve

**Solutions:**
- Increase training timesteps
- Adjust learning rate (try 1e-4 or 1e-3)
- Check reward function (should vary during episodes)
- Verify data quality and indicators

### Issue: Model only takes HOLD action

**Solutions:**
- Increase exploration (adjust `ent_coef`)
- Modify reward function to incentivize trading
- Reduce transaction costs
- Check action penalties

### Issue: High variance in returns

**Solutions:**
- Increase training data
- Add more features to state space
- Tune `gamma` and `gae_lambda`
- Use ensemble of models

## Advanced Features

### Multi-Symbol Training

Train on multiple symbols simultaneously:

```python
# Load data for multiple symbols
symbols = ['AAPL', 'TSLA', 'NVDA']
dfs = [load_historical_data(path, symbol=s) for s in symbols]
combined_df = pd.concat(dfs, ignore_index=True)

# Train model
model = train_model(combined_df, ...)
```

### Custom Reward Functions

Modify `_calculate_reward()` in `trading_environment.py`:

```python
def _calculate_reward(self, prev_net_worth, new_net_worth, action_valid):
    # Example: Sortino ratio (penalize downside volatility more)
    portfolio_change = new_net_worth - prev_net_worth
    
    if len(self.net_worth_history) > 10:
        returns = np.diff(self.net_worth_history[-10:])
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns)
            sortino = np.mean(returns) / downside_std if downside_std > 0 else 0
            reward += sortino * 0.001
    
    return reward
```

## License

MIT

