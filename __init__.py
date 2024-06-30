# Set the web directory, any .js file in that directory will be loaded by the frontend as a frontend extension
WEB_DIRECTORY = "./web"

from .nodes import MARS5TTS_Node,TTSTextEncode,LoadAudioPath,PreViewAudio
# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "MARS5TTS_Node":MARS5TTS_Node,
    "TTSTextEncode":TTSTextEncode,
    "LoadAudioPath":LoadAudioPath,
    "PreViewAudio": PreViewAudio
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "MARS5TTS_Node":"MARS5-TTS Node",
    "TTSTextEncode":"TTSTextEncode",
    "LoadAudioPath":"LoadAudioPath",
    "PreViewAudio": "PreViewAudio"
}