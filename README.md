<div align="center">

<img src="docs/kapak.jpg" alt="Bu kolu Arduino yönetiyor — Praxtify" width="100%">

# Arduino ile Robot Kol: Al-Bırak · UNO R4 WiFi + SO101

**Bu kolu bir Arduino nasıl yönetiyor?** Bu repo, altı STS3215 seri bus servolu SO101 robot kolunun bir kutuyu alıp
hedefe bıraktığı Arduino kodunu içerir. Duruşlar MuJoCo'da ters kinematikle hesaplanır, servo adımına çevrilir ve
**tek kablo** üzerinden altı servoya birden gönderilir. Gerçek kolun yoksa aynı kodu **MuJoCo simülasyonunda** çalıştırabilirsin.

[![Arduino](https://img.shields.io/badge/Arduino-UNO%20R4%20WiFi-00878F?logo=arduino&logoColor=white)](https://docs.arduino.cc/hardware/uno-r4-wifi/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MuJoCo](https://img.shields.io/badge/MuJoCo-3.x-1E88E5)](https://mujoco.org/)
[![Lisans: MIT](https://img.shields.io/badge/Lisans-MIT-green.svg)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-@praxtify-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/@praxtify)

</div>

<p align="center">
  <img src="docs/simulasyon.gif" alt="SO101 kol, Arduino kodunun komutlarıyla kutuyu alıp hedefe bırakıyor" width="720">
</p>

---

## İçindekiler

- [Ne öğreneceksin?](#ne-öğreneceksin)
- [Donanım](#donanım)
- [Bağlantılar](#bağlantılar)
- [Kodu karta yükle](#kodu-karta-yükle)
- [Kolun yoksa: MuJoCo simülasyonu](#kolun-yoksa-mujoco-simülasyonu)
- [Proje yapısı](#proje-yapısı)
- [Nasıl çalışıyor?](#nasıl-çalışıyor)
- [Kendin dene](#kendin-dene)
- [Kaynaklar ve lisanslar](#kaynaklar-ve-lisanslar)
- [Praxtify](#praxtify)

## Ne öğreneceksin?

| Konu | Bu projede |
|---|---|
| Seri bus servo | Altı STS3215 tek kabloya zincirli; her birinin kendi kimliği (ID) var |
| Açıdan adıma | Ters kinematiğin verdiği eklem açılarını servo adımına çevirme: `adım = 2048 + açı × 651,9` |
| Eş zamanlı hareket | `SyncWritePosEx` ile altı servoya **tek pakette** konum, hız ve ivme |
| Geri bildirim | `ReadMove` ile her servoya "hâlâ hareket ediyor musun?" diye sorup bekleme |
| Donanım UART | UNO R4'te `Serial1` (D0/D1), USB'den bağımsız 1 Mbit/sn hat |

Arduino kodunun tamamı **tek dosya, 41 satır**: [`al_birak/al_birak.ino`](al_birak/al_birak.ino). Videoda anlatılan kodla birebir aynıdır.

## Donanım

| Parça | Görevi |
|---|---|
| **SO101 robot kol** (6 × Feetech STS3215) | Taban, omuz, dirsek, bilek, bilek dönüşü, tutucu |
| **Arduino UNO R4 WiFi** | Kodu çalıştırır, servo kartına UART üzerinden komut gönderir |
| **Waveshare Bus Servo Adapter (A)** | Arduino'nun UART sinyalini servoların tek telli bus hattına çevirir, servolara güç verir |
| **3S Li-Po pil** (11,1 V) + XT60 → DC dönüştürücü | Servo gücü |
| 3 × dupont jumper kablo | TX, RX, GND |
| USB-C kablo | Arduino'ya güç ve kod |

> [!WARNING]
> STS3215'in **7,4 V** ve **12 V** sürümleri var. Pil voltajını kolundaki servoların sürümüne göre seç; videodaki kurulum 11,1 V'luk 3S pil kullanır.

## Bağlantılar

<p align="center"><img src="docs/baglanti.jpg" alt="Arduino UNO R4 WiFi ile Waveshare servo kartı arasında üç kablo: TX, RX, GND" width="720"></p>

1. **Servo kartında iki jumper'ı A konumuna al.** Kart artık kontrolü UART pinlerinden alır.
2. **Üç jumper kablo** — bu kartta bağlantı **çapraz değil, düz**:

   | Arduino UNO R4 WiFi | Waveshare Bus Servo Adapter (A) |
   |---|---|
   | D1 (TX) | TX |
   | D0 (RX) | RX |
   | GND | GND |

3. **Servo zincir kablosunu** karta tak, sonra **pili** bağla. Kartın kırmızı ışığı yanar.
4. **USB-C** ile Arduino'yu bilgisayara bağla.

## Kodu karta yükle

Arduino IDE kullanıyorsan: **Library Manager**'dan `SCServo`'yu, **Boards Manager**'dan *Arduino UNO R4 Boards*'u kur,
`al_birak/al_birak.ino`'yu aç, kart olarak *Arduino UNO R4 WiFi*'yi seçip yükle.

Komut satırından ([arduino-cli](https://arduino.github.io/arduino-cli/)):

```bash
git clone https://github.com/praxtify/1-arduino-robot-kol.git
cd 1-arduino-robot-kol

arduino-cli core install arduino:renesas_uno
arduino-cli lib install SCServo

arduino-cli compile -b arduino:renesas_uno:unor4wifi al_birak
arduino-cli upload  -b arduino:renesas_uno:unor4wifi -p <PORT> al_birak   # Windows: COM3 · Linux: /dev/ttyACM0
```

Derleme çıktısı: program alanının **%20**'si (54 372 / 262 144 bayt). Kol, kart açıldıktan 1 saniye sonra görevi bir kez yapar.

> [!IMPORTANT]
> - Tablodaki sayılar **2048 adım = MuJoCo'daki sıfır açı** varsayımıyla hesaplandı. Gerçek kolda servoların orta konumu bu
>   duruşa göre kalibre edilmiş olmalı; değilse kol farklı noktalara gider.
> - İlk denemede `HIZ` değerlerini düşür (örneğin 300) ve kolun çevresini boş tut.
> - Test edilen ortam: arduino-cli 1.5 · Arduino UNO R4 Boards 1.6.0 · SCServo 1.0.2.

## Kolun yoksa: MuJoCo simülasyonu

`simulasyon/arduino_sim.py`, `al_birak.ino`'yu **doğrudan okur** (HIZ, IVME, DURUS tablosu ve beklemeler) ve kodu
MuJoCo'da oynatır. Servolar koddaki hız ve ivmeyle hareket eder; kutuyu tutmak ve bırakmak tamamen fizik motorunun
temas hesabıyla olur.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python simulasyon/arduino_sim.py               # 3D pencereyle
python simulasyon/arduino_sim.py --ekransiz    # yalnız sonucu yazdır
```

Beklenen çıktı:

```text
9 duruş, 8.9 sn · kutu hedefin ortasına 1.8 mm yakın bırakıldı
```

`.ino`'daki tabloyu değiştirirsen simülasyon da değişir: kodu karta yüklemeden önce burada deneyebilirsin.

> [!NOTE]
> - Komutları **repo klasöründen** çalıştır.
> - **macOS'ta** pencereli çalıştırmak için `python` yerine `mjpython` kullan (MuJoCo ile birlikte gelir).
> - Test edilen ortam: Python 3.13 · MuJoCo 3.15 · NumPy 2.5 (Windows 11).

## Proje yapısı

```text
1-arduino-robot-kol/
├── al_birak/
│   └── al_birak.ino                        # Arduino kodu (videodaki)
├── simulasyon/
│   ├── sahne.py                            # SO101 + kutu sahnesi, ters kinematik, al-bırak planı
│   ├── duruslar.py                         # DURUS tablosunu ters kinematikle yeniden üretir
│   └── arduino_sim.py                      # .ino'yu okuyup MuJoCo'da oynatır
├── models/
│   └── mujoco_menagerie/robotstudio_so101/ # SO101 robot modeli (MuJoCo Menagerie, Apache 2.0)
├── docs/                                   # README görselleri
├── requirements.txt                        # mujoco, numpy (yalnız simülasyon için)
└── LICENSE                                 # MIT (proje kodu)
```

## Nasıl çalışıyor?

### 1 · Servolar: altı motor, tek kablo

```cpp
#include <SCServo.h>                        // Feetech servo kütüphanesi
SMS_STS servo;                              // STS3215 seri bus servolar

u8  ID[6]   = {1, 2, 3, 4, 5, 6};           // taban, omuz, dirsek, bilek, dönüş, tutucu
u16 HIZ[6]  = {800, 800, 800, 800, 800, 800};  // adım / saniye
u8  IVME[6] = {40, 40, 40, 40, 40, 40};     // × 100 adım / saniye²
```

STS3215'te bir tur **4096 adım**. Saniyede 800 adım, yaklaşık **70°/sn** eder (800 × 360 / 4096). İvme 40 × 100 = 4000 adım/sn².

### 2 · Duruş tablosu: açıdan adıma

Her satır kolun bir duruşu, altı sayı altı servonun hedefi: başla, kutunun üstü, aşağı in, kavra, kaldır, hedefin üstü,
indir, bırak, yukarı çekil.

<p align="center"><img src="docs/durus-formulu.jpg" alt="DURUS tablosu: adım = 2048 + açı × 651,9" width="720"></p>

Sayılar elle yazılmadı. MuJoCo'da her duruş için tutucu ucunun gideceği nokta verilir, **ters kinematik** eklem açılarını
bulur ve her açı servo adımına çevrilir:

$$\text{adım} = 2048 + \theta \cdot \frac{4096}{2\pi} \approx 2048 + \theta \cdot 651{,}9$$

Tabloyu kendin üretmek için:

```bash
python simulasyon/duruslar.py
```

Çıktı, `al_birak.ino`'daki `DURUS` tablosuyla **birebir aynıdır** (her duruşta uç hedefe 0,3 mm'den yakın).
**Kavra** satırında yalnız son sayı değişir: tutucu 2439'dan 1937'ye kapanır ve kutuyu sıkar.

### 3 · `git()`: tek paket, sonra bekle

<p align="center"><img src="docs/tek-paket.jpg" alt="SyncWritePosEx: altı servo, tek paket" width="720"></p>

```cpp
servo.SyncWritePosEx(ID, 6, hedef, HIZ, IVME);  // altı servo, tek paket
delay(20);
for (int j = 0; j < 6; j++)
  while (servo.ReadMove(ID[j]) == 1) delay(10);  // hepsi varana kadar bekle
```

`SyncWritePosEx` altı servoya konum, hız ve ivmeyi **tek pakette** gönderir; hepsi aynı anda yola çıkar.
`ReadMove` her servoya hâlâ hareket edip etmediğini sorar. En yavaş servo da varınca bir sonraki duruşa geçilir.

### 4 · Kurulum ve görev

```cpp
Serial1.begin(1000000);                   // D0 / D1 → Waveshare UART
servo.pSerial = &Serial1;
```

`Serial1`, UNO R4'ün **D0 ve D1** pinleridir: USB'den bağımsız, doğrudan servo kartına giden donanım UART'ı. Hat
saniyede 1 megabit hızla açılır. Ardından tablo sırayla dolaşılır, her duruştan sonra 300 ms beklenir (tutucu otursun).

### 5 · Simülasyon: kodun MuJoCo'daki koşusu

`arduino_sim.py`, servoların **yamuk hız profilini** taklit eder: koddaki ivmeyle hızlanır, en fazla `HIZ` ile gider,
aynı ivmeyle yavaşlayarak durur. Kısa mesafelerde tepe hıza ulaşmadan döner (üçgen profil). Bir hareketin süresi:

$$T = \frac{d}{v} + \frac{v}{a} \quad (d \ge v^2/a), \qquad T = 2\sqrt{d/a} \quad (d < v^2/a)$$

Her 5 ms'lik fizik adımında servo hedefleri motorlara verilir, `mj_step` dünyayı ilerletir. Görev 8,9 saniyede biter ve kutu
hedefin ortasına **1,8 mm** yakın bırakılır.

## Kendin dene

- `HIZ`'ı 400'e indir: görev ne kadar uzar? (`arduino_sim.py --ekransiz` süreyi yazar.)
- **Kavra** satırındaki 1937'yi 2100 yap: tutucu kutuyu yeterince sıkmazsa kutu kayıyor mu?
- `simulasyon/sahne.py`'de `DROP_SPOT`'u değiştir, `duruslar.py` ile yeni tabloyu üret ve `.ino`'ya yapıştır.
- `delay(300)`'ü kaldır: tutucu tam kapanmadan kalkarsa ne olur?

## Kaynaklar ve lisanslar

Bu repodaki **proje kodu** ([`al_birak.ino`](al_birak/al_birak.ino) ve [`simulasyon/`](simulasyon)) [MIT lisansı](LICENSE)
ile yayımlanır. Üçüncü taraf parçalar kendi lisanslarıyla gelir:

| Bileşen | Kaynak | Lisans | Repoda |
|---|---|---|---|
| **SO101 robot modeli** (MJCF + STL) | [MuJoCo Menagerie · `robotstudio_so101`](https://github.com/google-deepmind/mujoco_menagerie/tree/main/robotstudio_so101) — The Robot Studio'nun [SO-ARM100 / SO101](https://github.com/TheRobotStudio/SO-ARM100) tasarımından | [Apache 2.0](models/mujoco_menagerie/robotstudio_so101/LICENSE) | ✔ `models/` (değiştirilmeden) |
| **SCServo** Arduino kütüphanesi | [workloads/scservo](https://github.com/workloads/scservo) (Feetech & Waveshare kaynaklı) | GPL-3.0 | Library Manager ile kurulur |
| **Arduino UNO R4 Boards** çekirdeği | [arduino/ArduinoCore-renesas](https://github.com/arduino/ArduinoCore-renesas) | MIT | Boards Manager ile kurulur |
| **MuJoCo** fizik motoru | [Google DeepMind](https://github.com/google-deepmind/mujoco) | Apache 2.0 | `pip` ile kurulur |
| **NumPy** | [numpy.org](https://numpy.org/) | BSD 3-Clause | `pip` ile kurulur |

Görsellerdeki 3D modeller yalnız anlatım içindir ve repoda yer almaz. Kablolar Praxtify tarafından Blender'da modellendi.
Diğer parça modelleri (Arduino UNO R4 WiFi, Waveshare servo adaptörü, Li-Po pil) [GrabCAD](https://grabcad.com/library) topluluğundan alındı.

## Praxtify

**Teoriyi pratiğe dönüştürüyoruz.** Robotik, gömülü sistemler ve yapay zekâyı çalışan kodla, adım adım anlatıyoruz.
Bu projenin videosu ve yeni projeler için:

<p align="center">
  <a href="https://praxtify.com"><img src="https://img.shields.io/badge/praxtify.com-Web-111111?style=for-the-badge" alt="praxtify.com"></a>
  <a href="https://www.youtube.com/@praxtify"><img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube"></a>
  <a href="https://www.instagram.com/praxtify"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram"></a>
  <a href="https://www.tiktok.com/@praxtify"><img src="https://img.shields.io/badge/TikTok-000000?style=for-the-badge&logo=tiktok&logoColor=white" alt="TikTok"></a>
  <a href="https://x.com/praxtify"><img src="https://img.shields.io/badge/X-000000?style=for-the-badge&logo=x&logoColor=white" alt="X"></a>
  <a href="https://www.threads.net/@praxtify"><img src="https://img.shields.io/badge/Threads-000000?style=for-the-badge&logo=threads&logoColor=white" alt="Threads"></a>
  <a href="https://www.linkedin.com/company/praxtify"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="https://www.facebook.com/praxtify"><img src="https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white" alt="Facebook"></a>
  <a href="https://www.pinterest.com/praxtify"><img src="https://img.shields.io/badge/Pinterest-BD081C?style=for-the-badge&logo=pinterest&logoColor=white" alt="Pinterest"></a>
</p>

Soru, hata ya da öneri için bir [issue](../../issues) aç. Projeyi beğendiysen ⭐ vermeyi unutma!

**Serinin önceki projesi:** [0-mujoco-ters-kinematik](https://github.com/praxtify/0-mujoco-ters-kinematik): aynı kolun ters kinematiğini sıfırdan çözüyoruz.

**Serinin sıradaki projesi:** [2-arduino-radar](https://github.com/praxtify/2-arduino-radar): HC-SR04 ve SG90 ile masanın radarını kuruyoruz.
