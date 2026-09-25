<div align="center">

# 🎙️ Streaming TD-PSOLA Real-Time Voice Changer

**CPU-only real-time voice conversion built around a stateful TD-PSOLA streaming engine, with independent pitch/formant control, hardware-free tests, and a reproducible offline benchmark.**

CPU-only 即時變聲器：以 stateful TD-PSOLA 串流引擎獨立控制音高與共振峰，附硬體無關測試與可重現 benchmark。

[![tests](https://github.com/yoyocar2333/realtime-voice-changer/actions/workflows/tests.yml/badge.svg)](https://github.com/yoyocar2333/realtime-voice-changer/actions)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

[English](#english) · [中文](#中文)

</div>

---

<a name="english"></a>
## English

### Why this exists

Most lightweight voice changers either sound like a chipmunk (naive resampling)
or like an anonymous TV whistleblower (phase vocoder). This one uses
**TD-PSOLA**, which works entirely in the time domain by replaying your own
pitch periods at a new spacing — so it stays natural and human. Pitch and
formant are controlled independently, which is what actually makes a male voice
sound female rather than just higher.

> 📐 Full DSP rationale and measurements in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Features

- 🎚️ **Natural pitch + formant conversion** (TD-PSOLA, no metallic artefact)
- 🎧 **Dual output** — sends to a virtual cable *and* your headphones, so you can
  hear yourself while Discord hears the changed voice
- 🎭 **9 presets** — young/mature female, loli, deep/mature male, robot, alien, cave
- 🎛️ **Manual trims** — pitch, 3-band EQ, gain layered on top of any preset
- 📊 Live meters, CPU readout, noise gate, settings persistence
- ⚡ **Real-time budget** — 1024 samples @ 44.1 kHz gives a 23.22 ms block budget; the reference offline run uses 1.80–2.80 ms p50 compute across the five voice presets
- 🧪 **Tested** — 19 hardware-free DSP tests in CI; the reproducible synthetic benchmark measures ≤0.33% F0 target error across five pitch presets
- 🖥️ GUI **and** headless CLI

### Install

```bash
git clone https://github.com/yoyocar2333/realtime-voice-changer.git
cd realtime-voice-changer
python -m pip install -r requirements.txt
```

> **Multiple Pythons?** Always use `python -m pip` so packages land in the
> interpreter that actually runs the app. In VS Code, pick the matching one via
> *Python: Select Interpreter*.

On macOS/Linux you may need PortAudio for `sounddevice`:
`brew install portaudio` / `sudo apt install libportaudio2`.

### Run

```bash
python -m voicechanger            # GUI
# or
./run.sh        (macOS/Linux)
run.bat         (Windows)
```

Headless / scripted:

```bash
python -m voicechanger --list-devices
python -m voicechanger --no-gui --preset 年輕女聲 --in 1 --out 7 --monitor 5
```

### Routing into Discord

You need a virtual audio cable so Discord can read the processed audio:

- **Windows** — [VB-Cable](https://vb-audio.com/Cable/) (run installer as admin, reboot)
- **macOS** — [BlackHole](https://existential.audio/blackhole/)
- **Linux** — a PulseAudio null sink

Then:

```
①Mic input  → your real microphone
②Output     → CABLE Input      → Discord hears this
③Monitor    → your headphones  → you hear this
```

In Discord: **Settings → Voice & Video → Input Device → `CABLE Output`**.

> ⚠️ `CABLE Input` and `CABLE Output` are intentionally swapped between the two
> apps. Use **headphones** for the monitor to avoid echo.

### Presets (measured on a 120 Hz male voice)

| Preset      | Output F0 | Notes                          |
| ----------- | --------- | ------------------------------ |
| 👩 成熟女聲 | ~160 Hz   | **cleanest** — try this first  |
| 👧 年輕女聲 | ~190 Hz   | natural young female           |
| 🎀 蘿莉音   | ~214 Hz   | anime-style, most processing   |
| 🧔 大叔低音 | ~85 Hz    | deep male                      |
| 👨 成熟男聲 | ~101 Hz   | natural lower male             |
| 🤖🤖 robot / 👽 alien / 🏔️ cave | — | effects |

### Honest limitations & going further (RVC)

Pure-DSP real-time conversion has a ceiling: it *moves* your voice, it doesn't
*regenerate* a target timbre, so big shifts still sound slightly synthetic.
For broadcast-quality, indistinguishable conversion use a neural model:

- **RVC (Retrieval-based Voice Conversion)** — realtime client:
  [w-okada/voice-changer](https://github.com/w-okada/voice-changer)
- Needs a decent GPU and a trained/target model, with higher latency.

This project is the lightweight, no-GPU, no-training option that's "good enough"
for casual use.

### Engineering evidence

The project is intentionally structured as a small DSP/systems portfolio project rather than only a GUI demo:

- `StreamPSOLA` is **stateful and block-based**: autocorrelation pitch tracking, analysis epochs, overlap-add synthesis, formant resampling, bounded streaming buffers.
- `AudioEngine.process()` is **hardware-independent**, so the complete DSP chain can be tested without a microphone or sound card.
- The real-time callback path includes FIFO priming, smoothed makeup gain, block-boundary de-clicking, noise-gate reset, EQ/effects, limiter, and a monitor ring buffer.
- CI covers pitch movement, preset ranges, harmonic preservation, clipping/NaN safety, silence, pitch glides, and ring-buffer wrap-around.

### Reproducible benchmark

Run:

```bash
python benchmarks/benchmark_offline.py
```

The script synthesizes a repeatable 120 Hz male `/a/` vowel and feeds the **actual `AudioEngine`** in 1024-sample blocks. A reference run on Python 3.13.5 / Linux x86_64 produced:

| Preset | Target F0 | Measured F0 | Error | p50 compute | Startup buffer |
|---|---:|---:|---:|---:|---:|
| 年輕女聲 | 190.5 Hz | 191.1 Hz | 0.33% | 2.76 ms | 69.7 ms |
| 成熟女聲 | 160.2 Hz | 160.6 Hz | 0.23% | 2.75 ms | 69.7 ms |
| 蘿莉音 | 213.8 Hz | 214.4 Hz | 0.29% | 2.80 ms | 69.7 ms |
| 大叔低音 | 84.9 Hz | 85.0 Hz | 0.17% | 1.80 ms | 46.4 ms |
| 成熟男聲 | 100.9 Hz | 101.1 Hz | 0.20% | 2.29 ms | 69.7 ms |

Compute time is host-dependent; the important comparison is against the **23.22 ms/block real-time budget**. Device/driver buffering is not included in the offline startup figure.

### Development

```bash
pip install -e ".[dev]"
pytest -q
python benchmarks/benchmark_offline.py
```

The tests synthesize glottal-source voices and assert that pitch shifting actually moves F0, presets land in the intended range, harmonics are preserved, and the stream never clicks, clips, or emits NaNs — all without audio hardware.

---

<a name="中文"></a>
## 中文

### 這個專案要解決什麼

大多數輕量變聲器不是像花栗鼠（單純重採樣），就是像電視爆料者那種金屬聲（相位聲碼器）。本專案用 **TD-PSOLA**，完全在時域操作：偵測你的基音週期，用新的間距重新排列、疊加，所以聲音自然、像真人。音高與共振峰**獨立控制**——這才是讓男聲真的像女聲、而不只是變高的關鍵。

> 📐 完整 DSP 原理與實測數據見 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

### 功能

- 🎚️ **自然的音高＋共振峰變換**（TD-PSOLA，無金屬感）
- 🎧 **雙輸出**——同時送虛擬音訊線給 Discord、送耳機給你自己監聽
- 🎭 **9 種預設**——年輕/成熟女聲、蘿莉、大叔/成熟男聲、機器人、外星人、洞穴
- 🎛️ **手動微調**——音調、三段 EQ、音量，疊加在任何預設上
- 📊 即時音量計、CPU 顯示、噪音門、設定自動記憶
- ⚡ **即時運算預算**——44.1 kHz / 1024 samples 每 block 有 23.22 ms；參考離線 benchmark 的五組聲線 p50 為 1.80–2.80 ms
- 🧪 **可驗證**——19 個不需音訊硬體的 DSP 測試；五組移調預設的合成語音 F0 目標誤差皆 ≤0.33%
- 🖥️ 圖形介面與命令列皆可

### 安裝

```bash
git clone https://github.com/yoyocar2333/realtime-voice-changer.git
cd realtime-voice-changer
python -m pip install -r requirements.txt
```

> **有多個 Python？** 一律用 `python -m pip`，套件才會裝到實際執行程式的那個直譯器。VS Code 可用 *Python: Select Interpreter* 切換。

### 執行

```bash
python -m voicechanger      # 圖形介面
```
或雙擊 `run.bat`（Windows）／執行 `./run.sh`（macOS/Linux）。

### 接到 Discord

需要虛擬音訊線路讓 Discord 收到變聲後的聲音：

- **Windows**：[VB-Cable](https://vb-audio.com/Cable/)（以系統管理員安裝後重開機）
- **macOS**：[BlackHole](https://existential.audio/blackhole/)
- **Linux**：PulseAudio null sink

三個欄位：

```
①麥克風  → 你的麥克風
②輸出    → CABLE Input   →Discord 收到這個
③監聽    → 你的耳機       →你自己聽這個
```

Discord：**設定 → 語音與視訊 → 輸入裝置 → `CABLE Output`**。

> ⚠️ `CABLE Input` 與 `CABLE Output` 在兩個程式裡剛好相反。監聽請**戴耳機**避免回音。

### 預設（以 120Hz 男聲實測）

| 預設 | 輸出基頻 | 說明 |
|------|----------|------|
| 👩 成熟女聲 | ~160 Hz | **最乾淨**，建議先試 |
| 👧 年輕女聲 | ~190 Hz | 自然年輕女聲 |
| 🎀 蘿莉音  | ~214 Hz | 動漫風，處理最多 |
| 🧔 大叔低音 | ~85 Hz | 渾厚男聲 |
| 👨 成熟男聲 | ~101 Hz | 自然低沉男聲 |

### 書審 / 工程重點

這個 repo 的核心不是 GUI，而是可驗證的串流 DSP：

- `StreamPSOLA`：自相關基頻偵測、analysis epoch、overlap-add、formant resampling、bounded streaming buffer。
- `AudioEngine.process()` 完全不依賴音訊硬體，可離線測整條 DSP pipeline。
- 19 個 CI 測試涵蓋移調正確性、harmonic preservation、silence/glide、clipping/NaN 與 ring buffer。
- `python benchmarks/benchmark_offline.py` 可重現五組聲線的 F0 誤差與每 block 運算時間；參考結果的最大 F0 誤差為 **0.33%**。

### 誠實的限制與進階（RVC）

純 DSP 即時變聲有天花板：它是「搬移」你的聲音、不是「重新生成」目標音色，所以移調多時仍會有點人工感。若要做到幾乎聽不出來的擬真轉換，需要神經網路模型：

- **RVC**：即時版 [w-okada/voice-changer](https://github.com/w-okada/voice-changer)
- 需要像樣的 GPU 與訓練好的目標模型，延遲也較高。

本專案是不需 GPU、不需訓練、日常用「夠好」的輕量選擇。

---

## License

[MIT](LICENSE) © NTUquantum

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md).
