import os,sys
now_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(now_dir)

import time
import torch
import librosa
import cuda_malloc
import folder_paths
import soundfile as sf
from .inference import Mars5TTS,InferenceConfig as config_class

ckpts_dir = os.path.join(now_dir, "checkpoints")
output_dir = folder_paths.get_output_directory()
input_dir = folder_paths.get_input_directory()
device = "cuda" if cuda_malloc.cuda_malloc_supported() else "cpu"
class MARS5TTS_Node:
    def __init__(self):
        self.mars5_tts = None
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "text": ("TEXT",),
                "ref_voice": ("AUDIOPATH",),
                "if_deep_clone":("BOOLEAN",{
                    "default": True
                }),
                "rep_penalty_window":("INT",{
                    "default": 100
                }),
                "top_k":("INT",{
                    "default": 100
                }),
                "temperature":("FLOAT",{
                    "default": 0.7,
                    "min":0.,
                    "max":1.0,
                    "display": "slider"
                }),
                "freq_penalty":("INT",{
                    "default": 3
                }),

            },
            "optional":{
                "ref_transcript":("TEXT",),
            }
        }
    
    RETURN_TYPES = ("AUDIOPATH",)
    #RETURN_NAMES = ("image_output_name",)

    FUNCTION = "tts"

    #OUTPUT_NODE = False

    CATEGORY = "AIFSH_MARS5_TTS"

    def tts(self,text,ref_voice,if_deep_clone,rep_penalty_window,
            top_k,temperature,freq_penalty,ref_transcript=None):
        if self.mars5_tts:
            self.mars5_tts.to(device)
        else:
            # load model
            self.mars5_tts = Mars5TTS.from_pretrained("CAMB-AI/MARS5-TTS",local_dir=ckpts_dir)
            self.mars5_tts.to(device)
            self.mars5_tts.eval()
        
        if if_deep_clone:
            assert ref_transcript, "deep clone need ref_transcript,but you give nothing!"
        cfg = config_class(temperature=temperature,
                           top_k=top_k,
                           freq_penalty=freq_penalty,
                           rep_penalty_window=rep_penalty_window,
                           deep_clone=if_deep_clone)

        ref_wav, sr = librosa.load(ref_voice,sr=self.mars5_tts.sr,mono=True)
        ref_wav = torch.from_numpy(ref_wav)
        ref_wav.to(device)
        print("may take a while,wait ...")
        ar_codes, output_wav = self.mars5_tts.tts(text,ref_wav,ref_transcript,cfg=cfg)
        outfile = os.path.join(output_dir,f"mars5_{time.time_ns()}.wav")
        sf.write(outfile,output_wav,sr)
        return (outfile, )


class TTSTextEncode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True, 
                    "dynamicPrompts": True
                    }), 
            }
        }
    RETURN_TYPES = ("TEXT",)
    FUNCTION = "get_text"

    CATEGORY = "AIFSH_MARS5_TTS"

    def get_text(self,text):
        return (text,)

class PreViewAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"audio_path": ("AUDIOPATH",),}
                }

    CATEGORY = "AIFSH_MARS5_TTS"
    DESCRIPTION = "hello world!"

    RETURN_TYPES = ()

    OUTPUT_NODE = True

    FUNCTION = "load_audio"

    def load_audio(self, audio):
        audio_name = os.path.basename(audio)
        tmp_path = os.path.dirname(audio)
        audio_root = os.path.basename(tmp_path)
        return {"ui": {"audio":[audio_name,audio_root]}}

class LoadAudioPath:
    @classmethod
    def INPUT_TYPES(s):
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and f.split('.')[-1].lower() in ["wav", "mp3","flac","m4a"]]
        return {"required":
                    {"audio": (sorted(files),)},
                }

    CATEGORY = "AIFSH_MARS5_TTS"

    RETURN_TYPES = ("AUDIOPATH",)
    FUNCTION = "load_audio"

    def load_audio(self, audio):
        audio_path = folder_paths.get_annotated_filepath(audio)
        return (audio_path,)
