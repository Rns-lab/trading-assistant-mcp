"""
Transformer model for 1-minute price predictions with trading-specific optimizations
"""
from __future__ import annotations
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Union

class TradingTransformer(nn.Module):
   def __init__(self, 
                input_size: int,
                d_model: int = 256,
                nhead: int = 8,
                num_layers: int = 6,
                dropout: float = 0.1,
                prediction_horizon: int = 5,  # Predice 5 minuti in avanti
                confidence_threshold: float = 0.7) -> None:
       super().__init__()
       
       self.input_size = input_size
       self.confidence_threshold = confidence_threshold
       self.prediction_horizon = prediction_horizon
       
       # Feature embedding
       self.price_embedding = nn.Linear(1, d_model // 4)
       self.volume_embedding = nn.Linear(1, d_model // 4)
       self.technical_embedding = nn.Linear(input_size - 2, d_model // 2)  # Per indicatori tecnici
       
       self.embedding_dropout = nn.Dropout(dropout)
       self.layer_norm = nn.LayerNorm(d_model)
       
       # Position encoding migliorato per time series
       self.position_encoding = self.create_position_encoding(d_model)
       
       # Transformer layers con attention mask per serie temporali
       encoder_layer = nn.TransformerEncoderLayer(
           d_model=d_model,
           nhead=nhead,
           dropout=dropout,
           batch_first=True,
           activation='gelu'  # GELU invece di ReLU per migliori performance
       )
       
       self.transformer_encoder = nn.TransformerEncoder(
           encoder_layer,
           num_layers=num_layers
       )
       
       # Output heads
       self.price_predictor = nn.Sequential(
           nn.Linear(d_model, d_model // 2),
           nn.GELU(),
           nn.Dropout(dropout),
           nn.Linear(d_model // 2, prediction_horizon)  # Predice n steps avanti
       )
       
       self.confidence_predictor = nn.Sequential(
           nn.Linear(d_model, d_model // 2),
           nn.GELU(),
           nn.Dropout(dropout),
           nn.Linear(d_model // 2, prediction_horizon),
           nn.Sigmoid()  # Confidence score tra 0 e 1
       )
       
       self.volatility_predictor = nn.Sequential(
           nn.Linear(d_model, d_model // 2),
           nn.GELU(),
           nn.Dropout(dropout),
           nn.Linear(d_model // 2, prediction_horizon),
           nn.Softplus()  # Volatilità sempre positiva
       )

   def create_position_encoding(self, d_model: int, max_len: int = 1000) -> torch.Tensor:
       position = torch.arange(max_len).unsqueeze(1)
       div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
       
       pos_encoding = torch.zeros(max_len, d_model)
       pos_encoding[:, 0::2] = torch.sin(position * div_term)
       pos_encoding[:, 1::2] = torch.cos(position * div_term)
       
       return pos_encoding
   
   def create_attention_mask(self, seq_len: int) -> torch.Tensor:
       """Crea una mask causale per l'attention"""
       mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1)
       return mask == 1
   
   def embed_features(self, x: torch.Tensor) -> torch.Tensor:
       """Embedding separato per diverse feature"""
       price = x[:, :, 0].unsqueeze(-1)
       volume = x[:, :, 1].unsqueeze(-1)
       technical = x[:, :, 2:]
       
       price_emb = self.price_embedding(price)
       volume_emb = self.volume_embedding(volume)
       technical_emb = self.technical_embedding(technical)
       
       # Concatena gli embedding
       x = torch.cat([price_emb, volume_emb, technical_emb], dim=-1)
       return self.layer_norm(self.embedding_dropout(x))

   def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
       """
       Forward pass con multiple predictions
       Returns:
           Dict con price predictions, confidence scores e volatility estimates
       """
       batch_size, seq_len, _ = x.shape
       
       # Embedding
       x = self.embed_features(x)
       
       # Aggiungi position encoding
       x = x + self.position_encoding[:seq_len].unsqueeze(0)
       
       # Crea attention mask
       mask = self.create_attention_mask(seq_len)
       
       # Transformer encoding
       x = self.transformer_encoder(x, mask=mask)
       
       # Predictions
       price_preds = self.price_predictor(x[:, -1])
       confidence = self.confidence_predictor(x[:, -1])
       volatility = self.volatility_predictor(x[:, -1])
       
       return {
           'price_predictions': price_preds,
           'confidence_scores': confidence,
           'volatility_estimates': volatility
       }
   
   def get_trading_signal(self, 
                         predictions: Dict[str, torch.Tensor],
                         current_price: float) -> Dict[str, Union[str, float, int]]:
       """
       Genera segnali di trading basati su predictions e confidence
       """
       with torch.no_grad():
           prices = predictions['price_predictions'].squeeze()
           confidence = predictions['confidence_scores'].squeeze()
           volatility = predictions['volatility_estimates'].squeeze()
           
           # Prendi la predizione più vicina con confidence alta
           high_confidence_mask = confidence > self.confidence_threshold
           if not high_confidence_mask.any():
               return {'signal': 'HOLD', 'confidence': 0.0, 'target_price': current_price}
           
           # Prendi la prima predizione con alta confidence
           first_confident_idx = high_confidence_mask.nonzero()[0][0]
           predicted_price = prices[first_confident_idx].item()
           conf_score = confidence[first_confident_idx].item()
           vol_estimate = volatility[first_confident_idx].item()
           
           # Calcola il segnale
           price_change = (predicted_price - current_price) / current_price
           
           if price_change > vol_estimate:
               signal = 'BUY'
           elif price_change < -vol_estimate:
               signal = 'SELL'
           else:
               signal = 'HOLD'
               
           return {
               'signal': signal,
               'confidence': conf_score,
               'target_price': predicted_price,
               'volatility': vol_estimate,
               'prediction_minutes_ahead': first_confident_idx + 1
           }