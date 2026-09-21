"""Generate TTS narration audio and missing frame assets for the Casework demo video."""
import json
import shutil
from pathlib import Path
import win32com.client
from scripts.agent.llm import ROOT

def main():
    folder = ROOT / 'docs/demo'
    frames = folder / 'frames'
    frames.mkdir(exist_ok=True, parents=True)
    
    # 1. Ensure overview.png and coordinated.png exist
    overview_dst = frames / 'overview.png'
    if not overview_dst.exists():
        dashboard_src = folder / 'dashboard.png'
        if dashboard_src.exists():
            shutil.copy(dashboard_src, overview_dst)
            print('Copied dashboard.png -> overview.png')
        else:
            # Fallback to existing frame
            shutil.copy(frames / '03-desktop-before.png', overview_dst)
            print('Copied 03-desktop-before.png -> overview.png')
            
    coordinated_dst = frames / 'coordinated.png'
    if not coordinated_dst.exists():
        shutil.copy(frames / 'actions.png', coordinated_dst)
        print('Copied actions.png -> coordinated.png')
        
    # 2. Generate TTS audio files for all scenes using SAPI.SpVoice
    scenes = json.loads((folder / 'scenes.json').read_text(encoding='utf-8'))
    
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.Rate = -1
    
    for i, s in enumerate(scenes):
        audio_path = folder / f"{i}.wav"
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(str(audio_path.resolve()), 3, False)
        voice.AudioOutputStream = stream
        voice.Speak(s['text'])
        stream.Close()
        print(f"Generated {i}.wav for scene '{s['title']}'")
        
    print(f"Successfully generated all {len(scenes)} TTS audio files and frame assets!")

if __name__ == '__main__':
    main()
