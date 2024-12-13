"""
Test suite for data pipeline
"""
import unittest
import pandas as pd
import numpy as np
from src.models.data_pipeline import DataPipeline, TradingDataset

class TestDataPipeline(unittest.TestCase):
    def setUp(self):
        """Crea dati di test"""
        # Crea dati finti
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
        
        self.test_data = pd.DataFrame({
            'open': np.random.randn(1000).cumsum() + 100,
            'high': np.random.randn(1000).cumsum() + 102,
            'low': np.random.randn(1000).cumsum() + 98,
            'close': np.random.randn(1000).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 1000)
        }, index=dates)
        
        self.pipeline = DataPipeline(
            batch_size=32,
            sequence_length=60,
            prediction_horizon=5
        )
    
    def test_technical_features(self):
        """Test aggiunta feature tecniche"""
        df = self.pipeline.add_technical_features(self.test_data)
        
        # Verifica che tutte le feature attese siano presenti
        expected_features = ['rsi', 'macd', 'signal', 'bb_middle', 
                           'bb_upper', 'bb_lower', 'atr']
        for feature in expected_features:
            self.assertIn(feature, df.columns)
        
        # Verifica che non ci siano NaN
        self.assertFalse(df.isnull().any().any())
    
    def test_data_preparation(self):
        """Test preparazione dei data loader"""
        data = self.pipeline.add_technical_features(self.test_data)
        loaders = self.pipeline.prepare_data(data)
        
        # Verifica che ci siano tutti i componenti attesi
        self.assertIn('train', loaders)
        self.assertIn('val', loaders)
        self.assertIn('price_scaler', loaders)
        self.assertIn('volume_scaler', loaders)
        self.assertIn('feature_scaler', loaders)
        
        # Test dimensioni batch
        x, y = next(iter(loaders['train']))
        self.assertEqual(x.shape[0], 32)  # batch size
        self.assertEqual(x.shape[1], 60)  # sequence length
        self.assertEqual(y.shape[1], 5)   # prediction horizon

    def test_scaling(self):
        """Test che lo scaling funzioni correttamente"""
        data = self.pipeline.add_technical_features(self.test_data)
        loaders = self.pipeline.prepare_data(data)
        
        # Prendi un batch
        x, _ = next(iter(loaders['train']))
        
        # Verifica che i dati siano scalati (media ≈ 0, std ≈ 1)
        self.assertTrue(-1 < x.mean() < 1)
        self.assertTrue(0.5 < x.std() < 1.5)

if __name__ == '__main__':
    unittest.main()