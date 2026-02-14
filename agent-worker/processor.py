"""Event processor for transcript events"""
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for conversation engine (Docker volume mounts)
sys.path.append('/src')

from session_manager import SessionManager
from turn_manager import TurnManager


class EventProcessor:
    """Process transcript events and generate bot responses"""
    
    def __init__(
        self, 
        session_manager: SessionManager,
        turn_manager: TurnManager,
        meeting_engine
    ):
        self.session_manager = session_manager
        self.turn_manager = turn_manager
        self.meeting_engine = meeting_engine
    
    async def process_event(self, event: Dict[str, Any]):
        """
        Process a transcript event from Redis queue
        
        Args:
            event: {
                "type": "transcript",
                "bot_id": "...",
                "meeting_url": "...",
                "participant": {"id": "...", "name": "..."},
                "text": "...",
                "timestamp": "..."
            }
        """
        try:
            bot_id = event["bot_id"]
            text = event["text"]
            participant = event["participant"]
            participant_name = participant.get("name", "Unknown")
            
            print(f"\n{'='*70}")
            print(f"🎯 [WORKER] Processing transcript event")
            print(f"   Bot ID: {bot_id[:8]}...")
            print(f"   Speaker: {participant_name}")
            print(f"   Text: {text}")
            
            # Decision: Should we respond?
            should_respond, reason = self.turn_manager.should_respond_with_reason(text, participant_name)
            print(f"   🤔 Turn decision: {reason}")
            
            if not should_respond:
                print(f"   ⏭️  Skipping response")
                print(f"{'='*70}\n")
                return
            
            print(f"   ✅ Wake word detected! Will respond...")
            
            # Check if bot is currently speaking
            is_speaking = await self.turn_manager.is_speaking(bot_id)
            
            if is_speaking and self.turn_manager.should_interrupt(text):
                print(f"🛑 Interrupting current response (barge-in)")
                self.meeting_engine.cancel_response(bot_id)
                # Wait briefly for cancellation to complete
                import asyncio
                await asyncio.sleep(0.1)
            
            # Get conversation history
            session = await self.session_manager.get_session(bot_id)
            history = session.get("history", [])
            
            # Add user message to history
            await self.session_manager.add_message(bot_id, "user", text)
            
            # Mark bot as speaking
            await self.turn_manager.set_speaking(bot_id, True)
            
            start_time = datetime.utcnow()
            
            try:
                print(f"   📊 Session: {len(history)} messages in history")
                print(f"{'='*70}\n")
                
                # Process with conversation engine
                # This calls: LLM streaming -> sentence chunking -> parallel TTS -> audio upload
                metrics = await self.meeting_engine.process_text_to_audio(
                    text=text,
                    bot_id=bot_id,
                    history=history
                )
                
                # Add bot response to history
                response_text = metrics.get("response_text", "")
                await self.session_manager.add_message(bot_id, "assistant", response_text)
                
                # Log metrics
                self._log_metrics(bot_id, participant_name, text, metrics)
                
            finally:
                # Mark bot as done speaking
                await self.turn_manager.set_speaking(bot_id, False)
        
        except Exception as e:
            print(f"❌ Error processing event: {e}")
            import traceback
            traceback.print_exc()
    
    def _log_metrics(
        self, 
        bot_id: str, 
        participant: str, 
        text: str, 
        metrics: Dict[str, Any]
    ):
        """Log detailed metrics in a readable format"""
        print("\n" + "="*60)
        print(f"📊 METRICS - Bot: {bot_id[:8]}...")
        print(f"👤 User: {participant}")
        print(f"💬 Input: {text[:80]}...")
        print("-"*60)
        
        if "llm" in metrics:
            llm = metrics["llm"]
            print(f"🤖 LLM First Token: {llm.get('first_token_time', 0)*1000:.0f}ms")
            print(f"🤖 LLM Total Time: {llm.get('total_time', 0)*1000:.0f}ms")
        
        if "tts" in metrics:
            tts = metrics["tts"]
            print(f"🎵 TTS Chunks: {tts.get('calls', 0)}")
            print(f"🎵 TTS Total Time: {tts.get('total_time', 0)*1000:.0f}ms")
        
        if "total" in metrics:
            total = metrics["total"]
            print(f"⚡ TTFA (Time to First Audio): {total.get('ttfa', 0)*1000:.0f}ms")
            print(f"⏱️  Total Response Time: {total.get('time', 0)*1000:.0f}ms")
        
        print("="*60 + "\n")
