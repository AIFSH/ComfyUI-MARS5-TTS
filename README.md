# ComfyUI-MARS5-TTS
a comfyui custom node for [MARS5-TTS](https://github.com/Camb-ai/MARS5-TTS)
- [workfolw](./doc/mars_uvr5_workflow.json)

## Example
input
- [ref_audio](./doc/trump.MP3)

https://github.com/AIFSH/ComfyUI-MARS5-TTS/assets/149982694/4e85b99d-4472-482f-b520-e63592f3c4a2

-  reference text

```
we're going to make America great again. we're a failing nation right now. we're a seriously failing nation
```
output
- [tts_output_audio](./doc/mars5_1719705960726329200.wav)
  
https://github.com/AIFSH/ComfyUI-MARS5-TTS/assets/149982694/ce64c69e-4db8-47b1-ae31-9d173d772047

## How to use
```
## in ComfyUI/custom_nodes/
git clone https://github.com/AIFSH/ComfyUI-MARS5-TTS.git
cd ComfyUI-MARS5-TTS
pip install -r requirements.txt
```
`weights` will be downloaded from huggingface 

## Tutorial
【MARS5-TTS | ComfyUI插件来了，会是英文版的SeedTTS开源平替吗？-哔哩哔哩】 https://b23.tv/etjjwVd

## Thanks
[MARS5-TTS](https://github.com/Camb-ai/MARS5-TTS)
