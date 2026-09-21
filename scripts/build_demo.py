"""Compose an edited, narrated walkthrough from actual CUA browser captures."""
import json
import subprocess
import wave
from pathlib import Path
import imageio_ffmpeg
from scripts.agent.llm import ROOT

def main():
    folder=ROOT/'docs/demo'; segments=folder/'segments';segments.mkdir(exist_ok=True)
    scenes=json.loads((folder/'scenes.json').read_text(encoding='utf-8'))
    exe=imageio_ffmpeg.get_ffmpeg_exe(); total=0; files=[]
    for i,s in enumerate(scenes):
        source=folder/'frames'/s['image'];audio=folder/(str(i)+'.wav')
        if not source.exists() or not audio.exists():raise RuntimeError('Missing demo capture or narration: '+str(source))
        with wave.open(str(audio)) as w: duration=max(28,w.getnframes()/w.getframerate()+1)
        total+=duration
        title=segments/(str(i)+'.txt');title.write_text(s['title'],encoding='utf-8')
        # Relative filter paths avoid Windows drive-letter escaping.
        title_path='segments/'+str(i)+'.txt'
        vf="scale=1440:810:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:70:color=0x0b1218,drawbox=x=0:y=0:w=iw:h=65:color=0x0b1218:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='"+title_path+"':fontsize=30:fontcolor=white:x=35:y=16,drawbox=x=0:y=860:w=iw:h=40:color=0x0b1218:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='Edited walkthrough | Actual application captures | Simulated customer responses':fontsize=18:fontcolor=0x8be2c2:x=35:y=870"
        out=segments/(str(i)+'.mp4')
        subprocess.run([exe,'-y','-loglevel','error','-loop','1','-framerate','5','-i',str(source),'-i',str(audio),'-vf',vf,'-af','apad','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-ar','44100',str(out)],cwd=folder,check=True)
        files.append("file '"+str(i)+".mp4'")
    if not 180<=total<=300:raise RuntimeError('Demo duration outside 3–5 minutes: '+str(total))
    concat=segments/'list.txt';concat.write_text('\n'.join(files),encoding='utf-8')
    subprocess.run([exe,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(folder/'casework-demo.mp4')],check=True)
    (folder/'video_manifest.json').write_text(json.dumps({'duration_seconds':total,'scenes':len(scenes),'format':'Edited actual-UI screenshot walkthrough with synthetic narration','customer_responses':'explicit simulations'},indent=2))
    print('Created demo:',round(total,1),'seconds')

if __name__=='__main__':main()
