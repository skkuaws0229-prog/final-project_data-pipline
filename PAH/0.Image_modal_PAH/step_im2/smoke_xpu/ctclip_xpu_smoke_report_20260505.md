# CT-CLIP XPU Smoke Test

- Patient: `ID00007637202177411956430`
- Device: `Intel(R) Arc(TM) 140T GPU (16GB)`
- Input tensor: `[1, 1, 240, 480, 480]`
- Encoded tokens: `[1, 24, 24, 24, 512]`
- Image embedding: `[1, 512]`
- Missing weight keys: `0`
- Unexpected weight keys: `1`
- Preprocess seconds: `0.14`
- Model load seconds: `7.14`
- XPU inference seconds: `16.85`

CPU fallback was intentionally not used.