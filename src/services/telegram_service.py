"""
Servizio di notifiche Telegram per il Trading Assistant
"""
import os
import asyncio
from telegram import (
    Bot, 
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from datetime import datetime
from typing import Dict

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.pending_orders = {}
        self.setup_bot()

    def setup_bot(self):
        """Inizializza il bot e i suoi handler"""
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CallbackQueryHandler(self._button_callback))

    async def start(self):
        """Avvia il bot"""
        await self.app.initialize()
        await self.app.start()
        print("🤖 Trading Assistant Bot started!")

    async def stop(self):
        """Ferma il bot"""
        await self.app.stop()

    async def send_trade_signal(self, signal_data: Dict) -> bool:
        """
        Invia segnale di trading e richiede autorizzazione
        """
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')
        self.pending_orders[order_id] = signal_data
        
        message = self._format_signal_message(signal_data, order_id)
        keyboard = self._create_approval_keyboard(order_id)
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            print(f"Error sending signal: {e}")
            return False

    def _format_signal_message(self, signal: Dict, order_id: str) -> str:
        """Formatta il messaggio del segnale"""
        return (
            f"🚨 <b>Trading Signal</b> 🚨\n\n"
            f"Symbol: {signal['symbol']}\n"
            f"Action: {signal['signal']}\n"
            f"Entry Price: {signal['current_price']:.8f}\n"
            f"Target: {signal['target_price']:.8f}\n"
            f"Stop Loss: {signal['stop_loss']:.8f}\n\n"
            f"Confidence: {signal['confidence']:.2%}\n"
            f"Risk/Reward: {signal['risk_reward']:.2f}\n"
            f"Position Size: {signal['position_size']:.8f}\n\n"
            f"Analysis:\n"
            f"- Technical Score: {signal.get('technical_score', 0):.2%}\n"
            f"- Risk Score: {signal.get('risk_score', 0):.2%}\n"
            f"- Volatility: {signal.get('volatility', 0):.2%}\n\n"
            f"Order ID: {order_id}\n\n"
            f"Do you want to execute this trade?"
        )

    def _create_approval_keyboard(self, order_id: str) -> InlineKeyboardMarkup:
        """Crea la tastiera per l'approvazione"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _start_command(self, update, context):
        """Handler per il comando /start"""
        await update.message.reply_text(
            "🤖 Welcome to Trading Assistant Bot!\n\n"
            "I will send you trading signals and wait for your approval "
            "before executing any trades."
        )

    async def _button_callback(self, update, context):
        """Handler per le risposte ai bottoni"""
        query = update.callback_query
        action, order_id = query.data.split('_')
        
        if order_id not in self.pending_orders:
            await query.answer("Order expired or already processed")
            return
            
        signal_data = self.pending_orders[order_id]
        
        if action == "approve":
            await query.edit_message_text(
                f"✅ Order Approved!\n\n"
                f"Executing trade for {signal_data['symbol']}..."
            )
            # Qui implementeremo l'esecuzione dell'ordine
        else:
            await query.edit_message_text(
                f"❌ Order Rejected\n\n"
                f"Signal for {signal_data['symbol']} has been cancelled."
            )
        
        del self.pending_orders[order_id]