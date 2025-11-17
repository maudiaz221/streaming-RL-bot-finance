"""
Train RL trading model using historical data
"""
import os
import argparse
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
import gymnasium as gym

from trading_environment import StockTradingEnv
from data_preparation import load_historical_data, prepare_training_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_env(df: pd.DataFrame, initial_balance: float = 10000.0):
    """Create and wrap the trading environment"""
    env = StockTradingEnv(df, initial_balance=initial_balance)
    env = Monitor(env)
    return env


def train_model(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame = None,
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    batch_size: int = 64,
    n_epochs: int = 10,
    save_path: str = "./models",
    model_name: str = "ppo_trading_model"
):
    """
    Train PPO model for stock trading
    
    Args:
        train_df: Training data with OHLCV and indicators
        test_df: Test data for evaluation
        total_timesteps: Total training timesteps
        learning_rate: Learning rate
        batch_size: Batch size for PPO
        n_epochs: Number of epochs per update
        save_path: Directory to save models
        model_name: Base name for saved model
    
    Returns:
        Trained model
    """
    logger.info("=" * 70)
    logger.info("Starting RL Model Training")
    logger.info("=" * 70)
    
    # Create save directory
    os.makedirs(save_path, exist_ok=True)
    
    # Create training environment
    logger.info(f"Creating training environment with {len(train_df)} samples")
    train_env = DummyVecEnv([lambda: create_env(train_df)])
    
    # Create evaluation environment if test data provided
    eval_env = None
    eval_callback = None
    if test_df is not None and len(test_df) > 0:
        logger.info(f"Creating evaluation environment with {len(test_df)} samples")
        eval_env = DummyVecEnv([lambda: create_env(test_df)])
        
        # Evaluation callback
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=f"{save_path}/best_model",
            log_path=f"{save_path}/eval_logs",
            eval_freq=10000,
            deterministic=True,
            render=False,
            n_eval_episodes=5
        )
    
    # Checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=f"{save_path}/checkpoints",
        name_prefix=model_name
    )
    
    # Create PPO model
    logger.info("Creating PPO model...")
    logger.info(f"  Learning rate: {learning_rate}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  N epochs: {n_epochs}")
    
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=learning_rate,
        n_steps=2048,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        clip_range_vf=None,
        normalize_advantage=True,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=f"{save_path}/tensorboard"
    )
    
    # Train the model
    logger.info(f"Starting training for {total_timesteps} timesteps...")
    start_time = datetime.now()
    
    callbacks = [checkpoint_callback]
    if eval_callback:
        callbacks.append(eval_callback)
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=callbacks,
        progress_bar=True
    )
    
    end_time = datetime.now()
    training_time = (end_time - start_time).total_seconds()
    logger.info(f"✅ Training completed in {training_time:.2f} seconds")
    
    # Save final model
    final_model_path = f"{save_path}/{model_name}.zip"
    model.save(final_model_path)
    logger.info(f"✅ Model saved to {final_model_path}")
    
    # Evaluate on training set
    logger.info("\n" + "=" * 70)
    logger.info("Evaluating on training set...")
    train_stats = evaluate_model(model, train_df)
    logger.info("\nTraining Set Performance:")
    for key, value in train_stats.items():
        logger.info(f"  {key}: {value}")
    
    # Evaluate on test set if available
    if test_df is not None and len(test_df) > 0:
        logger.info("\n" + "=" * 70)
        logger.info("Evaluating on test set...")
        test_stats = evaluate_model(model, test_df)
        logger.info("\nTest Set Performance:")
        for key, value in test_stats.items():
            logger.info(f"  {key}: {value}")
    
    logger.info("\n" + "=" * 70)
    logger.info("Training Complete!")
    logger.info("=" * 70)
    
    return model


def evaluate_model(model, df: pd.DataFrame, n_episodes: int = 1) -> dict:
    """
    Evaluate trained model on data
    
    Args:
        model: Trained RL model
        df: Data to evaluate on
        n_episodes: Number of episodes to run
    
    Returns:
        Dictionary of performance metrics
    """
    env = create_env(df)
    
    episode_rewards = []
    episode_stats = []
    
    for episode in range(n_episodes):
        obs, _ = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_reward += reward
        
        episode_rewards.append(episode_reward)
        
        # Get portfolio statistics
        stats = env.unwrapped.get_portfolio_statistics()
        episode_stats.append(stats)
    
    # Aggregate statistics
    avg_stats = {
        'avg_episode_reward': np.mean(episode_rewards),
        'avg_total_return': np.mean([s['total_return'] for s in episode_stats]),
        'avg_return_pct': np.mean([s['total_return_pct'] for s in episode_stats]),
        'avg_sharpe_ratio': np.mean([s['sharpe_ratio'] for s in episode_stats]),
        'avg_max_drawdown': np.mean([s['max_drawdown'] for s in episode_stats]),
        'avg_total_trades': np.mean([s['total_trades'] for s in episode_stats])
    }
    
    return avg_stats


def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='Train RL trading model')
    parser.add_argument('--data-path', type=str, default='../data/processed',
                       help='Path to processed data directory')
    parser.add_argument('--symbol', type=str, default='AAPL',
                       help='Stock symbol to train on')
    parser.add_argument('--timesteps', type=int, default=100000,
                       help='Total training timesteps')
    parser.add_argument('--save-path', type=str, default='./models',
                       help='Path to save models')
    parser.add_argument('--model-name', type=str, default='ppo_trading_model',
                       help='Model name')
    parser.add_argument('--train-split', type=float, default=0.8,
                       help='Train/test split ratio')
    
    args = parser.parse_args()
    
    try:
        # Load and prepare data
        logger.info(f"Loading data from {args.data_path}")
        df = load_historical_data(args.data_path, symbol=args.symbol)
        
        if df is None or len(df) == 0:
            logger.error("No data loaded. Please check data path and symbol.")
            return
        
        logger.info(f"Loaded {len(df)} records for {args.symbol}")
        
        # Prepare training data
        train_df, test_df = prepare_training_data(df, train_split=args.train_split)
        
        logger.info(f"Train set: {len(train_df)} samples")
        logger.info(f"Test set: {len(test_df)} samples")
        
        # Train model
        model = train_model(
            train_df=train_df,
            test_df=test_df,
            total_timesteps=args.timesteps,
            save_path=args.save_path,
            model_name=args.model_name
        )
        
        logger.info("\n✅ All done! Model is ready for deployment.")
        logger.info(f"   Model location: {args.save_path}/{args.model_name}.zip")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise


if __name__ == "__main__":
    main()

