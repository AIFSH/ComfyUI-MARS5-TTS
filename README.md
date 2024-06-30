# ComfyUI-MARS5-TTS
a comfyui custom node for [MARS5-TTS](https://github.com/Camb-ai/MARS5-TTS)

## Example
input
- [ref_audio](./doc/trump.MP3)

<div>
  <audio controls src="doc/trump.MP3?raw=true" width="600px"/>
</div>

-  reference text

```
we're going to make America great again. we're a failing nation right now. we're a seriously failing nation
```
output
- [tts_output_audio](./doc/mars5_1719705960726329200.wav)

<div>
  <audio controls src="doc/mars5_1719705960726329200.wav?raw=true" width="600px"/>
</div>

## How to use
```
## in ComfyUI/custom_nodes/
git clone https://github.com/AIFSH/ComfyUI-MARS5-TTS.git
cd ComfyUI-MARS5-TTS
pip install -r requirements.txt
```
`weights` will be downloaded from huggingface 

## Tutorial
[Demo]()

## Thanks
[MARS5-TTS](https://github.com/Camb-ai/MARS5-TTS)
