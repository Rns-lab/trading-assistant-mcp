"""
Data pipeline for the Transformer model
Handles data preprocessing, batching, and feature engineering
"""
import numpy as np
import pandas as pd
import torch
from typing import Dict, Tuple, List
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset, DataLoader

class TradingDataset(Dataset):
    def __init__(self, 
                 data: pd.DataFrame,
                 sequence_length: int = 60,  # 60 minuti di storico
                 prediction_horizon: int = 5,  # 5 minuti in avanti
                 features: List[str] = None):
        """
        Parameters:
            data: DataFrame con timestamp index e colonne per features
            sequence_length: Lunghezza della sequenza di input
            prediction_horizon: Quanti step avanti predire
            features: Lista delle feature da usare (oltre a price e volume)
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        
        # Preprocessing
        self.price_scaler = StandardScaler()
        self.volume_scaler = StandardScaler()
        self.feature_scaler = StandardScaler()
        
        # Prepara i dati
        self.data = self._prepare_data(data, features)
        
    def _prepare_data(self, data: pd.DataFrame, features: List[str]) -> torch.Tensor:
        """Prepara e scala i dati"""
        # Estrai prezzi e volumi
        prices = self.price_scaler.fit_transform(data[['close']].values)
        volumes = self.volume_scaler.fit_transform(data[['volume']].values)
        
        # Prepara feature tecniche
        if features:
            technical_features = self.feature_scaler.fit_transform(data[features].values)
            # Concatena tutto
            all_features = np.concatenate([
                prices,
                volumes,
                technical_features
            ], axis=1)
        else:
            all_features = np.concatenate([prices, volumes], axis=1)
            
        return torch.FloatTensor(all_features)
    
    def __len__(self) -> int:
        return len(self.data) - self.sequence_length - self.prediction_horizon
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            x: Input sequence
            y: Target prices for next prediction_horizon steps
        """
        # Input sequence
        x = self.data[idx:idx + self.sequence_length]
        
        # Target sequence
        y = self.data[idx + self.sequence_length:
                     idx + self.sequence_length + self.prediction_horizon, 0]  # Solo prezzi
        
        return x, y

class DataPipeline:
    def __init__(self,
                 batch_size: int = 32,
                 sequence_length: int = 60,
                 prediction_horizon: int = 5,
                 train_split: float = 0.8,
                 features: List[str] = None):
        """
        Parameters:
            batch_size: Dimensione del batch
            sequence_length: Lunghezza della sequenza di input
            prediction_horizon: Quanti step avanti predire
            train_split: Frazione dei dati per training
            features: Lista delle feature tecniche da usare
        """
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.train_split = train_split
        self.features = features or []
        
    def prepare_data(self, data: pd.DataFrame) -> Dict[str, DataLoader]:
        """
        Prepara i data loader per training e validation
        """
        # Split train/validation
        train_size = int(len(data) * self.train_split)
        train_data = data.iloc[:train_size]
        val_data = data.iloc[train_size:]
        
        # Crea dataset
        train_dataset = TradingDataset(
            train_data,
            self.sequence_length,
            self.prediction_horizon,
            self.features
        )
        
        val_dataset = TradingDataset(
            val_data,
            self.sequence_length,
            self.prediction_horizon,
            self.features
        )
        
        # Crea data loaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )
        
        return {
            'train': train_loader,
            'val': val_loader,
            'price_scaler': train_dataset.price_scaler,
            'volume_scaler': train_dataset.volume_scaler,
            'feature_scaler': train_dataset.feature_scaler
        }
    
    def add_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Aggiunge feature tecniche al DataFrame
        """
        df = data.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (std * 2)
        df['bb_lower'] = df['bb_middle'] - (std * 2)
        
        # Average True Range (ATR)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Rimuovi righe con NaN
        df = df.dropna()
        
        return df