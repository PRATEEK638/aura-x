#!/usr/bin/env python3
"""
Aura-X CLI — Interactive AI Assistant
Text-first interface. Voice output optional (toggle with /voice).
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    # ── Console setup ───────────────────────────────────────────────────
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        console = Console()
        R = True
    except ImportError:
        R = False
        console = None

    def cprint(text, style=""):
        if R:
            console.print(f"[{style}]{text}[/{style}]" if style else text)
        else:
            print(text)

    def cpanel(text, title="Aura-X"):
        if R:
            console.print(Panel(text, title=f"[bold cyan]{title}[/bold cyan]",
                                border_style="cyan", padding=(0, 1)))
        else:
            print(f"\n🤖 {title}: {text}\n")

    def cerr(text):
        cprint(f"✗ {text}", "red")

    def cinfo(text):
        cprint(f"  {text}", "dim")

    # ── Banner ──────────────────────────────────────────────────────────
    if R:
        b = Text()
        b.append("\n ╔════════════════════════════════════════╗\n", style="bright_cyan")
        b.append(" ║    ", style="bright_cyan")
        b.append("⚡ AURA-X", style="bold bright_white on blue")
        b.append("  AI Desktop Assistant    ", style="bright_cyan")
        b.append("║\n", style="bright_cyan")
        b.append(" ╚════════════════════════════════════════╝\n", style="bright_cyan")
        console.print(b)
    else:
        print("\n" + "=" * 42)
        print("   ⚡ AURA-X — AI Desktop Assistant")
        print("=" * 42)

    cinfo("Initializing...")

    # ── Init assistant ──────────────────────────────────────────────────
    try:
        from core.assistant import AuraXAssistant
        assistant = AuraXAssistant()
        assistant.start()
    except Exception as e:
        cerr(f"Init failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    speaker = assistant.speaker

    # ── Check what's available ──────────────────────────────────────────
    cinfo(f"Voice Output: {'✓ edge-tts ready' if speaker and speaker._available else '✗ Not available'}")

    # Check voice input
    voice_in = False
    recognizer = None
    mic = None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        voice_in = True
        cinfo("Voice Input:  ✓ Microphone detected")
    except Exception as e:
        cinfo(f"Voice Input:  ✗ ({e})")

    # Check Ollama
    try:
        if assistant.ai_router.ollama.is_healthy():
            models = assistant.ai_router.ollama.list_models()
            cinfo(f"Ollama:       ✓ {len(models)} models ({', '.join(models[:3])})")
        else:
            cerr("Ollama:       ✗ Not running! Start: ollama serve")
    except Exception:
        cerr("Ollama:       ✗ Cannot connect")

    cinfo(f"Tools:        {len(assistant.tool_executor.list_tools())} available")

    # ── State ───────────────────────────────────────────────────────────
    listening_mode = False
    voice_speak = False  # Voice OFF by default — user toggles with /voice

    # ── Helper: respond (text only, voice optional) ─────────────────────
    def respond(text: str):
        """Print response. Speak only if voice mode is on."""
        cpanel(text)
        if voice_speak and speaker and speaker._available:
            speaker.speak(text)

    # ── Helper: listen for voice ────────────────────────────────────────
    def listen_once() -> str:
        if not voice_in:
            return ""
        try:
            cinfo("🎤 Listening... (speak now)")
            with mic as source:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            cinfo("🔄 Transcribing...")
            text = recognizer.recognize_google(audio)
            if text:
                cprint(f"  🎤 You said: \"{text}\"", "green")
                return text
        except Exception as e:
            if "timed out" not in str(e).lower():
                cinfo(f"  (couldn't hear: {e})")
        return ""

    # ── Helper: process and respond ─────────────────────────────────────
    def process(user_text: str):
        if not user_text.strip():
            return
        if R:
            with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = assistant.process_input(user_text)
        else:
            cinfo("Thinking...")
            response = assistant.process_input(user_text)
        respond(response)

    # ── Startup greeting (text only) ────────────────────────────────────
    respond("Hello Boss! I'm Aura-X, your AI assistant. What can I do for you?")

    # ── Commands help ───────────────────────────────────────────────────
    cinfo("")
    cinfo("Commands:  /voice   — Toggle voice output (currently OFF)")
    cinfo("           /listen  — Toggle continuous voice input")
    cinfo("           /mic     — One-shot voice input")
    cinfo("           /status  — System status")
    cinfo("           /tools   — List tools")
    cinfo("           /clear   — Clear memory")
    cinfo("           /quit    — Exit")
    cinfo("  Or just type your message\n")

    # ── Continuous voice listening loop ──────────────────────────────────
    def voice_loop():
        nonlocal listening_mode
        while listening_mode:
            text = listen_once()
            if text:
                if speaker and speaker.is_speaking():
                    speaker.stop_speaking()
                process(text)
            time.sleep(0.2)

    # ── Main loop ───────────────────────────────────────────────────────
    while True:
        try:
            if R:
                user_input = console.input("[bold green]You:[/bold green] ").strip()
            else:
                user_input = input("You: ").strip()

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ("/quit", "/exit", "/q"):
                listening_mode = False
                cinfo("Shutting down...")
                respond("Goodbye Boss, take care!")
                time.sleep(1)
                assistant.stop()
                break

            elif cmd == "/listen":
                if not voice_in:
                    cerr("Microphone not available. Install: pip install SpeechRecognition pyaudio")
                    continue
                listening_mode = not listening_mode
                if listening_mode:
                    respond("Voice mode ON — I'm listening!")
                    threading.Thread(target=voice_loop, daemon=True, name="VoiceLoop").start()
                else:
                    respond("Voice mode OFF — type your messages.")
                continue

            elif cmd == "/mic":
                if not voice_in:
                    cerr("Microphone not available.")
                    continue
                text = listen_once()
                if text:
                    if speaker and speaker.is_speaking():
                        speaker.stop_speaking()
                    process(text)
                continue

            elif cmd == "/voice":
                voice_speak = not voice_speak
                state = "ON" if voice_speak else "OFF"
                cinfo(f"Voice output: {state}")
                if voice_speak and speaker and speaker._available:
                    cinfo("  (responses will be spoken aloud)")
                elif voice_speak and (not speaker or not speaker._available):
                    cerr("  edge-tts not available. Install: pip install edge-tts pygame")
                    voice_speak = False
                continue

            elif cmd == "/status":
                status = assistant.get_system_status()
                if R:
                    from rich.table import Table
                    t = Table(title="System Status", border_style="cyan")
                    t.add_column("Component", style="bold")
                    t.add_column("Status")
                    t.add_row("Running", "✓" if status["running"] else "✗")
                    t.add_row("Voice Out", f"{'✓ ON' if voice_speak else '✗ OFF'}")
                    t.add_row("Voice In", "✓ Listening" if listening_mode else ("✓ Ready" if voice_in else "✗"))
                    t.add_row("Last Model", status["ai_stats"].get("last_model", "none"))
                    mem = status.get("memory_stats", {}).get("short_term", {})
                    t.add_row("Memory", f"{mem.get('current_messages', 0)} msgs")
                    t.add_row("Tools", str(len(status.get("tools", []))))
                    console.print(t)
                else:
                    print(f"  Running: {status['running']}, Voice: {voice_speak}")
                    print(f"  Model: {status['ai_stats'].get('last_model', 'none')}")
                continue

            elif cmd == "/tools":
                tools = assistant.tool_executor.list_tools()
                cinfo(f"Available tools ({len(tools)}):")
                for tool in sorted(tools):
                    cinfo(f"  • {tool}")
                continue

            elif cmd == "/clear":
                assistant.memory_manager.clear_short_term()
                cinfo("Memory cleared.")
                continue

            elif cmd == "/help":
                cinfo("Commands:")
                cinfo("  /voice  — Toggle voice output")
                cinfo("  /listen — Toggle continuous voice input")
                cinfo("  /mic    — One-shot voice input")
                cinfo("  /status — System status")
                cinfo("  /tools  — List available tools")
                cinfo("  /clear  — Clear conversation memory")
                cinfo("  /quit   — Exit")
                continue

            elif cmd.startswith("/"):
                cerr(f"Unknown: {cmd}. Try /help")
                continue

            # ── Process text input ──────────────────────────────────────
            process(user_input)

        except KeyboardInterrupt:
            print()
            listening_mode = False
            cinfo("Shutting down...")
            respond("Goodbye Boss!")
            time.sleep(1)
            assistant.stop()
            break
        except EOFError:
            break
        except Exception as e:
            cerr(f"Error: {e}")


if __name__ == "__main__":
    main()
