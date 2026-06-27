<div align="center">

# 🎙️ Realtime Voice Changer

**Lightweight, real-time voice changer using TD-PSOLA — natural male↔female conversion for Discord and other VoIP apps, without the metallic "phase-vocoder" sound.**

輕量級即時變聲器，採用 TD-PSOLA 時域演算法，男女互轉自然不金屬，可直接用於 Discord 等語音軟體。

[![tests](https://github.com/NTUquantum/realtime-voice-changer/actions/workflows/tests.yml/badge.svg)](https://github.com/NTUquantum/realtime-voice-changer/actions)
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
- 🪶 **Light** — < 17 % of one CPU core, < 80 MB RAM, ~70 ms latency
- 🧪 **Tested** — 19 hardware-free DSP tests in CI
- 🖥️ GUI **and** headless CLI

### Install

```bash
git clone https://github.com/NTUquantum/realtime-voice-changer.git
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

### Development

```bash
pip install -e ".[dev]"
pytest -q
```

The tests synthesise glottal-source voices and assert that pitch shifting
actually moves F0, that presets land in the right range, that harmonics are
preserved (low metallic artefact) and that the stream never clicks or clips —
all without audio hardware.

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
- 🪶 **輕量**——CPU < 17%、記憶體 < 80MB、延遲約 70ms
- 🧪 **有測試**——19 個不需音訊硬體的 DSP 測試
- 🖥️ 圖形介面與命令列皆可

### 安裝

```bash
git clone https://github.com/NTUquantum/realtime-voice-changer.git
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

### 誠實的限制與進階（RVC）

純 DSP 即時變聲有天花板：它是「搬移」你的聲音、不是「重新生成」目標音色，所以移調多時仍會有點人工感。若要做到幾乎聽不出來的擬真轉換，需要神經網路模型：

- **RVC**：即時版 [w-okada/voice-changer](https://github.com/w-okada/voice-changer)
- 需要像樣的 GPU 與訓練好的目標模型，延遲也較高。

本專案是不需 GPU、不需訓練、日常用「夠好」的輕量選擇。

---

## License

[MIT](LICENSE) © NTUquantum

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md).
